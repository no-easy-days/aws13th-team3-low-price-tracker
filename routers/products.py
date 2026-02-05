# routers/products.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Item
from services.naver_shopping_client import search_products, KEYBOARD_CATEGORY_ID

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/{item_id}/lowest-price")
def get_lowest_price(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 네이버에서 가격 낮은 순으로 많이 가져와서(최대 100)
    results = search_products(
        query=item.title,
        category=KEYBOARD_CATEGORY_ID,
        sort="asc",
        display=100,
    )

    # 같은 상품(external_id)만 필터링
    same_product = [r for r in results if r.get("external_id") == item.external_id]

    if not same_product:
        # 검색 결과에서 같은 상품을 못 찾으면 fallback: 전체 결과 중 최저가
        if not results:
            raise HTTPException(status_code=404, detail="No search results")
        best = results[0]
    else:
        best = same_product[0]  # sort=asc라서 첫 번째가 최저가

    return {
        "item_id": item.id,
        "title": item.title,
        "external_id": item.external_id,
        "current_lowest_price": best["price"],
        "lowest_mall_name": best.get("mall_name", ""),
        "lowest_product_url": best.get("product_url", ""),
        "checked_count": len(results),
        "matched_count": len(same_product),
    }
