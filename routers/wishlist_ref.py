# routers/wishlist_ref.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from datetime import datetime  # datetime 에러 방지용 import
from database import get_db
import models
import schemas
from database import get_db
from routers.auth import get_current_user
from crud import add_to_wishlist, remove_from_wishlist

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

@router.get("", response_model=schemas.WishlistListResponse)
async def get_wishlist(
    display: int = Query(10, le=100),
    start: int = Query(1, le=1000),
    sort: str = Query("date", pattern="^(sim|date|asc|dsc)$"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # ✅ 로그인 유저
):
    user_id = current_user.id
    query = db.query(models.Wishlist).filter(models.Wishlist.user_id == user_id)

    if sort == "date":
        query = query.order_by(models.Wishlist.created_at.desc())
    elif sort == "asc":
        query = query.order_by(models.Wishlist.item_id.asc())
    elif sort == "dsc":
        query = query.order_by(models.Wishlist.item_id.desc())

    total_count = query.count()
    offset = start - 1
    items = query.offset(offset).limit(display).all()

    return schemas.WishlistListResponse(
        result_code="SUCCESS",
        total_count=total_count,
        user_id=user_id,
        wishlist_items=items,
    )

@router.post("", response_model=schemas.WishlistItemOut)
def create_wishlist(
    payload: schemas.WishlistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    w = add_to_wishlist(db, user_id=current_user.id, item_id=payload.item_id)
    # item 같이 내려주고 싶으면 relationship 로딩 필요할 수도 있음(지금은 OK일 가능성 높음)
    return w

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wishlist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    remove_from_wishlist(db, user_id=current_user.id, item_id=item_id)
    return