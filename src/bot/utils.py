"""Utility helpers for the bot."""

from __future__ import annotations

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
