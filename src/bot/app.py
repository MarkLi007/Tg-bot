"""Application factory for the Telegram bot."""

from __future__ import annotations

import json
import logging
import sys
import time

from telegram.ext import Application, ApplicationBuilder

from .handlers import register
from .settings import Settings
from .settings import settings as default_settings
from .storage import Storage


class JsonFormatter(logging.Formatter):
    """Format logs as structured JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": round(time.time(), 3),
            "lvl": record.levelname,
            "msg": record.getMessage(),
            "name": record.name,
        }
        for key in ("chat_id", "user_id", "points"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging with JSON formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def create_application(app_settings: Settings | None = None) -> Application:
    """Create the telegram application instance."""
    setup_logging()
    app_settings = app_settings or default_settings
    storage = Storage(app_settings.db_path)

    async def _post_init(application: Application) -> None:
        await storage.initialize()

    application = (
        ApplicationBuilder().token(app_settings.telegram_token).post_init(_post_init).build()
    )
    register(application, storage, app_settings)
    return application
