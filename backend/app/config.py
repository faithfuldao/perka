from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str

    # ── S3 / Cloudflare R2 ────────────────────────────────────
    S3_BUCKET: str = "perka-assets"
    S3_REGION: str = "auto"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = ""

    # ── Apple Wallet ──────────────────────────────────────────
    APPLE_TEAM_ID: str = ""
    APPLE_CERT_ENCRYPTION_KEY: str = ""
    APPLE_CERT_P12_PATH: str = ""
    APPLE_CERT_PASSWORD: str = ""
    APPLE_WWDR_CERT_PATH: str = ""
    API_BASE_URL: str = "http://localhost:8000"

    # ── Google Wallet ─────────────────────────────────────────
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = ""

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
