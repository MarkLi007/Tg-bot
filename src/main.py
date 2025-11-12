"""CLI entrypoint for running the bot."""

from __future__ import annotations

import logging

from bot.app import create_application


def main() -> None:
    """Start the telegram bot."""
    application = create_application()
    logger = logging.getLogger(__name__)
    logger.info("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
