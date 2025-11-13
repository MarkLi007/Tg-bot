"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio

from bot.app import create_application


async def main() -> None:
    application = await create_application()
    async with application:
        await application.start()
        await application.updater.start_polling(allowed_updates=None)
        try:
            await asyncio.Future()
        finally:
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    asyncio.run(main())
