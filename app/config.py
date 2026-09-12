"""
Central typed configuration, loaded from environment variables / .env.
Same shape as the trading-bot project's engine/config.py -- pydantic
Settings, fresh instance per get_settings() call so tests can monkeypatch
environment variables cleanly.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./signalroom.db"

    jwt_secret: str = ""
    jwt_refresh_secret: str = ""

    # No public admin signup -- the one founder/trader account is
    # bootstrapped from these on first startup, same pattern as the
    # trading-bot project's api/bootstrap.py.
    admin_email: str = ""
    admin_password: str = ""

    # How many extra 30s steps either side of "now" a TOTP code stays
    # valid for (pyotp's valid_window). 1 = ~90s total, the RFC-typical
    # choice.
    totp_valid_window: int = 1

    # Retention rule (matches growthclubpk.com's own stated policy):
    # a bot-enabled member with no executed trade in this many days can
    # have their access flagged for review.
    inactivity_revoke_days: int = 14

    log_level: str = "INFO"
    environment: str = "development"


def get_settings() -> Settings:
    return Settings()
