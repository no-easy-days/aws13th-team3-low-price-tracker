
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Item, PriceHistory


def upsert_item_from_naver(db: Session, data: Dict[str, Any]) -> Item:
    """
    normalized naver item(dict)을 items 테이블에 upsert.
    external_id 기준.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # MySQL DATETIME용 naive로 통일(권장)

    external_id = data["external_id"]
    price = int(data["price"])

    item = db.query(Item).filter(Item.external_id == external_id).first()

    if item is None:
        item = Item(
            external_id=external_id,
            title=data["title"],
            image_url=data.get("image_url") or None,
            product_url=data["product_url"],
            mall_name=data.get("mall_name") or None,
            initial_price=price,
            last_seen_price=price,
            min_price=price,              # 일단 최초값, 이후 최근7일 로직에서 갱신
            last_checked_at=now,
            is_active=True,
        )
        db.add(item)
        db.flush()  # item.id 확보
    else:
        item.title = data["title"]
        item.image_url = data.get("image_url") or None
        item.product_url = data["product_url"]
        item.mall_name = data.get("mall_name") or None
        item.last_seen_price = price
        item.last_checked_at = now

    return item


def insert_price_history(db: Session, item_id: int, price: int) -> PriceHistory:
    ph = PriceHistory(
        item_id=item_id,
        price=price,
    )
    db.add(ph)
    db.flush()
    return ph


def update_min_price_last_7d(db: Session, item: Item) -> None:
    """
    price_history 기준 최근 7일 최저가를 items.min_price로 갱신
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=7)

    min_price = (
        db.query(func.min(PriceHistory.price))
        .filter(PriceHistory.item_id == item.id)
        .filter(PriceHistory.checked_at >= since)
        .scalar()
    )

    if min_price is not None:
        item.min_price = int(min_price)
