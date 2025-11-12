"""Application factory for the Telegram bot."""

from __future__ import annotations

import json
import logging
import sys
import time

from telegram.error import BadRequest, TelegramError
from telegram.ext import Application, ApplicationBuilder

from .handlers import register_handlers
from .settings import TOKEN
from .storage import init_db


def setup_logging() -> None:
    """Configure root logger to emit JSON records."""

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            payload = {
                "ts": round(time.time(), 3),
                "lvl": record.levelname,
                "msg": record.getMessage(),
                "name": record.name,
            }
            # Preserve extra context if provided.
            for key in ("chat_id", "user_id", "error", "error_type", "points", "bonus"):
                if hasattr(record, key):
                    payload[key] = getattr(record, key)
            return json.dumps(payload, ensure_ascii=False)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


async def on_error(update, context) -> None:  # type: ignore[override]
    """Log unexpected errors with structured metadata."""

    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
    user_id = getattr(getattr(update, "effective_user", None), "id", None)
    error = context.error
    logging.exception(
        "unhandled_error",
        extra={
            "chat_id": chat_id,
            "user_id": user_id,
            "error_type": type(error).__name__,
            "error": str(error),
        },
    )


async def create_application() -> Application:
    """Create and configure the Telegram application."""

    setup_logging()
    await init_db()

    application = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()

    # Ensure polling mode is clean each start.
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
    except (TelegramError, BadRequest) as exc:  # pragma: no cover - defensive
        logging.warning("delete_webhook_failed", extra={"error": str(exc)})

    register_handlers(application)
    application.add_error_handler(on_error)

    logging.info("Bot is running...")
    return application
