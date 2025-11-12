"""Application factory for the Telegram bot."""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder

from .handlers import register
from .settings import Settings
from .settings import settings as default_settings
from .storage import Storage


def create_application(app_settings: Settings | None = None) -> Application:
    """Create the telegram application instance."""
    app_settings = app_settings or default_settings
    storage = Storage(app_settings.db_path)

    async def _post_init(application: Application) -> None:
        await storage.initialize()

    application = (
        ApplicationBuilder().token(app_settings.telegram_token).post_init(_post_init).build()
    )
    register(application, storage, app_settings)
    return application
