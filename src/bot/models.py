"""Database models and SQL statements for the points bot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

CREATE_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS scores (
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    points INTEGER NOT NULL DEFAULT 0,
    message_cnt INTEGER NOT NULL DEFAULT 0,
    last_signin TEXT,
    PRIMARY KEY (user_id, chat_id)
);
"""

ENABLE_WAL = "PRAGMA journal_mode=WAL;"


@dataclass(slots=True)
class Score:
    """Representation of a user's score entry."""

    user_id: int
    chat_id: int
    points: int
    message_cnt: int
    last_signin: datetime | None = None
