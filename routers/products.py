# routers/products.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.naver_shopping_client import search_and_save, KEYBOARD_CATEGORY_ID

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search-save")
def search_save(q: str, db: Session = Depends(get_db)):
    saved = search_and_save(db, query=q, category=KEYBOARD_CATEGORY_ID)
    return {"saved_count": saved}
