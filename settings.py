# settings.py
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env에서 읽을 값들
    NAVER_CLIENT_ID: str
    NAVER_CLIENT_SECRET: str

    # DB_HOST: str
    # DB_PORT: int
    # ...

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 다른 값이 있어도 무시
    )


settings = Settings()