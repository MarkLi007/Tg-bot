"""Simple language catalogue for bot responses."""

from __future__ import annotations

import os

LANG = os.getenv("LANG", "en")

TEXTS: dict[str, str] = {
    "start": (
        "🤖 <b>Group Points Bot</b> is ready!\n"
        "- Each text message: +1 point\n"
        "- /signin once per day: +10 points\n"
        "- /me to view your score\n"
        "- /rank for your ranking\n"
        "- /top for leaderboard"
    ),
    "no_record": "You have no score yet. Start chatting to earn points!",
    "signin_ok": "✅ Sign-in successful! You earned <b>{bonus}</b> points.",
    "signin_dup": "You already signed in today. Come back tomorrow!",
    "me": (
        "👤 {name}\n"
        "🏅 Points: <b>{points}</b>\n"
        "💬 Messages: {msgs}\n"
        "🗓️ Last sign-in (UTC): {last}"
    ),
    "rank": "Your current ranking: <b>#{rank}</b>\nPoints: <b>{points}</b>",
    "top_title": "🏆 <b>Leaderboard</b>",
    "unauthorized": "⚠️ This bot is not authorized for this chat.",
    "pong": "PONG",
    "chatid": "Current chat id: <code>{chat_id}</code>",
    "config": "LANG={lang}\nALLOWED_CHAT_IDS={ids}\nDB_PATH={db}",
}


def t(key: str, **kwargs: object) -> str:
    """Fetch a localized string."""

    template = TEXTS[key]
    return template.format(**kwargs)


__all__ = ["t"]
