"""Telegram command and message handlers."""

from __future__ import annotations

import datetime as dt
import logging
import os

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
    int(value) for value in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if value.strip()
}
THROTTLE = Throttle(THROTTLE_SECONDS)
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}


def register_handlers(app: Application) -> None:
    """Register command and message handlers."""
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("signin", cmd_signin))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("rank", cmd_rank))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.effective_message.reply_text(
        t("start"),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.effective_message.reply_text(t("pong"), parse_mode=ParseMode.HTML)


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    chat = update.effective_chat
    if chat:
        await update.effective_message.reply_text(
            t("chatid", chat_id=chat.id),
            parse_mode=ParseMode.HTML,
        )


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
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
    if not await guard(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not all((message, user, chat)):
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
        t("signin_ok", bonus=DAILY_SIGNIN_BONUS),
        parse_mode=ParseMode.HTML,
    )


async def cmd_me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not all((message, user, chat)):
        return
    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        row = await get_user_score(db, user.id, chat.id)
    if row is None:
        await message.reply_text(t("no_record"), parse_mode=ParseMode.HTML)
        return
    last = row["last_signin"] if "last_signin" in row.keys() else row[2]
    if last:
        try:
            last_dt = dt.datetime.fromisoformat(last).astimezone(dt.timezone.utc)
            last_value = last_dt.strftime("%Y-%m-%d")
        except ValueError:
            last_value = html_escape(last)
    else:
        last_value = "—"
    await message.reply_text(
        t(
            "me",
            name=html_escape(user.full_name),
            points=int(row["points"] if "points" in row.keys() else row[0]),
            msgs=int(row["message_cnt"] if "message_cnt" in row.keys() else row[1]),
            last=last_value,
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not all((message, user, chat)):
        return
    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        row = await get_user_score(db, user.id, chat.id)
        rank = await get_rank(db, user.id, chat.id)
    if row is None or rank is None:
        await message.reply_text(t("no_record"), parse_mode=ParseMode.HTML)
        return
    await message.reply_text(
        t(
            "rank",
            rank=rank,
            points=int(row["points"] if "points" in row.keys() else row[0]),
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not all((message, user, chat)):
        return
    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        rows = await get_top(db, chat.id, limit=10)
    if not rows:
        await message.reply_text(t("no_record"), parse_mode=ParseMode.HTML)
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = [t("top_title")]
    for idx, row in enumerate(rows, start=1):
        medal = medals[idx - 1] if idx <= len(medals) else f"{idx}."
        mention = mention_from_row_html(
            row["user_id"],
            row["username"],
            row["first_name"],
            row["last_name"],
        )
        lines.append(
            f"{medal} {mention} — <b>{int(row['points'])}</b> pts / {int(row['message_cnt'])} msgs"
        )
    await message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not all((message, chat, user)):
        return
    if message.from_user and message.from_user.is_bot:
        return
    if chat.type not in GROUP_TYPES:
        return
    if not THROTTLE.should_allow(user.id):
        return
    async with get_db() as db:
        await ensure_row(db, user.id, chat.id)
        await upsert_user(db, user, chat.id)
        await add_message_point(db, user.id, chat.id, MESSAGE_POINT)
    logging.info(
        "message_scored",
        extra={"chat_id": chat.id, "user_id": user.id, "points": MESSAGE_POINT},
    )


async def guard(update: Update) -> bool:
    """Return True if the update is allowed to proceed."""
    chat = update.effective_chat
    if chat is None:
        return False
    if chat.type not in GROUP_TYPES:
        return False
    if ALLOWED_CHAT_IDS and chat.id not in ALLOWED_CHAT_IDS:
        return False
    return True
