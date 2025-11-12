"""Simple internationalization helpers for bot responses."""

from __future__ import annotations

import os

LANG = os.getenv("LANG", "en").lower()

TEXTS = {
    "start": {
        "en": (
            "🤖 *Group Points Bot* is ready!\n"
            "- Group messages earn *{message_point}* point(s).\n"
            "- Daily /signin gives *{daily_signin_bonus}* points (UTC).\n"
            "- Use /me, /rank, /top to explore your stats."
        )
    },
    "no_record": {"en": "You have no score yet. Start chatting!"},
    "signin_ok": {"en": "✅ Sign-in successful! You earned *{bonus}* points."},
    "signin_dup": {"en": "You already signed in today."},
    "rank": {"en": "Your rank: *#{rank}*  Points: *{points}*"},
    "rank_error": {"en": "Unable to calculate rank right now. Please try again later."},
    "top_title": {"en": "🏆 *Leaderboard*"},
    "top_empty": {"en": "No scores have been recorded yet."},
    "private_only": {"en": "Please use this command inside a group."},
    "me_title": {"en": "👤 {name}"},
    "me_points": {"en": "🏅 Points: *{points}*"},
    "me_messages": {"en": "💬 Messages: {messages}"},
    "me_last_signin": {"en": "🗓️ Last Sign-in (UTC): {last_signin}"},
}


def t(key: str, **kwargs: object) -> str:
    template = TEXTS.get(key, {}).get(LANG, "")
    return template.format(**kwargs)
