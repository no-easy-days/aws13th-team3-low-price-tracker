from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, ConfigDict


# =========================================================
# 공통 Config
# - from_attributes: ORM 객체 -> Pydantic 변환 가능
# - populate_by_name: alias/필드명 혼용 입력 허용
# =========================================================
ORM_CONFIG = ConfigDict(from_attributes=True, populate_by_name=True)


# =========================================================
# Auth / User
# =========================================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ORM_CONFIG

    id: int
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# =========================================================
# 외부 API "정제 결과" 표준 스키마 (normalize_naver_item 결과와 1:1)
# - 네 코드의 normalize_naver_item()이 반환하는 dict와 정확히 맞음
# =========================================================
class NormalizedProduct(BaseModel):
    external_id: str
    title: str
    product_url: str
    image_url: Optional[str] = ""
    mall_name: Optional[str] = ""
    price: int


# =========================================================
# API 응답용 ProductItem
# - 팀에서 원했던 필드명(product_id, link, lprice 등)을 유지하되
# - 입력은 정제 결과(external_id, product_url, price 등)도 그대로 받게 alias 처리
# =========================================================
class ProductItem(BaseModel):
    model_config = ORM_CONFIG

    product_id: str = Field(..., validation_alias="external_id", description="네이버 상품 ID")
    title: str = Field(..., description="상품명")
    link: HttpUrl = Field(..., validation_alias="product_url", description="네이버 쇼핑 링크")
    lprice: int = Field(..., validation_alias="price", description="현재 최저가(int)")
    mall_name: Optional[str] = Field(None, description="판매처 이름")
    image: Optional[HttpUrl] = Field(None, validation_alias="image_url", description="상품 이미지 URL")

class ProductsGetResponse(BaseModel):
    result_code: str = Field("SUCCESS", description="결과 코드")
    total_count: int = Field(..., description="전체 상품 수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 당 개수")
    items: List[ProductItem] = Field(..., description="상품 목록")


# =========================================================
#  DB(ERD) 응답용 스키마들
# - Wishlist 라우터가 ORM 객체(list of models.Wishlist)를 그대로 반환해도 깨지지 않게 설계
# - item 정보까지 내려주고 싶어서 WishlistItemOut에 item(중첩) 포함
# =========================================================
class ItemOut(BaseModel):
    model_config = ORM_CONFIG

    id: int
    external_id: str
    title: str
    product_url: str
    image_url: Optional[str] = None
    mall_name: Optional[str] = None

    initial_price: int
    last_seen_price: Optional[int] = None
    min_price: Optional[int] = None
    last_checked_at: Optional[datetime] = None
    is_active: int
    created_at: datetime


class WishlistItemOut(BaseModel):
    model_config = ORM_CONFIG

    # DB wishlist 테이블 컬럼에 맞춤
    id: int
    user_id: int
    item_id: int
    is_active: int
    created_at: datetime

    # relationship: Wishlist.item (있으면 같이 내려감)
    item: Optional[ItemOut] = None


class WishlistListResponse(BaseModel):
    result_code: str = Field("SUCCESS", description="결과 코드")
    total_count: int = Field(..., description="전체 아이템 수")
    user_id: int = Field(..., description="유저 ID")

    # ORM Wishlist 리스트가 그대로 들어와도 파싱 가능
    wishlist_items: List[WishlistItemOut] = Field(..., description="아이템 목록")

# 알람
AlertType = Literal["TARGET_PRICE", "DROP_FROM_PREV", "NEW_LOW"]

class AlertCreate(BaseModel):
    wishlist_id: int = Field(..., description="wishlist PK")
    alert_type: AlertType = Field(..., description="알림 타입")
    target_price: Optional[int] = Field(None, description="TARGET_PRICE일 때 목표가")

class AlertOut(BaseModel):
    id: int
    wishlist_id: int
    alert_type: str
    target_price: Optional[int]
    is_enabled: int
    last_triggered_ph_id: Optional[int]
    last_triggered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class AlertToggle(BaseModel):
    is_enabled: int = Field(..., description="1=enabled, 0=disabled")