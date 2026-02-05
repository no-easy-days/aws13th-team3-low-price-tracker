from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/wishlist",
    tags=["wishlist"]
)

@router.patch("", response_model=schemas.PriceUpdateResponse)
async def update_item_price(
        request: schemas.PriceUpdateRequest = Body(...),
        db: Session = Depends(get_db)
):
    """
    [상품 가격 업데이트 API]
    - item_id(PK)로 상품을 찾아서 가격을 비교합니다.
    - 가격이 더 떨어졌다면 DB를 업데이트하고 결과를 반환합니다.
    """

    item = db.query(models.Wishlist).filter(models.Wishlist.wishlist_id == request.item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="해당 상품을 찾을 수 없습니다.")

    old_price = item.lprice
    new_price = request.price

    diff_amount = new_price - old_price

    if old_price == 0:
        diff_rate = 0.0
    else:
        diff_rate = round((diff_amount / old_price) * 100, 2)

    if new_price < old_price:
        item.lprice = new_price
        item.updated_at = datetime.now()
        db.commit()
        db.refresh(item)
        msg = "가격 정보가 최신화되었습니다."
    else:
        msg = "가격이 떨어지지 않아 유지되었습니다."

    response_data = schemas.PriceUpdateData(
        product_id=item.product_id,
        title=item.title,
        new_price=new_price,
        old_price=old_price,
        diff_amount=diff_amount,
        diff_rate=diff_rate,
        updated_at=item.updated_at or datetime.now()
    )

    return schemas.PriceUpdateResponse(
        result_code="SUCCESS",
        message=msg,
        data=response_data
    )