from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from crud import upsert_item_from_naver, insert_price_history, update_min_price_last_7d
from services.naver_shopping_client import refresh_product_price, KEYBOARD_CATEGORY_ID
from models import Wishlist, Item


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
