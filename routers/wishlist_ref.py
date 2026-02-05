from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/wishlist",
    tags=["wishlist"]
)


@router.get("", response_model=schemas.WishlistListResponse)
async def get_wishlist(
        display: int = Query(10, le=100),
        start: int = Query(1, le=1000),
        sort: str = Query("date", regex="^(sim|date|asc|dsc)$"),
        db: Session = Depends(get_db),  # DB와 연결(database.py 만들어지면 참고해서 수정
        user_id: int = 1
):
    query = db.query(models.Wishlist).filter(models.Wishlist.user_id == user_id)

    if sort == "date":
        query = query.order_by(models.Wishlist.created_at.desc())
    elif sort == "asc":
        query = query.order_by(models.Wishlist.lprice.asc())
    elif sort == "dsc":
        query = query.order_by(models.Wishlist.lprice.desc())

    total_count = query.count()

    offset = start - 1
    items = query.offset(offset).limit(display).all()

    return schemas.WishlistListResponse(
        result_code="SUCCESS",
        total_count=total_count,
        user_id=user_id,
        wishlist_items=items
    )