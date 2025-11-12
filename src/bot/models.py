"""Database models for the points bot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Score:
    """Representation of a user's score entry."""

    user_id: int
    chat_id: int
    points: int
    message_cnt: int
    last_signin: datetime | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
