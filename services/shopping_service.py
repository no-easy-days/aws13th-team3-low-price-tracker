# services/shopping_service.py
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from crud import upsert_item_from_naver, insert_price_history, update_min_price_last_7d
from models import Wishlist, Item
from services.naver_shopping_client import (
    search_products,
    refresh_product_price,
    KEYBOARD_CATEGORY_ID,
)

def save_naver_search_results(db: Session, items: List[Dict[str, Any]]) -> List[int]:
    """
    네이버 검색 결과(normalized list)를 DB에 저장/갱신하고,
    저장된 item_id 리스트 반환
    """
    saved_ids: List[int] = []

    for data in items:
        item = upsert_item_from_naver(db, data)
        insert_price_history(db, item.id, int(data["price"]))
        update_min_price_last_7d(db, item)
        saved_ids.append(item.id)

    db.commit()
    return saved_ids

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
    수집 배치용:
    네이버 쇼핑 검색을 여러 페이지(start)로 돌려서 total개까지 수집/저장(upsert)한다.
    (외부 호출: naver_shopping_client, 저장: crud)
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

        normalized_items = search_products(
            query=query,
            category=category,
            display=display,
            start=start,
            sort=sort,
            strict=strict,
        )

        #  저장은 이 레이어가 책임
        for data in normalized_items:
            item = upsert_item_from_naver(db, data)
            insert_price_history(db, item.id, int(data["price"]))
            update_min_price_last_7d(db, item)

        db.commit()

        saved_total += len(normalized_items)
        start += display

        if len(normalized_items) == 0:
            break

    return saved_total

def refresh_wishlist_prices(db: Session) -> int:
    """
    활성화된 wishlist 기반으로 item 가격을 갱신하고 price_history 기록.
    return: 갱신한 item 개수
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
        new_price = refresh_product_price(
            query=item.title,
            product_url=item.product_url,
            category=KEYBOARD_CATEGORY_ID,
        )

        item.last_seen_price = new_price
        insert_price_history(db, item.id, new_price)
        update_min_price_last_7d(db, item)
        updated += 1

    db.commit()
    return updated