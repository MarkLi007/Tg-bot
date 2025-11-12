"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    """Container for runtime configuration."""

    token: str
    db_path: str
    message_point: int
    daily_signin_bonus: int
    throttle_seconds: int


def _parse_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value: {value}") from exc


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    db_path = os.getenv("DB_PATH", "points.db").strip() or "points.db"
    message_point = _parse_int(os.getenv("MESSAGE_POINT"), default=1)
    daily_signin_bonus = _parse_int(os.getenv("DAILY_SIGNIN_BONUS"), default=10)
    throttle_seconds = _parse_int(os.getenv("THROTTLE_SECONDS"), default=5)
    settings = Settings(
        token=token,
        db_path=db_path,
        message_point=message_point,
        daily_signin_bonus=daily_signin_bonus,
        throttle_seconds=throttle_seconds,
    )
    validate(settings)
    return settings


def validate(settings: Settings) -> None:
    if not settings.token:
        raise ValueError("TELEGRAM_TOKEN is required. Please set it in your environment.")
    if settings.message_point < 0:
        raise ValueError("MESSAGE_POINT must be non-negative.")
    if settings.daily_signin_bonus < 0:
        raise ValueError("DAILY_SIGNIN_BONUS must be non-negative.")
    if settings.throttle_seconds < 0:
        raise ValueError("THROTTLE_SECONDS must be non-negative.")


settings = load_settings()
TOKEN = settings.token
DB_PATH = settings.db_path
MESSAGE_POINT = settings.message_point
DAILY_SIGNIN_BONUS = settings.daily_signin_bonus
THROTTLE_SECONDS = settings.throttle_seconds
