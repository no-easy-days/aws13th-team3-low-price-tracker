# services/naver_shopping_client.py
from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, List

import requests
from settings import settings


class DataCleaningError(ValueError):
    """네이버 쇼핑 응답 데이터 정제 단계에서 기대 형태가 아닐 때 발생."""


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_title(raw_title: Any) -> str:
    """
    title 정제:
    - HTML 엔티티 디코딩 (&quot; → ")
    - HTML 태그 제거 (<b>...</b> 등)
    - trim
    정책(옵션 A): 비정상 값이면 예외 발생
    """
    if raw_title is None:
        raise DataCleaningError("title is None")

    if not isinstance(raw_title, str):
        raise DataCleaningError(f"title is not a string: type={type(raw_title)} value={raw_title!r}")

    s = unescape(raw_title)          # HTML 엔티티 디코딩
    s = _HTML_TAG_RE.sub("", s)      # 태그 제거
    s = s.strip()

    if not s:
        raise DataCleaningError(f"title is empty after cleaning: raw={raw_title!r}")

    return s


def parse_price_to_int(raw_price: Any, *, field_name: str = "lprice") -> int:
    """
    가격 정제:
    - 문자열/정수 입력을 int로 통일
    - 빈 값/비숫자/음수면 예외
    정책: 비정상 값이면 예외 발생
    """
    if raw_price is None:
        raise DataCleaningError(f"{field_name} is None")

    if isinstance(raw_price, int):
        if raw_price < 0:
            raise DataCleaningError(f"{field_name} is negative: {raw_price}")
        return raw_price

    if isinstance(raw_price, str):
        s = raw_price.strip()
        if not s:
            raise DataCleaningError(f"{field_name} is empty string")

        # 콤마 제거 (혹시 들어오는 케이스)
        s = s.replace(",", "")

        if not s.isdigit():
            raise DataCleaningError(f"{field_name} is not numeric: raw={raw_price!r}")

        price = int(s)
        if price < 0:
            raise DataCleaningError(f"{field_name} parsed negative: raw={raw_price!r} -> {price}")
        return price

    raise DataCleaningError(f"{field_name} has unsupported type: type={type(raw_price)} value={raw_price!r}")


def normalize_naver_item(naver_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    네이버 쇼핑 item(dict) 1개를 DB(ERD) 친화적인 표준 dict로 변환.
    ERD 매핑 기준:
      - title      -> items.title
      - link       -> items.product_url
      - image      -> items.image_url
      - mallName   -> items.mall_name
      - lprice     -> items.initial_price / last_seen_price / min_price 용 (int)

    필수 필드가 누락/비정상이면 예외 발생
    """
    if not isinstance(naver_item, dict):
        raise DataCleaningError(f"naver_item is not dict: type={type(naver_item)} value={naver_item!r}")

    raw_title = naver_item.get("title")
    raw_link = naver_item.get("link")
    raw_image = naver_item.get("image")
    raw_mall = naver_item.get("mallName")
    raw_price = naver_item.get("lprice")

    title = clean_title(raw_title)

    if raw_link is None or not isinstance(raw_link, str) or not raw_link.strip():
        raise DataCleaningError(f"link is missing/invalid: raw={raw_link!r}")
    product_url = raw_link.strip()

    external_id = extract_external_id(product_url)

    # image_url / mall_name은 비어도 서비스 동작은 가능하니 빈 문자열 허용
    image_url = raw_image.strip() if isinstance(raw_image, str) else ""
    mall_name = raw_mall.strip() if isinstance(raw_mall, str) else ""

    price = parse_price_to_int(raw_price, field_name="lprice")

    # 표준 dict
    return {
        "external_id": external_id,
        "title": title,
        "product_url": product_url,  # ERD의 items.product_url에 맞춰 key를 이렇게 둠
        "image_url": image_url,
        "mall_name": mall_name,
        "price": price,              # int 고정
    }



class NaverAPIError(RuntimeError):
    """네이버 쇼핑 API 호출 자체가 실패했을 때 발생(인증/제한/서버/응답형식 오류 등)."""


NAVER_SHOPPING_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"


def _build_naver_headers() -> Dict[str, str]:
    cid = getattr(settings, "NAVER_CLIENT_ID", None)
    secret = getattr(settings, "NAVER_CLIENT_SECRET", None)

    if not cid or not secret:
        raise NaverAPIError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET is missing in settings")

    return {
        "X-Naver-Client-Id": cid,
        "X-Naver-Client-Secret": secret,
    }


def search_products(
    query: str,
    *,
    display: int = 10,
    start: int = 1,
    sort: str = "sim",
    timeout: float = 5.0,
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """
    네이버 쇼핑 검색 API 호출 후 items를 normalize_naver_item()로 정제해 리스트로 반환.

    실패 정책:
    - API 호출 실패(401/429/5xx/네트워크 등): NaverAPIError (전체 실패)
    - item 정제 실패(DataCleaningError):
        - strict=False(기본): 해당 item만 제외하고 계속
        - strict=True: 예외를 그대로 올려 전체 실패(문제 즉시 발견)
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if not (1 <= display <= 100):
        raise ValueError("display must be between 1 and 100")
    if start < 1:
        raise ValueError("start must be >= 1")

    params = {
        "query": query.strip(),
        "display": display,
        "start": start,
        "sort": sort,
    }

    try:
        resp = requests.get(
            NAVER_SHOPPING_SEARCH_URL,
            headers=_build_naver_headers(),
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise NaverAPIError(f"Naver API request failed: {e!r}") from e

    # status code 처리
    if resp.status_code == 200:
        pass
    elif resp.status_code in (401, 403):
        raise NaverAPIError("Naver API auth failed (401/403): check client id/secret")
    elif resp.status_code == 429:
        raise NaverAPIError("Naver API rate limit exceeded (429)")
    else:
        body_preview = (resp.text or "")[:300]
        raise NaverAPIError(f"Naver API error: status={resp.status_code}, body={body_preview!r}")

    # JSON 파싱/shape 검증
    try:
        data = resp.json()
    except ValueError as e:
        raise NaverAPIError(f"Invalid JSON response: {e!r}") from e

    items = data.get("items")
    if not isinstance(items, list):
        raise NaverAPIError(f"Unexpected response shape: items is not a list (got {type(items)})")

    normalized: List[Dict[str, Any]] = []

    for it in items:
        try:
            normalized.append(normalize_naver_item(it))
        except DataCleaningError as e:
            if strict:
                raise
            continue

    return normalized

def refresh_product_price(
    *,
    query: str,
    product_url: str,
    timeout: float = 5.0,
) -> int:
    if not query:
        raise ValueError("query is empty")
    if not product_url:
        raise ValueError("product_url is empty")

    items = search_products(
        query=query,
        display=20,  # 검색 순위 변동 대비 여유 확보
        strict=False,
        timeout=timeout,
    )

    for item in items:
        if item["product_url"] == product_url:
            return item["price"]

    raise NaverAPIError(
        f"Product not found in search results during refresh "
        f"(query={query}, product_url={product_url})"
    )

_ID_RE = re.compile(r"/(catalog|products)/(\d+)")

def extract_external_id(product_url: str) -> str:
    m = _ID_RE.search(product_url)
    if not m:
        raise DataCleaningError(
            f"cannot extract external_id from url: {product_url!r}"
        )
    return m.group(2)