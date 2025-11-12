"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio

from bot.app import create_application

if __name__ == "__main__":
    application = asyncio.run(create_application())
    application.run_polling(allowed_updates=None, drop_pending_updates=True)
