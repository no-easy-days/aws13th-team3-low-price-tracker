from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db  # DB 세션 가져오기
import schemas

router = APIRouter(
    prefix="/wishlist",
    tags=["wishlist"]
)


@router.get("/drops", response_model=schemas.ProductSearchResponse)
async def get_lowest_price_products(
):
    """
    [최저가 상품 조회 API]
    - 특정 키워드(예: 키보드)에 대한 쇼핑 검색 결과를 반환합니다.
    - 현재는 명세서 기반 더미 데이터를 반환합니다.
    """

    # --- [TODO] 실제로는 여기서 네이버 쇼핑 API 등을 호출하거나 DB 로직이 들어감 ---

    # 더미 데이터 생성
    mock_items = [
        schemas.ProductItem(
            product_id="82495671234",
            title="로지텍 MX KEYS S 무선 일루미네이티드 <b>키보드</b>",
            link="https://search.shopping.naver.com/gate.nhn?id=82495671234",
            lprice=139000,
            mall_name="네이버 스토어",
            brand="로지텍",
            maker="로지텍",
            category1="디지털/가전",
            category2="PC주변기기",
            category3="키보드",
            category4="무선키보드"
        ),
        schemas.ProductItem(
            product_id="21345678901",
            title="COX CK87 게이트론 LED 게이밍 기계식 <b>키보드</b> (갈축)",
            link="https://search.shopping.naver.com/gate.nhn?id=21345678901",
            lprice=45900,
            mall_name="쿠팡",
            brand="COX",
            maker="앱코",
            category1="디지털/가전",
            category2="PC주변기기",
            category3="키보드",
            category4="기계식키보드"
        )
    ]

    return schemas.ProductSearchResponse(
        search_keyword="키보드",
        result_code="SUCCESS",
        total_count=285400,
        items=mock_items
    )