from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
import models
import schemas

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=schemas.AlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(payload: schemas.AlertCreate, db: Session = Depends(get_db)):
    # wishlist 존재 확인
    w = db.query(models.Wishlist).filter(models.Wishlist.id == payload.wishlist_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    # TARGET_PRICE면 target_price 필수
    if payload.alert_type == "TARGET_PRICE" and payload.target_price is None:
        raise HTTPException(status_code=400, detail="target_price is required for TARGET_PRICE")

    a = models.Alert(
        wishlist_id=payload.wishlist_id,
        alert_type=payload.alert_type,
        target_price=payload.target_price,
        is_enabled=1,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    wishlist_id: int = Query(..., description="wishlist PK"),
    db: Session = Depends(get_db),
):
    rows = db.query(models.Alert).filter(models.Alert.wishlist_id == wishlist_id).all()
    return rows


@router.patch("/{alert_id}", response_model=schemas.AlertOut)
def toggle_alert(
    alert_id: int,
    payload: schemas.AlertToggle,
    db: Session = Depends(get_db),
):
    a = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    if payload.is_enabled not in (0, 1):
        raise HTTPException(status_code=400, detail="is_enabled must be 0 or 1")

    a.is_enabled = payload.is_enabled
    db.commit()
    db.refresh(a)
    return a
