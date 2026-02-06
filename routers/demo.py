# routers/demo.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Item, Wishlist, Alert
from crud import insert_price_history, update_min_price_last_7d
from services.alert_service import evaluate_alerts_for_price_update

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_ITEM_ID = 1
DEMO_USER_ID = 1
DEMO_PRICE = 120000


@router.post("/trigger-alert")
def trigger_alert(db: Session = Depends(get_db)):
    """
    Swagger 시연용:
    - item_id=1의 가격을 120000으로 '강제 반영'
    - price_history 1건 INSERT
    - wishlist/alert 없으면 자동 생성
    - 알람 평가 실행 -> 조건 충족 시 터미널에 [ALERT TRIGGERED] 출력
    """

    # 1) item 존재 확인
    item = db.query(Item).filter(Item.id == DEMO_ITEM_ID).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item not found: id={DEMO_ITEM_ID}")

    # (선택) 데모가 항상 '가격 변동'으로 인식되도록 기존 가격을 일부러 올려둠
    old_last_seen_price: Optional[int] = item.last_seen_price
    old_min_price: Optional[int] = item.min_price

    item.last_seen_price = DEMO_PRICE  # 최종적으로 12만원으로 반영될 값

    # 2) wishlist 없으면 생성 (활성)
    wishlist = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == DEMO_USER_ID)
        .filter(Wishlist.item_id == DEMO_ITEM_ID)
        .first()
    )
    if wishlist is None:
        wishlist = Wishlist(user_id=DEMO_USER_ID, item_id=DEMO_ITEM_ID, is_active=1)
        db.add(wishlist)
        db.flush()  # wishlist.id 확보
    else:
        wishlist.is_active = 1  # 데모에서는 무조건 활성

    # 3) alert 없으면 생성 (TARGET_PRICE 120000)
    alert = (
        db.query(Alert)
        .filter(Alert.wishlist_id == wishlist.id)
        .filter(Alert.alert_type == "TARGET_PRICE")
        .first()
    )
    if alert is None:
        alert = Alert(
            wishlist_id=wishlist.id,
            alert_type="TARGET_PRICE",
            target_price=DEMO_PRICE,
            is_enabled=1,
        )
        db.add(alert)
    else:
        # 데모에서는 무조건 목표가/활성으로 맞춰둠
        alert.target_price = DEMO_PRICE
        alert.is_enabled = 1

    # 4) price_history INSERT (id/checked_at 자동)
    ph = insert_price_history(db, item.id, DEMO_PRICE)

    # 5) min_price 갱신 (최근 7일 최저가)
    update_min_price_last_7d(db, item)

    # 6) 알람 평가 실행 (조건 맞으면 alert_service 내부 print가 터미널에 찍힘)
    triggered = evaluate_alerts_for_price_update(
        db,
        wishlist_id=wishlist.id,
        new_ph=ph,
        old_last_seen_price=old_last_seen_price,
        old_min_price=old_min_price,
    )

    db.commit()

    return {
        "item_id": item.id,
        "set_price": DEMO_PRICE,
        "price_history_id": ph.id,
        "wishlist_id": wishlist.id,
        "triggered_count": triggered,
        "note": "If triggered_count > 0, check terminal output for [ALERT TRIGGERED].",
    }
