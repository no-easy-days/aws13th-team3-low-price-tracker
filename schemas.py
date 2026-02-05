from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import List, Optional
from datetime import datetime

# ==========================================
# 1. 인증 (Auth) & 유저 (User)
# ==========================================
class TokenOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# 2. 위시리스트 (Wishlist)
# ==========================================
class WishlistItem(BaseModel):
    wishlist_id: int = Field(..., description="위시리스트 PK")
    product_id: str = Field(..., description="네이버 상품 ID")
    title: str = Field(..., description="상품명")
    link: str = Field(..., description="네이버 쇼핑 링크")
    lprice: int = Field(..., description="현재 최저가")
    initial_price: int = Field(..., description="위시리스트 담을 당시 가격")
    mall_name: str = Field(..., description="판매처 이름")
    brand: Optional[str] = Field(None, description="브랜드")
    category1: Optional[str] = Field(None, description="대분류")
    category2: Optional[str] = Field(None, description="중분류")
    category3: Optional[str] = Field(None, description="소분류")
    created_at: datetime = Field(..., description="등록 일시")

class WishlistListResponse(BaseModel):
    result_code: str = Field("SUCCESS", description="결과 코드")
    total_count: int = Field(..., description="전체 아이템 수")
    user_id: int = Field(..., description="유저 ID")
    wishlist_items: List[WishlistItem] = Field(..., description="아이템 목록")

# ==========================================
# 3. [팀원 작업분 보존] 상품 조회 (ProductItem 유지)
# ==========================================
# 팀원이 만든 코드는 건드리지 않습니다.
class ProductItem(BaseModel):
    product_id: str = Field(..., description="네이버 상품 ID")
    title: str = Field(..., description="상품명")
    link: HttpUrl = Field(..., description="네이버 쇼핑 링크")
    lprice: int = Field(..., description="현재 최저가(문자열로 올 수도 있음)")
    mall_name: Optional[str] = Field(None, description="판매처 이름")
    image: Optional[HttpUrl] = Field(None, description="상품 이미지 URL")
    brand: Optional[str] = Field(None, description="브랜드")
    category1: Optional[str] = Field(None, description="대분류")
    category2: Optional[str] = Field(None, description="중분류")
    category3: Optional[str] = Field(None, description="소분류")

class ProductsGetResponse(BaseModel):
    result_code: str = Field("SUCCESS", description="결과 코드")
    total_count: int = Field(..., description="전체 상품 수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 당 개수")
    items: List[ProductItem] = Field(..., description="상품 목록")

# ==========================================
# 4. [본인 작업분 수정] 최저가 조회 (이름 변경: ProductItem -> SearchProductItem)
# ==========================================
# 이름이 겹치지 않게 'Search'를 붙여서 내 코드를 수정합니다.
class SearchProductItem(BaseModel):
    product_id: str = Field(..., description="상품 ID")
    title: str = Field(..., description="상품명 (HTML 태그 포함)")
    link: str = Field(..., description="쇼핑몰 링크")
    lprice: int = Field(..., description="최저가")
    mall_name: str = Field(..., description="판매 쇼핑몰 이름")
    brand: Optional[str] = Field(None, description="브랜드")
    maker: Optional[str] = Field(None, description="제조사")
    category1: Optional[str] = Field(None, description="대분류")
    category2: Optional[str] = Field(None, description="중분류")
    category3: Optional[str] = Field(None, description="소분류")
    category4: Optional[str] = Field(None, description="세분류")

class ProductSearchResponse(BaseModel):
    search_keyword: str = Field(..., description="검색 키워드")
    result_code: str = Field("SUCCESS", description="결과 코드")
    total_count: int = Field(..., description="전체 검색 결과 수")
    # 여기도 변경된 이름(SearchProductItem)을 쓰도록 수정했습니다.
    items: List[SearchProductItem] = Field(..., description="상품 목록")

# 가격 업데이트 관련
class PriceUpdateRequest(BaseModel):
    item_id: int = Field(..., description="갱신할 상품의 고유 식별자 (BigInteger)")
    price: int = Field(..., description="새로운 가격")

class PriceUpdateData(BaseModel):
    product_id: str = Field(..., description="상품 ID")
    title: str = Field(..., description="상품명")
    new_price: int = Field(..., description="갱신된 가격")
    old_price: int = Field(..., description="이전 가격")
    diff_amount: int = Field(..., description="가격 차이 (새 가격 - 옛 가격)")
    diff_rate: float = Field(..., description="할인율/변동률 (%)")
    updated_at: datetime = Field(..., description="업데이트 일시")

class PriceUpdateResponse(BaseModel):
    result_code: str = Field("SUCCESS", description="결과 코드")
    message: str = Field(..., description="메시지")
    data: PriceUpdateData