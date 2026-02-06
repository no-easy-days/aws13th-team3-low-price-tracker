# routers/wishlist_ref.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from datetime import datetime  # datetime 에러 방지용 import
from database import get_db
import models
import schemas
from database import get_db
from routers.auth import get_current_user
from crud import add_to_wishlist, remove_from_wishlist, hard_remove_from_wishlist

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

@router.get("", response_model=schemas.WishlistListResponse)
async def get_wishlist(
        display: int = Query(10, le=100),
        start: int = Query(1, le=1000),
        sort: str = Query("date", regex="^(sim|date|asc|dsc)$"),
        db: Session = Depends(get_db),
        user_id: int = 1  # 추후 Auth 적용 시 current_user.id로 변경 필요
):
    # Wishlist 테이블만으로는 가격 정렬이나 상품 정보를 알 수 없으므로 Item 테이블과 JOIN합니다.
    # models.Wishlist.item 관계(relationship)를 사용하여 JOIN
    query = db.query(models.Wishlist).join(models.Wishlist.item).filter(models.Wishlist.user_id == user_id)

    # models.Wishlist.lprice는 존재하지 않으므로, models.Item.last_seen_price를 사용해야 합니다.
    if sort == "date":
        # 최신순 (위시리스트 담은 날짜 기준)
        query = query.order_by(models.Wishlist.created_at.desc())
    elif sort == "asc":
        # 가격 낮은 순 (아이템의 최근 가격 기준)
        query = query.order_by(models.Item.last_seen_price.asc())
    elif sort == "dsc":
        # 가격 높은 순 (아이템의 최근 가격 기준)
        query = query.order_by(models.Item.last_seen_price.desc())
    # sim(정확도) 정렬은 DB에 저장된 후에는 판단하기 어려우므로 date로 대체하거나 생략

    # 전체 개수 조회
    total_count = query.count()

    # 페이징 적용 (start는 1부터 시작하므로 -1)
    offset = (start - 1) * display
    rows = query.offset(offset).limit(display).all()

    # DB에서 꺼낸 ORM 객체(Wishlist)를 Pydantic 스키마(WishlistItem) 구조로 변환합니다.
    wishlist_items = []
    for row in rows:
        # row는 Wishlist 객체이고, row.item을 통해 Item 객체에 접근 가능
        item = row.item

        wishlist_items.append(
            schemas.WishlistItem(
                wishlist_id=row.id,
                created_at=row.created_at,
                # --- 아래는 Item 테이블에서 가져오는 정보 ---
                product_id=item.external_id,  # 네이버 상품 ID
                title=item.title,
                link=item.product_url,
                lprice=item.last_seen_price if item.last_seen_price is not None else 0,  # None 방지
                initial_price=item.initial_price,
                mall_name=item.mall_name or "",  # None 방지
                # --- 현재 DB 모델(Item)에 없는 컬럼들은 None 처리 ---
                brand=None,
                category1=None,
                category2=None,
                category3=None
            )
        )

    # 최종 응답 생성
    return schemas.WishlistListResponse(
        result_code="SUCCESS",
        total_count=total_count,
        user_id=user_id,
        wishlist_items=wishlist_items
    )
