from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

# crud에서 수정된 함수들 import
from crud import (
    upsert_item_from_naver,
    insert_price_history,
    update_min_price_last_7d,
)
from services.naver_shopping_client import refresh_product_price, search_products, KEYBOARD_CATEGORY_ID
from services.alert_service import evaluate_alerts_for_price_update
from models import Wishlist, Item, PriceHistory


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------
# 🛠️ [핵심] 가격 변동 처리 공통 로직
# ---------------------------------------------------------
def _process_price_update(db: Session, item: Item, new_price: int, is_created: bool):
    """
    아이템의 가격 변동을 감지하고, 변동이 있을 때만:
    1. PriceHistory 저장
    2. Item의 last_seen_price, min_price 갱신
    3. 알림(Alert) 트리거 체크
    """
    # 1. 신규 상품이면? -> 이미 crud에서 가격을 넣었으니 히스토리만 쌓고 끝냄
    if is_created:
        insert_price_history(db, item.id, new_price)
        return

    # 2. 기존 상품 -> 가격 비교 (이제 crud가 가격을 안 건드렸으니 비교 가능!)
    old_last_seen_price = item.last_seen_price
    old_min_price = item.min_price

    # 변동 없음: 시간만 갱신하고 종료
    if old_last_seen_price is not None and int(old_last_seen_price) == new_price:
        item.last_checked_at = _now_naive_utc()
        return

        # 3. 변동 발생: 히스토리 기록 & 아이템 업데이트
    ph = insert_price_history(db, item.id, new_price)

    item.last_seen_price = new_price
    item.last_checked_at = _now_naive_utc()

    # 4. 최저가 갱신 로직
    if old_min_price is None or new_price < int(old_min_price):
        item.min_price = new_price
    else:
        update_min_price_last_7d(db, item)

    # 5. 알림 체크 (가격 변동 시에만)
    wishlists = (
        db.query(Wishlist)
        .filter(Wishlist.item_id == item.id)
        .filter(Wishlist.is_active == 1)
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
    - _process_price_update를 통해 가격 변동 및 알림 처리 위임
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
            # ✅ 수정된 crud 호출 (tuple 반환 대응)
            item, is_created = upsert_item_from_naver(db, data)

            # 로직 위임
            _process_price_update(db, item, int(data["price"]), is_created)

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
        # ✅ 수정된 crud 호출 (tuple 반환 대응)
        item, is_created = upsert_item_from_naver(db, data)

        # 로직 위임
        _process_price_update(db, item, int(data["price"]), is_created)

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
        .filter(Wishlist.is_active == 1)
        .filter(Item.is_active == 1)
        .all()
    )

    updated_count = 0

    for item in rows:
        try:
            # 네이버 API로 최신 가격 조회
            new_price = refresh_product_price(
                query=item.title,
                product_url=item.product_url,
            )

            # 기존 상품이므로 is_created=False
            _process_price_update(db, item, int(new_price), is_created=False)

            updated_count += 1

        except Exception as e:
            # 특정 상품 갱신 실패해도 다른 상품은 계속 진행
            print(f"Failed to refresh item {item.id}: {e}")
            continue

    db.commit()
    return updated_count