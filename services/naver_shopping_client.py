# services/naver_shopping_client.py
from __future__ import annotations

import re
from html import unescape
from typing import Any, Dict


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
    정책(옵션 A): 비정상 값이면 예외 발생
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

    # image_url / mall_name은 비어도 서비스 동작은 가능하니 빈 문자열 허용
    image_url = raw_image.strip() if isinstance(raw_image, str) else ""
    mall_name = raw_mall.strip() if isinstance(raw_mall, str) else ""

    price = parse_price_to_int(raw_price, field_name="lprice")

    # 표준 dict
    return {
        "title": title,
        "product_url": product_url,  # ERD의 items.product_url에 맞춰 key를 이렇게 둠
        "image_url": image_url,
        "mall_name": mall_name,
        "price": price,              # int 고정
    }