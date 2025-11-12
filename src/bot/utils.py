"""Utility helpers for the bot."""

from __future__ import annotations

import html
import time


class Throttle:
    """In-memory throttle helper."""

    def __init__(self, interval_seconds: int) -> None:
        self.interval = max(0, interval_seconds)
        self._last_seen: dict[int, float] = {}

    def should_allow(self, key: int) -> bool:
        """Return True if the action should be allowed for the given key."""
        if self.interval == 0:
            return True
        now = time.monotonic()
        last = self._last_seen.get(key)
        if last is None or now - last >= self.interval:
            self._last_seen[key] = now
            return True
        return False

    def reset(self, key: int) -> None:
        """Reset throttle tracking for key."""
        self._last_seen.pop(key, None)


def html_escape(value: str | None) -> str:
    """Escape a string for safe HTML output."""
    return html.escape(value or "", quote=True)


def mention_from_row_html(
    user_id: int, username: str | None, first: str | None, last: str | None
) -> str:
    """Return a clickable HTML mention for leaderboard rows."""
    if username:
        display = f"@{username}"
    else:
        parts = [part for part in (first, last) if part]
        display = " ".join(parts).strip() or f"User {user_id}"
    display = html_escape(display)
    return f'<a href="tg://user?id={user_id}">{display}</a>'
