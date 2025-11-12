"""Utility helpers for the bot."""

from __future__ import annotations

import time

from . import models


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


def mention_from_row(score: models.Score) -> str:
    """Return a Markdown-safe mention for the provided score row."""
    if score.username:
        return f"[@{score.username}](tg://user?id={score.user_id})"
    name_parts = [part for part in (score.first_name, score.last_name) if part]
    if name_parts:
        return _escape_markdown(" ".join(name_parts))
    return f"User {score.user_id}"


def display_name(score: models.Score) -> str:
    """Return a readable name for the user suitable for Markdown output."""
    name_parts = [part for part in (score.first_name, score.last_name) if part]
    if score.username:
        return f"@{score.username}"
    if name_parts:
        return _escape_markdown(" ".join(name_parts))
    return f"User {score.user_id}"


def _escape_markdown(value: str) -> str:
    """Escape characters that are special in Telegram Markdown."""
    for ch in ("_", "*", "[", "]", "(", ")"):
        value = value.replace(ch, f"\\{ch}")
    return value
