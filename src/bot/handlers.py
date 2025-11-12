"""Telegram command and message handlers."""

from __future__ import annotations

import logging
import os
from datetime import timezone

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .lang import t
from .settings import DAILY_SIGNIN_BONUS, MESSAGE_POINT, THROTTLE_SECONDS
from .storage import (
    add_message_point,
    ensure_row,
    get_db,
    get_rank,
    get_top,
    get_user_score,
    signin,
    upsert_user,
)
from .utils import Throttle, html_escape, mention_from_row_html

ALLOWED_CHAT_IDS = {
    int(value)
    for value in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
    if value.strip()
}

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}


def register_handlers(application: Application) -> None:
    """Wire command and message handlers onto the application."""

    application.bot_data["throttle"] = Throttle(THROTTLE_SECONDS)

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("ping", cmd_ping))
    application.add_handler(CommandHandler("chatid", cmd_chatid))
    application.add_handler(CommandHandler("config", cmd_config))
    application.add_handler(CommandHandler("signin", cmd_signin))
    application.add_handler(CommandHandler("me", cmd_me))
    application.add_handler(CommandHandler("rank", cmd_rank))
    application.add_handler(CommandHandler("top", cmd_top))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message)
    )


def _allowed(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        return True
    chat = update.effective_chat
    return bool(chat and chat.id in ALLOWED_CHAT_IDS)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.effective_message.reply_text(t("start"), parse_mode=ParseMode.HTML)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.effective_message.reply_text(t("pong"), parse_mode=ParseMode.HTML)


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    chat = update.effective_chat
    if not chat:
        return
    await update.effective_message.reply_text(
        t("chatid", chat_id=chat.id), parse_mode=ParseMode.HTML
    )


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await update.effective_message.reply_text(
        t(
            "config",
            lang=os.getenv("LANG", "en"),
            ids=os.getenv("ALLOWED_CHAT_IDS", ""),
            db=os.getenv("DB_PATH", "points.db"),
        ),
        parse_mode=ParseMode.HTML,
    )


async def cmd_signin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not (message and user and chat):
        return

    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        applied = await signin(db, user.id, chat.id, DAILY_SIGNIN_BONUS)

    if not applied:
        await message.reply_text(t("signin_dup"), parse_mode=ParseMode.HTML)
        return

    logging.info(
        "signin_ok",
        extra={"chat_id": chat.id, "user_id": user.id, "bonus": DAILY_SIGNIN_BONUS},
    )
    await message.reply_text(
        t("signin_ok", bonus=DAILY_SIGNIN_BONUS), parse_mode=ParseMode.HTML
    )


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not (message and user and chat):
        return

    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        score = await get_user_score(db, user.id, chat.id)
    if not score:
        await message.reply_text(t("no_record"), parse_mode=ParseMode.HTML)
        return

    last = (
        score.last_signin.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if score.last_signin
        else "—"
    )
    await message.reply_text(
        t(
            "me",
            name=html_escape(user.full_name),
            points=int(score.points),
            msgs=int(score.message_cnt),
            last=html_escape(last),
        ),
        parse_mode=ParseMode.HTML,
    )


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not (message and user and chat):
        return

    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        rank = await get_rank(db, user.id, chat.id)
        score = await get_user_score(db, user.id, chat.id)
    points = int(score.points) if score else 0
    await message.reply_text(
        t("rank", rank=rank if rank is not None else "N/A", points=points),
        parse_mode=ParseMode.HTML,
    )


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    message = update.effective_message
    chat = update.effective_chat
    if not (message and chat):
        return

    async with get_db() as db:
        rows = await get_top(db, chat.id)
    if not rows:
        await message.reply_text(t("no_record"), parse_mode=ParseMode.HTML)
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = [t("top_title")]
    for idx, row in enumerate(rows, start=1):
        medal = medals[idx - 1] if idx <= len(medals) else f"{idx}."
        mention = mention_from_row_html(
            row.user_id, row.username, row.first_name, row.last_name
        )
        lines.append(
            f"{medal} {mention} — <b>{int(row.points)}</b> pts / {int(row.message_cnt)} msgs"
        )
    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not (message and chat and user):
        return
    if chat.type not in GROUP_TYPES:
        return
    if user.is_bot:
        return

    throttle: Throttle = context.application.bot_data["throttle"]
    if not throttle.should_allow(user.id):
        return

    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        await add_message_point(db, user.id, chat.id, MESSAGE_POINT)
    logging.info(
        "message_scored",
        extra={"chat_id": chat.id, "user_id": user.id, "points": MESSAGE_POINT},
    )


__all__ = ["register_handlers"]
