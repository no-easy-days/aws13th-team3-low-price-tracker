from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from services.shopping_service import refresh_wishlist_prices
from services.naver_shopping_client import (
    search_and_save_pages,
    KEYBOARD_CATEGORY_ID,
)

from routers.auth import router as auth_router
from routers.shopping_alert import router as shopping_alert_router
from routers.wishlist_ref import router as wishlist_ref_router


scheduler = BackgroundScheduler(timezone="Asia/Seoul")

# ✅ 수집(아이템 채우기) 설정
COLLECT_QUERY = os.getenv("COLLECT_QUERY", "기계식 키보드")
COLLECT_TOTAL_PER_RUN = int(os.getenv("COLLECT_TOTAL_PER_RUN", "100"))  # ✅ 10분마다 목표 수집 개수
COLLECT_PAGE_SIZE = int(os.getenv("COLLECT_PAGE_SIZE", "50"))          # ✅ 호출 1회당 display(1~100)


def job_collect_items():
    """
    ✅ 10분마다 items를 계속 채우는 수집 배치:
    - 키보드 카테고리만
    - query로 여러 페이지를 돌려 total개까지 upsert + price_history 기록
    """
    db = SessionLocal()
    try:
        saved = search_and_save_pages(
            db,
            query=COLLECT_QUERY,
            category=KEYBOARD_CATEGORY_ID,
            total=COLLECT_TOTAL_PER_RUN,
            page_size=COLLECT_PAGE_SIZE,
            sort="sim",
            strict=False,
        )
        print(f"[collector] collected {saved} items (query={COLLECT_QUERY!r})")
    except Exception as e:
        print("[collector] error:", repr(e))
    finally:
        db.close()


def job_refresh_prices():
    """
    (선택) wishlist 기반 가격 갱신 배치
    - wishlist 미구현이면 updated=0이어도 정상
    """
    db = SessionLocal()
    try:
        updated = refresh_wishlist_prices(db)
        print(f"[scheduler] refreshed {updated} items")
    except Exception as e:
        print("[scheduler] error:", repr(e))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ✅ 서버 시작 시 1회 수집
    job_collect_items()

    # ✅ 서버 시작 시 1회 갱신(원하면 유지)
    job_refresh_prices()

    # ✅ 이후 10분마다 수집
    scheduler.add_job(
        job_collect_items,
        "interval",
        minutes=10,
        id="item_collect",
        replace_existing=True,
    )

    # ✅ 이후 10분마다 wishlist 갱신(원하면 유지)
    scheduler.add_job(
        job_refresh_prices,
        "interval",
        minutes=10,
        id="price_refresh",
        replace_existing=True,
    )

    scheduler.start()
    print("[scheduler] started (every 10 minutes)")

    yield

    scheduler.shutdown()
    print("[scheduler] stopped")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(shopping_alert_router)
app.include_router(wishlist_ref_router)
