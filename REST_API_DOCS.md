# REST_API 명세서

네이버 API

[https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md](https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md)

---

### 네이버 API 참고사항

API를 요청할 때 다음 예와 같이 HTTP 요청 헤더에 [**클라이언트 아이디와 클라이언트 시크릿**](https://developers.naver.com/docs/common/openapiguide/appregister.md#%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%96%B8%ED%8A%B8-%EC%95%84%EC%9D%B4%EB%94%94%EC%99%80-%ED%81%B4%EB%9D%BC%EC%9D%B4%EC%96%B8%ED%8A%B8-%EC%8B%9C%ED%81%AC%EB%A6%BF-%ED%99%95%EC%9D%B8)을 추가해야 합니다.

```bash
> GET/v1/search/shop.xml?query=%EC%A3%BC%EC%8B%9D&display=10&start=1&sort=sim HTTP/1.1
>Host: openapi.naver.com
>User-Agent: curl/7.49.1
>Accept:*/*
> X-Naver-Client-Id:{xxxxxxx}
> X-Naver-Client-Secret:{xxxxxxxx}
```

### 요청 예시

```bash
curl"https://openapi.naver.com/v1/search/blog.xml?query=%EB%A6%AC%EB%B7%B0&display=10&start=1&sort=sim" \
-H"X-Naver-Client-Id: {애플리케이션 등록 시 발급받은 클라이언트 아이디 값}" \
-H"X-Naver-Client-Secret: {애플리케이션 등록 시 발급받은 클라이언트 시크릿 값}"-v
```

---

### 네이버 API 파라미터 종류

| **파라미터** | **타입** | **필수 여부** | **설명** |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |
| filter | String | ❌ | 검색 결과에 포함할 상품 유형- 설정 안 함: 모든 상품(기본값)- `naverpay`: 네이버페이 연동 상품 |
| exclude | String | ❌ | 검색 결과에서 제외할 상품 유형.
 `exclude={option}:{option}:{option}` 형태로 설정합니다(예: `exclude=used:cbshop`).
- `used`: 중고
- `rental`: 렌탈
- `cbshop`: 해외직구, 구매대행 |

---

### **구현할 기능**

| **기능** | **설명** | **기술 포인트** |
| --- | --- | --- |
| 상품 검색 | 키워드로 네이버 쇼핑 검색 | requests, 헤더에 인증 정보 포함 |
| 위시리스트 등록 | 원하는 상품을 내 DB에 저장 | INSERT |
| 가격 추적 | 저장된 상품의 현재가를 다시 조회해서 기록 | 1:N 관계 (상품-가격히스토리) |
| 가격 변동 조회 | 가격이 떨어진 상품만 필터링 | 비교 로직, 서브쿼리 |

### 구현할 엔드포인트

- `GET /products/search?query=맥북에어` - 네이버 쇼핑에서 검색
- `POST /wishlist` - 위시리스트에 상품 추가
- `GET /wishlist` - 내 위시리스트 조회
- `POST /wishlist/refresh` - 위시리스트 상품들의 현재가 업데이트
- `GET /wishlist/drops` - 가격이 떨어진 상품만 조회

---

### URL 설계

| 동작 | HTTP 메서드 | URL | 설명 |
| --- | --- | --- | --- |
| 상품 검색 | GET | `/products` | 사용자가 원하는 상품 |
| 위시리스트 조회 | GET | `/wishlist` | 전체 위시리스트 목록 |
| 위시리스트 상품 추가 | POST | `/wishlist` | 위시리스트에 상품 추가 |
| 위시리스트 상품 삭제 | DELETE | `/wishlist` | 위시리스트에서 상품 삭제 |
| 최저가 상품 조회 | GET | `/wishlist/drops` | 가격이 떨어진 상품을 조회 |
| 상품 가격 업데이트 | POST | `/wishlist/refresh` | 위시리스트 상품들의 현재가 업데이트 |

---

# REST API 명세

### 상품 검색

**GET** `/products`

**Query Parameters**

| **파라미터** | **타입** | **필수 여부** | **설명** |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |

**Response (200 OK)**

```python
{
  "lastBuildDate": "Wed, 04 Feb 2026 17:10:00 +0900",
  "total": 45000,
  "start": 1,
  "display": 1,
  "items": [
    {
      "title": "저소음 갈축 <b>키보드</b> 커스텀 기계식 유선",
      "link": "https://search.shopping.naver.com/catalog/12345",
      "lprice": "89000",
      "hprice": "120000",
      "mallName": "네이버 스토어",
      "product_id": "88223344",
      "productType": "1",
      "maker": "키보드메이커",
      "brand": "타이핑마스터",
      "category1": "디지털/가전",
      "category2": "주변기기",
      "category3": "키보드",
      "category4": "기계식키보드"
    }
  ]
}
```

### 위시리스트 조회

**GET** `/wishlist`

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |

**Response (200 OK)**

```python
HTTP/1.1 200 OK
Server: uvicorn
Date: Wed, 04 Oct 2023 09:04:44 GMT
Content-Type: application/json;charset=utf-8
Content-Length: 452
Connection: keep-alive

{
  "result_code": "SUCCESS",
  "total_count": 2,
  "user_id": 000000
  "wishlist_items": [
    {
      "wishlist_id": 101,
      "items_id": "8234567890",
      "title": "토체프 D&T 콜라보 저소음 적축 웜톤베이지",
      "link": "https://search.shopping.naver.com/gate.nhn?id=8234567890",
      "lprice": 159000,
      "initial_price": 165000,
      "mall_name": "네이버 스토어",
      "brand": "씽크웨이",
      "category1": "디지털/가전",
      "category2": "PC주변기기",
      "category3": "키보드",
      "created_at": "2023-10-01T10:00:00"
    },
    {
      "wishlist_id": 102,
      "product_id": "9876543210",
      "title": "리얼포스 R3 하이브리드 저소음 45g 균등 블랙",
      "link": "https://search.shopping.naver.com/gate.nhn?id=9876543210",
      "lprice": 395000,
      "initial_price": 380000,
      "mall_name": "리더스키",
      "brand": "리얼포스",
      "category1": "디지털/가전",
      "category2": "PC주변기기",
      "category3": "키보드",
      "created_at": "2023-10-03T14:30:00"
    }
  ]
}
```

### 위시리스트 상품 추가

**POST** `/wishlist`

**Query Parameters**

| **파라미터** | **타입** | **필수 여부** | **설명** |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |

**Request Body**

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| product_id | Biginteger | ✅ | 추가할 상품의 아이디입니다. |
| image | HttpUrl | ❌ | 추가할 상품의 이미지입니다. |

**RESPONSE (200 OK)**

```jsx
{
  "result_code": "SUCCESS",
  "message": "상품이 위시리스트에 성공적으로 등록되었습니다.",
  "data": {
    "product_id": "8472910356",
    "title": "COX CK87 게이트론 LED 게이밍 기계식 키보드",
    "link": "https://search.shopping.naver.com/catalog/32824317618",
    "image": "https://shopping-phinf.pstatic.net/main_3282431/32824317618.20220615111912.jpg",
    "lprice": 1390000,
    "mall_name": "리더스키",
    "brand": "COX",
    "category1": "디지털/가전",
    "category2": "PC주변기기",
    "category3": "키보드",,
    "created_at": "2026-02-05T10:00:00"
  }
}

```

### 위시리스트 삭제

**DELETE** `/wishlist`

**Query Parameters**

| **파라미터** | **타입** | **필수 여부** | **설명** |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |

**RESPONSE (200 OK)**

```jsx
{
  "result_code": "SUCCESS",
  "message": "위시리스트에서 해당 상품이 삭제되었습니다.",
  "data": {
    "product_id": "8472910356",
    "title": "COX CK87 게이트론 LED 게이밍 기계식 키보드"
  }
}

```

### 최저가 상품 조회

**GET** `/wishlist/drops`

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| query | String | ✅ | 검색어. UTF-8로 인코딩되어야 합니다. |
| display | Integer | ❌ | 한 번에 표시할 검색 결과 개수(기본값: 10, 최댓값: 100) |
| start | Integer | ❌ | 검색 시작 위치(기본값: 1, 최댓값: 1000) |
| sort | String | ❌ | 검색 결과 정렬 방법
- `sim`: 정확도순으로 내림차순 정렬(기본값)
- `date`: 날짜순으로 내림차순 정렬
- `asc`: 가격순으로 오름차순 정렬
- `dsc`: 가격순으로 내림차순 정렬 |

Response (200 OK)

```python
HTTP/1.1 200 OK
Content-Type: application/json;charset=utf-8
Content-Length: 624
Connection: keep-alive

{
  "search_keyword": "키보드",
  "result_code": "SUCCESS",
  "total_count": 285400,
  "items": [
    {
      "product_id": "82495671234",
      "title": "로지텍 MX KEYS S 무선 일루미네이티드 <b>키보드</b>",
      "link": "https://search.shopping.naver.com/gate.nhn?id=82495671234",
      "lprice": 139000,
      "mall_name": "네이버 스토어",
      "brand": "로지텍",
      "maker": "로지텍",
      "category1": "디지털/가전",
      "category2": "PC주변기기",
      "category3": "키보드",
      "category4": "무선키보드"
    },
    {
      "product_id": "21345678901",
      "title": "COX CK87 게이트론 LED 게이밍 기계식 <b>키보드</b> (갈축)",
      "link": "https://search.shopping.naver.com/gate.nhn?id=21345678901",
      "lprice": 45900,
      "mall_name": "쿠팡",
      "brand": "COX",
      "maker": "앱코",
      "category1": "디지털/가전",
      "category2": "PC주변기기",
      "category3": "키보드",
      "category4": "기계식키보드"
    }
  ]
}
```

### 상품 가격 업데이트

**GET** `/wishlist`

Request Body

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| item_id | Biginteger | ✅ | 새롭게 갱신되는 상품의 고유 식별자입니다. |
| price | Integer | ✅ | 상품에 대한 가격입니다. 가격이 현재가에서 더 떨어지지 않았다면 그대로 유지됩니다. |

```python
HTTP/1.1 200 OK
Content-Type: application/json;charset=utf-8
Content-Length: 512
Connection: keep-alive

{
  "result_code": "SUCCESS",
  "message": "가격 정보가 최신화되었습니다.",
  "data": {
    "product_id": "9876543210",
    "title": "리얼포스 R3 하이브리드 저소음 45g 균등 블랙",
    "new_price": 379000,
    "old_price": 395000,
    "diff_amount": -16000,
    "diff_rate": -4.05,
    "updated_at": "2026-02-04T19:20:00"
  }
}
```

---