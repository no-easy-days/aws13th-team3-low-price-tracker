from schemas import ProductsGetResponse, ProductItem
from typing import List
from fastapi import APIRouter, Query



router = APIRouter(prefix="/products", tags=["products"])

@router.get(
    "",
    response_model=ProductsGetResponse,
    summary="상품 목록 조회",
    description="네이버 쇼핑 API 연동 전 단계로 임시 데이터(mock)를 반환합니다.",
)
def get_products(
    q: str = Query(..., description="검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 당 개수"),
):
    items: List[ProductItem] = [
        ProductItem(
            product_id="123456",
            title=f"[MOCK] {q} 검색 결과 샘플 상품",
            link="https://shopping.naver.com",
            lprice=10000,
            mall_name="NAVER",
            image=None,
            brand=None,
            category1=None,
            category2=None,
            category3=None,
        ),
        ProductItem(
            product_id="789012",
            title=f"[MOCK] {q} 검색 결과 샘플 상품 2",
            link="https://shopping.naver.com",
            lprice=25000,
            mall_name="NAVER",
            image=None,
            brand=None,
            category1=None,
            category2=None,
            category3=None,
        ),
    ]

    return {
        "result_code": "SUCCESS",
        "total_count": len(items),
        "page": page,
        "size": size,
        "items": items,
    }
