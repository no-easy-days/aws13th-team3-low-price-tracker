
from pydantic import BaseModel, EmailStr, HttpUrl

## Auth
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

## User

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True

## Token
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# 위시리스트 조회 스키마 정의
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

class ProductItemOut(BaseModel):
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
    items: List[ProductItemOut] = Field(..., description="상품 목록")