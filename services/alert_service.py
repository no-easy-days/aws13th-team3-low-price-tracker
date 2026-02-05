from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Alert, Wishlist, Item, PriceHistory


def _now_naive_utc() -> datetime:
    # MySQL DATETIME용 naive UTC
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_prev_price(db: Session, item_id: int) -> Optional[int]:
    """
    직전 가격(가장 최근 price_history 2개 중 '바로 이전' 값)을 가져온다.
    - price_history가 2개 미만이면 None
    """
    rows = (
        db.query(PriceHistory)
        .filter(PriceHistory.item_id == item_id)
        .order_by(desc(PriceHistory.checked_at), desc(PriceHistory.id))
        .limit(2)
        .all()
    )
    if len(rows) < 2:
        return None
    return int(rows[1].price)


def evaluate_alerts_for_price_update(
    db: Session,
    *,
    wishlist_id: int,
    new_ph: PriceHistory,
    old_last_seen_price: Optional[int],
    old_min_price: Optional[int],
) -> int:
    """
    가격 갱신 후 알람을 판별하고, 트리거된 알람은 DB에만 표시(last_triggered_*)한다.
    실제 알림 전송은 하지 않는다.

    return: 트리거된 알람 개수
    """
    alerts = (
        db.query(Alert)
        .filter(Alert.wishlist_id == wishlist_id)
        .filter(Alert.is_enabled == 1)
        .all()
    )

    if not alerts:
        return 0

    # wishlist -> item
    wishlist = db.query(Wishlist).filter(Wishlist.id == wishlist_id).first()
    if not wishlist:
        return 0

    item = db.query(Item).filter(Item.id == wishlist.item_id).first()
    if not item:
        return 0

    current_price = int(new_ph.price)
    triggered = 0

    # DROP_FROM_PREV용 직전 가격(없으면 판단 불가)
    prev_price = _get_prev_price(db, item.id)

    for a in alerts:
        # 중복 트리거 방지(같은 price_history로 이미 트리거했으면 skip)
        if a.last_triggered_ph_id is not None and a.last_triggered_ph_id == new_ph.id:
            continue

        hit = False

        if a.alert_type == "TARGET_PRICE":
            if a.target_price is not None and current_price <= int(a.target_price):
                hit = True

        elif a.alert_type == "DROP_FROM_PREV":
            if prev_price is not None and current_price < int(prev_price):
                hit = True

        elif a.alert_type == "NEW_LOW":
            # "새로운 최저가"는 기존 min_price보다 낮아졌는지로 판단
            # (update_min_price_last_7d가 호출되기 전 old_min_price를 전달받는 전제)
            if old_min_price is not None and current_price < int(old_min_price):
                hit = True

        if hit:
            a.last_triggered_ph_id = new_ph.id
            a.last_triggered_at = _now_naive_utc()
            triggered += 1

    return triggered
