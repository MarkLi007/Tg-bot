"""Telegram command and message handlers."""

from __future__ import annotations

from datetime import timezone

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .settings import Settings
from .storage import Storage
from .utils import Throttle

GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}

HELP_MESSAGE = (
    "我是群积分机器人：\n"
    "- 群聊文本消息 +{message_point} 分\n"
    "- 每日签到 /signin +{daily_signin_bonus} 分 (UTC)\n"
    "- /me 查看我的积分\n"
    "- /rank 查看我的排名\n"
    "- /top 查看积分榜前十"
)


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
    await update.effective_message.reply_text(
        HELP_MESSAGE.format(
            message_point=settings.message_point,
            daily_signin_bonus=settings.daily_signin_bonus,
        )
    )


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    storage = _get_storage(context)
    score = await storage.get_user_score(user.id, message.chat_id)
    if score is None:
        await message.reply_text("你还没有积分记录，快来发言赚取积分吧！")
        return
    last_sign = (
        score.last_signin.astimezone(timezone.utc).strftime("%Y-%m-%d")
        if score.last_signin
        else "无"
    )
    await message.reply_text(
        f"当前积分：{score.points}\n发言次数：{score.message_cnt}\n上次签到：{last_sign} (UTC)"
    )


async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    storage = _get_storage(context)
    score = await storage.get_user_score(user.id, message.chat_id)
    if score is None:
        await message.reply_text("暂无积分记录。")
        return
    user_rank = await storage.get_rank(user.id, message.chat_id)
    if user_rank is None:
        await message.reply_text("暂无法计算排名，请稍后再试。")
        return
    await message.reply_text(
        f"你的当前排名：#{user_rank}\n积分：{score.points}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    storage = _get_storage(context)
    top_scores = await storage.get_top(message.chat_id, limit=10)
    if not top_scores:
        await message.reply_text("本群暂无积分记录。")
        return
    lines = ["本群积分榜："]
    for idx, score in enumerate(top_scores, start=1):
        lines.append(
            f"#{idx} 用户 {score.user_id}: {score.points} 分 / {score.message_cnt} 次发言"
        )
    await message.reply_text("\n".join(lines))


async def signin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _ensure_group(update):
        await _reply_private_only(update)
        return
    message = update.effective_message
    user = message.from_user
    storage = _get_storage(context)
    settings = _get_settings(context)
    applied = await storage.signin(user.id, message.chat_id, settings.daily_signin_bonus)
    score = await storage.get_user_score(user.id, message.chat_id)
    if applied:
        current_points = score.points if score else settings.daily_signin_bonus
        await message.reply_text(
            f"签到成功！获得 {settings.daily_signin_bonus} 分，当前积分 {current_points}。"
        )
    else:
        await message.reply_text("今日已签到，请明天再来～")


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
    await storage.add_message_point(message.from_user.id, message.chat_id, settings.message_point)


async def _ensure_group(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in GROUP_TYPES)


async def _reply_private_only(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("请在群组中使用该命令。")


def _get_storage(context: CallbackContext) -> Storage:
    return context.application.bot_data["storage"]


def _get_settings(context: CallbackContext) -> Settings:
    return context.application.bot_data["settings"]


def _get_throttle(context: CallbackContext) -> Throttle:
    return context.application.bot_data["throttle"]
