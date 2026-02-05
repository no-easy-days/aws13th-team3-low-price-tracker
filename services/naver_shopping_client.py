# services/naver_shopping_client.py
from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict, List

import requests
from sqlalchemy.orm import Session

from crud import upsert_item_from_naver, insert_price_history, update_min_price_last_7d
from settings import settings

KEYBOARD_CATEGORY_ID = "50000151"


class DataCleaningError(ValueError):
    """네이버 쇼핑 응답 데이터 정제 단계에서 기대 형태가 아닐 때 발생."""


_HTML_TAG_RE = re.compile(r"<[^>]+>")


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


def clean_title(raw_title: Any) -> str:
    if raw_title is None:
        raise DataCleaningError("title is None")
    if not isinstance(raw_title, str):
        raise DataCleaningError(f"title is not a string: type={type(raw_title)} value={raw_title!r}")

    s = unescape(raw_title)
    s = _HTML_TAG_RE.sub("", s)
    s = s.strip()

    if not s:
        raise DataCleaningError(f"title is empty after cleaning: raw={raw_title!r}")
    return s


def parse_price_to_int(raw_price: Any, *, field_name: str = "lprice") -> int:
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
        s = s.replace(",", "")
        if not s.isdigit():
            raise DataCleaningError(f"{field_name} is not numeric: raw={raw_price!r}")
        price = int(s)
        if price < 0:
            raise DataCleaningError(f"{field_name} parsed negative: raw={raw_price!r} -> {price}")
        return price

    raise DataCleaningError(f"{field_name} has unsupported type: type={type(raw_price)} value={raw_price!r}")


_ID_RE = re.compile(r"/(catalog|products)/(\d+)")


def extract_external_id(product_url: str) -> str:
    m = _ID_RE.search(product_url)
    if not m:
        raise DataCleaningError(f"cannot extract external_id from url: {product_url!r}")
    return m.group(2)


def normalize_naver_item(naver_item: Dict[str, Any]) -> Dict[str, Any]:
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

    image_url = raw_image.strip() if isinstance(raw_image, str) else ""
    mall_name = raw_mall.strip() if isinstance(raw_mall, str) else ""

    price = parse_price_to_int(raw_price, field_name="lprice")

    return {
        "external_id": external_id,
        "title": title,
        "product_url": product_url,
        "image_url": image_url,
        "mall_name": mall_name,
        "price": price,
    }


def search_products(
    query: str,
    *,
    category: str | None = None,
    display: int = 10,
    start: int = 1,
    sort: str = "sim",
    timeout: float = 5.0,
    strict: bool = False,
) -> List[Dict[str, Any]]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    if not (1 <= display <= 100):
        raise ValueError("display must be between 1 and 100")
    if start < 1:
        raise ValueError("start must be >= 1")

    if category is None:
        category = KEYBOARD_CATEGORY_ID

    params = {
        "query": query.strip(),
        "display": display,
        "start": start,
        "sort": sort,
        "category": category,
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

    if resp.status_code == 200:
        pass
    elif resp.status_code in (401, 403):
        raise NaverAPIError("Naver API auth failed (401/403): check client id/secret")
    elif resp.status_code == 429:
        raise NaverAPIError("Naver API rate limit exceeded (429)")
    else:
        body_preview = (resp.text or "")[:300]
        raise NaverAPIError(f"Naver API error: status={resp.status_code}, body={body_preview!r}")

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
        except DataCleaningError:
            if strict:
                raise
            continue

    return normalized


def search_and_save_pages(
    db: Session,
    *,
    query: str,
    category: str | None = None,
    total: int = 100,
    page_size: int = 50,
    sort: str = "sim",
    strict: bool = False,
) -> int:
    """
    ✅ '수집 배치'용:
    네이버 쇼핑 검색을 여러 페이지(start)로 돌려서 total개까지 수집/저장(upsert)한다.
    - total: 목표 수집 개수
    - page_size: 한 번 호출당 display (1~100)
    """
    if category is None:
        category = KEYBOARD_CATEGORY_ID

    if total < 1:
        return 0
    if not (1 <= page_size <= 100):
        raise ValueError("page_size must be between 1 and 100")

    saved_total = 0
    start = 1

    while saved_total < total:
        display = min(page_size, total - saved_total)
        items = search_products(
            query=query,
            category=category,
            display=display,
            start=start,
            sort=sort,
            strict=strict,
        )

        for data in items:
            item = upsert_item_from_naver(db, data)
            insert_price_history(db, item.id, data["price"])
            update_min_price_last_7d(db, item)

        db.commit()

        saved_total += len(items)
        start += display  # 다음 페이지로 이동 (1-base)

        if len(items) == 0:
            break

    return saved_total


def refresh_product_price(
    *,
    query: str,
    product_url: str,
    category: str | None = None,
    timeout: float = 5.0,
) -> int:
    if not query:
        raise ValueError("query is empty")
    if not product_url:
        raise ValueError("product_url is empty")

    if category is None:
        category = KEYBOARD_CATEGORY_ID

    items = search_products(
        query=query,
        category=category,
        display=20,
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

