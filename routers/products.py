import os
import requests

from fastapi import APIRouter, HTTPException, Query
from schemas import ProductsGetResponse  # 너가 만든 스키마 이름에 맞춰 수정

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "/search",
    response_model=ProductsGetResponse,
    summary="네이버 쇼핑 상품 검색",
)
def search_products(
    query: str = Query(..., description="검색어 (UTF-8 인코딩)"),
    display: int = Query(10, ge=1, le=100, description="표시 개수(기본 10, 최대 100)"),
    start: int = Query(1, ge=1, le=1000, description="검색 시작 위치(기본 1, 최대 1000)"),
    sort: str = Query("sim", description="정렬(sim/date/asc/dsc)"),
    filter: str | None = Query(None, description="필터(예: naverpay)"),
    exclude: str | None = Query(None, description="제외 옵션(예: used:cbshop)"),
):
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="NAVER API 키가 설정되어 있지 않습니다.")

    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort,
    }
    if filter:
        params["filter"] = filter
    if exclude:
        params["exclude"] = exclude

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"네이버 API 호출 실패: {e}")
