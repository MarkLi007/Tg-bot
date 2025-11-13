"""Application factory for the Telegram bot."""

from __future__ import annotations

import json
import logging
import sys
import time

from telegram.ext import Application, ApplicationBuilder

from .handlers import register_handlers
from .settings import TOKEN
from .storage import init_db


def setup_logging() -> None:
    """Configure structured JSON logging for the bot."""

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            payload = {
                "ts": round(time.time(), 3),
                "lvl": record.levelname,
                "msg": record.getMessage(),
                "name": record.name,
            }
            for field in (
                "chat_id",
                "user_id",
                "bonus",
                "points",
                "thread_id",
                "is_topic",
                "delta",
                "error_type",
                "error",
            ):
                if hasattr(record, field):
                    payload[field] = getattr(record, field)
            return json.dumps(payload, ensure_ascii=False)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


async def on_error(update, context) -> None:  # type: ignore[override]
    """Log unexpected errors with structured context."""
    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
    user_id = getattr(getattr(update, "effective_user", None), "id", None)
    logging.exception(
        "unhandled_error",
        extra={
            "chat_id": chat_id,
            "user_id": user_id,
            "error_type": type(context.error).__name__,
            "error": str(context.error),
        },
    )


async def create_application() -> Application:
    """Instantiate and configure the Telegram application."""
    setup_logging()
    await init_db()
    application = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()
    await application.bot.delete_webhook(drop_pending_updates=True)
    register_handlers(application)
    application.add_error_handler(on_error)
    logging.info("Bot is running...", extra={"name": "__main__"})
    return application
