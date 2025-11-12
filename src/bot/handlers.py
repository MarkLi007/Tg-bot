"""Telegram command and message handlers."""

from __future__ import annotations

import logging
from datetime import timezone

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .lang import t
from .settings import Settings
from .storage import Storage
from .utils import Throttle, display_name, mention_from_row

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}

logger = logging.getLogger(__name__)


def register(application: Application, storage: Storage, settings: Settings) -> None:
    """Register handlers on the provided application."""
    application.bot_data["storage"] = storage
    application.bot_data["settings"] = settings
    application.bot_data["throttle"] = Throttle(settings.throttle_seconds)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("me", me))
    application.add_handler(CommandHandler("rank", rank))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("signin", signin))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    settings = _get_settings(context)
    message = update.effective_message
    user = update.effective_user
    if message and user:
        await _upsert_user(context, user, message.chat_id)
    await message.reply_text(
        t(
            "start",
            message_point=settings.message_point,
            daily_signin_bonus=settings.daily_signin_bonus,
        ),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    if user:
        await _upsert_user(context, user, message.chat_id)
    storage = _get_storage(context)
    score = await storage.get_user_score(user.id, message.chat_id)
    if score is None:
        await message.reply_text(t("no_record"))
        return
    last_sign = (
        score.last_signin.astimezone(timezone.utc).strftime("%Y-%m-%d")
        if score.last_signin
        else "—"
    )
    name = display_name(score)
    lines = [
        t("me_title", name=name),
        t("me_points", points=score.points),
        t("me_messages", messages=score.message_cnt),
        t("me_last_signin", last_signin=last_sign),
    ]
    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    if user:
        await _upsert_user(context, user, message.chat_id)
    storage = _get_storage(context)
    score = await storage.get_user_score(user.id, message.chat_id)
    if score is None:
        await message.reply_text(t("no_record"))
        return
    user_rank = await storage.get_rank(user.id, message.chat_id)
    if user_rank is None:
        await message.reply_text(t("rank_error"))
        return
    await message.reply_text(
        t("rank", rank=user_rank, points=score.points),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    storage = _get_storage(context)
    user = update.effective_user
    if message and user:
        await _upsert_user(context, user, message.chat_id)
    top_scores = await storage.get_top(message.chat_id, limit=10)
    if not top_scores:
        await message.reply_text(t("top_empty"))
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = [t("top_title")]
    for idx, score in enumerate(top_scores, start=1):
        medal = medals[idx - 1] if idx <= len(medals) else f"{idx}."
        mention = mention_from_row(score)
        lines.append(
            f"{medal} {mention} — *{score.points}* pts / {score.message_cnt} msgs"
        )
    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def signin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    if user:
        await _upsert_user(context, user, message.chat_id)
    storage = _get_storage(context)
    settings = _get_settings(context)
    applied = await storage.signin(user.id, message.chat_id, settings.daily_signin_bonus)
    score = await storage.get_user_score(user.id, message.chat_id)
    if applied:
        current_points = score.points if score else settings.daily_signin_bonus
        await message.reply_text(
            t("signin_ok", bonus=settings.daily_signin_bonus),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        logger.info(
            "signin_ok",
            extra={"chat_id": message.chat_id, "user_id": user.id, "points": current_points},
        )
    else:
        await message.reply_text(t("signin_dup"))


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        return
    message = update.effective_message
    if message is None or message.from_user is None:
        return
    if message.from_user.is_bot:
        return
    storage = _get_storage(context)
    settings = _get_settings(context)
    throttle = _get_throttle(context)
    if not throttle.should_allow(message.from_user.id):
        return
    await _upsert_user(context, message.from_user, message.chat_id)
    score = await storage.add_message_point(
        message.from_user.id, message.chat_id, settings.message_point
    )
    logger.info(
        "message_scored",
        extra={
            "chat_id": message.chat_id,
            "user_id": message.from_user.id,
            "points": score.points,
        },
    )


async def _ensure_group(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in GROUP_TYPES)


async def _reply_private_only(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(t("private_only"))


async def _upsert_user(context: CallbackContext, user, chat_id: int) -> None:
    storage = _get_storage(context)
    await storage.upsert_user(user, chat_id)


def _get_storage(context: CallbackContext) -> Storage:
    return context.application.bot_data["storage"]


def _get_settings(context: CallbackContext) -> Settings:
    return context.application.bot_data["settings"]


def _get_throttle(context: CallbackContext) -> Throttle:
    return context.application.bot_data["throttle"]
