"""CLI entrypoint for running the bot."""

from __future__ import annotations

import logging

from bot.app import create_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the telegram bot."""
    application = create_application()
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
