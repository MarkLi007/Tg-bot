"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    """Container for runtime configuration."""

    telegram_token: str
    db_path: str = "points.db"
    message_point: int = 1
    daily_signin_bonus: int = 10
    throttle_seconds: int = 5

    @classmethod
    def from_env(cls) -> Settings:
        """Create settings from environment variables."""
        token = os.getenv("TELEGRAM_TOKEN", "").strip()
        db_path = os.getenv("DB_PATH", "points.db").strip() or "points.db"
        message_point = cls._parse_int(os.getenv("MESSAGE_POINT"), default=1)
        daily_bonus = cls._parse_int(os.getenv("DAILY_SIGNIN_BONUS"), default=10)
        throttle_seconds = cls._parse_int(os.getenv("THROTTLE_SECONDS"), default=5)
        instance = cls(
            telegram_token=token,
            db_path=db_path,
            message_point=message_point,
            daily_signin_bonus=daily_bonus,
            throttle_seconds=throttle_seconds,
        )
        instance.validate()
        return instance

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN is required. Please set it in your environment.")
        if self.message_point < 0:
            raise ValueError("MESSAGE_POINT must be non-negative.")
        if self.daily_signin_bonus < 0:
            raise ValueError("DAILY_SIGNIN_BONUS must be non-negative.")
        if self.throttle_seconds < 0:
            raise ValueError("THROTTLE_SECONDS must be non-negative.")

    @staticmethod
    def _parse_int(value: str | None, *, default: int) -> int:
        if value is None or not value.strip():
            return default
        try:
            return int(value)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError(f"Invalid integer value: {value}") from exc


settings = Settings.from_env()
