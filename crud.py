from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func
import models
from models import Item, PriceHistory

def remove_from_wishlist(db: Session, *, user_id: int, item_id: int) -> models.Wishlist:
    w = (
        db.query(models.Wishlist)
        .filter(
            models.Wishlist.user_id == user_id,
            models.Wishlist.item_id == item_id,
            models.Wishlist.is_active == 1,
        )
        .first()
    )
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    w.is_active = 0
    db.commit()
    db.refresh(w)
    return w

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
# crud.py
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from models import Wishlist, Item

def add_to_wishlist(db, *, user_id: int, item_id: int) -> Wishlist:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    w = Wishlist(user_id=user_id, item_id=item_id, is_active=1)
    db.add(w)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # 이미 있으면 기존 row 반환(혹은 그냥 409로 반환해도 됨)
        existing = (
            db.query(Wishlist)
            .filter(Wishlist.user_id == user_id, Wishlist.item_id == item_id)
            .first()
        )
        return existing

    db.refresh(w)
    return w
