from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from crud import (
    upsert_item_from_naver,
    insert_price_history,
    update_min_price_last_7d,
)
from services.naver_shopping_client import refresh_product_price, search_products
from services.alert_service import evaluate_alerts_for_price_update
from models import Wishlist, Item


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

KEYBOARD_CATEGORY_ID = "50000151"

def collect_items_pages(
    db: Session,
    *,
    query: str,
    category: str | None = None,
    total: int = 100,
    page_size: int = 50,
    sort: str = "sim",
    strict: bool = False,
) -> int:
    """
    ✅ 배치 수집용(Items 채우기)
    - 네이버 쇼핑 검색을 페이지(start)로 돌려서 total개까지 수집/저장(upsert)한다.
    - 가격이 바뀐 경우에만 price_history 기록 (같은 가격이면 스킵)
    - min_price(최근 7일 최저가) 갱신
    - 해당 item을 참조하는 wishlist가 있으면 알람 판별까지 수행(실제 전송 X)
    """
    if category is None:
        category = KEYBOARD_CATEGORY_ID

    if total < 1:
        return 0
    if not (1 <= page_size <= 100):
        raise ValueError("page_size must be between 1 and 100")

    saved_total = 0
    start = 1

    while saved_total < total:
        display = min(page_size, total - saved_total)

        items = search_products(
            query=query,
            category=category,
            display=display,
            start=start,
            sort=sort,
            strict=strict,
        )

        if not items:
            break

        for data in items:
            # upsert 수행 (Item 생성/갱신)
            item = upsert_item_from_naver(db, data)

            old_last_seen_price: Optional[int] = item.last_seen_price
            old_min_price: Optional[int] = item.min_price
            new_price = int(data["price"])

            # ✅ 가격이 변동된 경우에만 history 기록
            if old_last_seen_price is None or new_price != int(old_last_seen_price):
                ph = insert_price_history(db, item.id, new_price)
                update_min_price_last_7d(db, item)

                # ✅ 이 item을 참조하는 wishlist가 있으면 알람 판별
                wishlists = (
                    db.query(Wishlist)
                    .filter(Wishlist.item_id == item.id)
                    .filter(Wishlist.is_active == True)
                    .all()
                )

                for w in wishlists:
                    evaluate_alerts_for_price_update(
                        db,
                        wishlist_id=w.id,
                        new_ph=ph,
                        old_last_seen_price=old_last_seen_price,
                        old_min_price=old_min_price,
                    )

        db.commit()

        saved_total += len(items)
        start += display  # 다음 페이지로 이동 (1-base)

    return saved_total
def save_naver_search_results(db: Session, items: List[Dict[str, Any]]) -> List[int]:
    """
    네이버 검색 결과(normalized list)를 DB에 저장/갱신하고,
    저장된 item_id 리스트 반환
    """
    saved_ids: List[int] = []

    for data in items:
        # 기존 item 여부 확인
        item = upsert_item_from_naver(db, data)

        # 가격 변동 여부 판단
        old_last_seen_price: Optional[int] = item.last_seen_price
        old_min_price: Optional[int] = item.min_price

        # price_history는 "가격이 변했을 때만" 기록
        if old_last_seen_price is None or int(data["price"]) != int(old_last_seen_price):
            ph = insert_price_history(db, item.id, int(data["price"]))

            # min_price 갱신
            update_min_price_last_7d(db, item)

            # wishlist 기반 알람 트리거 판별
            wishlists = (
                db.query(Wishlist)
                .filter(Wishlist.item_id == item.id)
                .filter(Wishlist.is_active == True)
                .all()
            )

            for w in wishlists:
                evaluate_alerts_for_price_update(
                    db,
                    wishlist_id=w.id,
                    new_ph=ph,
                    old_last_seen_price=old_last_seen_price,
                    old_min_price=old_min_price,
                )

        saved_ids.append(item.id)

    db.commit()
    return saved_ids


def refresh_wishlist_prices(db: Session) -> int:
    """
    활성화된 wishlist 기반으로 item 가격을 갱신하고
    - 가격이 바뀐 경우에만 price_history 기록
    - 알람 조건을 판별하여 DB에 트리거 상태만 저장
    return: 갱신 처리된 item 개수
    """
    rows = (
        db.query(Item)
        .join(Wishlist, Wishlist.item_id == Item.id)
        .filter(Wishlist.is_active == True)
        .filter(Item.is_active == True)
        .all()
    )

    updated = 0

    for item in rows:
        # 갱신 전 상태 저장
        old_last_seen_price: Optional[int] = item.last_seen_price
        old_min_price: Optional[int] = item.min_price

        # 네이버 API로 최신 가격 조회
        new_price = refresh_product_price(
            query=item.title,
            product_url=item.product_url,
        )

        # 가격이 안 바뀌면 skip (history도 안 쌓음)
        if old_last_seen_price is not None and int(new_price) == int(old_last_seen_price):
            continue

        # 최신 가격 반영
        item.last_seen_price = int(new_price)
        item.last_checked_at = _now_naive_utc()

        # price_history 기록
        ph = insert_price_history(db, item.id, int(new_price))

        # min_price 갱신
        update_min_price_last_7d(db, item)

        # 이 item을 참조하는 wishlist 기준으로 알람 판별
        wishlists = (
            db.query(Wishlist)
            .filter(Wishlist.item_id == item.id)
            .filter(Wishlist.is_active == True)
            .all()
        )

        for w in wishlists:
            evaluate_alerts_for_price_update(
                db,
                wishlist_id=w.id,
                new_ph=ph,
                old_last_seen_price=old_last_seen_price,
                old_min_price=old_min_price,
            )

        updated += 1

    db.commit()
    return updated
