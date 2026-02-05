from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.shopping_service import save_naver_search_results
from services.naver_shopping_client import search_products, KEYBOARD_CATEGORY_ID

router = APIRouter(prefix="/shopping", tags=["shopping"])

@router.get("/search")
def search_and_save(q: str, db: Session = Depends(get_db)):
    # 외부 호출은 client, 저장은 service
    items = search_products(query=q, category=KEYBOARD_CATEGORY_ID, display=10)
    ids = save_naver_search_results(db, items)
    return {"count": len(ids), "saved_item_ids": ids, "items": items}