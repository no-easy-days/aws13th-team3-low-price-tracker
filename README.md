## Database Schema Overview

본 프로젝트는 가격 추적 및 알림 서비스를 목표로 하며,
사용자, 상품, 가격 이력, 알림을 분리된 테이블 구조로 설계하였다.

### users

사용자 계정 정보를 관리하는 테이블이다.  
인증과 권한의 기준이 되며, 위시리스트와 알림의 소유 주체가 된다.

- id: 사용자 고유 식별자(PK)
- email: 로그인에 사용되는 이메일 주소 (중복 불가)
- password_hash: 비밀번호 해시 값
- created_at: 사용자 계정 생성 시점

---

### items

가격 추적 대상이 되는 상품 정보를 관리하는 테이블이다.  
여러 사용자가 동일한 상품을 공유할 수 있으며, 가격 이력의 기준 엔티티이다.

- id: 상품 고유 식별자(PK)
- external_id: 외부 쇼핑몰 상품 고유 ID
- title: 상품명
- image_url: 상품 이미지 URL
- product_url: 상품 상세 페이지 URL
- mall_name: 쇼핑몰 이름
- initial_price: 최초 등록 시 가격
- last_seen_price: 가장 최근에 확인된 가격
- min_price: 지금까지 기록된 최저가
- last_checked_at: 마지막 가격 수집 시각
- is_active: 가격 추적 활성 여부
- created_at: 상품 등록 시점

---

### wishlist

사용자와 상품 간의 관계를 관리하는 테이블이다.  
사용자가 관심 있는 상품 목록을 표현하며, 알림 설정의 기준 단위가 된다.

- id: 위시리스트 항목 고유 식별자(PK)
- user_id: 위시리스트를 소유한 사용자 ID
- item_id: 관심 상품 ID
- created_at: 위시리스트 추가 시점
- is_active: 위시리스트 활성 여부

---

### price_history

상품의 가격 변동 이력을 저장하는 테이블이다.  
가격 그래프, 하락 감지, 최저가 판단, 알림 트리거의 근거 데이터로 사용된다.

- id: 가격 이력 고유 식별자(PK)
- item_id: 가격이 수집된 상품 ID
- price: 해당 시점의 상품 가격
- checked_at: 가격 수집 시각

---

### alerts

가격 알림 조건과 상태를 관리하는 테이블이다.  
사용자별, 상품별 알림 규칙을 정의하고 중복 알림을 방지한다.

- id: 알림 고유 식별자(PK)
- wishlist_id: 알림이 설정된 위시리스트 ID
- alert_type: 알림 조건 유형  
  - TARGET_PRICE: 목표 가격 도달 시  
  - DROP_FROM_PREV: 직전 가격 대비 하락 시  
  - NEW_LOW: 역대 최저가 갱신 시
- target_price: 목표 가격 (TARGET_PRICE 유형에서 사용)
- is_enabled: 알림 활성 여부
- last_triggered_ph_id: 마지막으로 알림을 발생시킨 가격 이력 ID
- last_triggered_at: 마지막 알림 발송 시각
- created_at: 알림 생성 시점

---

### Table Relationships

- users : wishlist = 1 : N
- items : wishlist = 1 : N
- items : price_history = 1 : N
- wishlist : alerts = 1 : N
- alerts : price_history = 1 : 0..1 (마지막 트리거 기준)

---

### Design Considerations

- 사용자, 상품, 가격 이력, 알림을 명확히 분리하여 확장성과 유지보수성을 확보하였다.
- 가격 수집 로직과 알림 로직을 분리하여 배치 처리에 적합한 구조로 설계하였다.
- 가격 이력 기반 알림 중복 발생을 방지하기 위해 마지막 트리거 정보를 관리한다.
