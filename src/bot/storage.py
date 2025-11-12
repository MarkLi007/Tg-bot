"""Async SQLite helpers for the points bot."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite
from telegram import User as TelegramUser

from .models import Score
from .settings import DB_PATH

INIT_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS scores(
  user_id INTEGER NOT NULL,
  chat_id INTEGER NOT NULL,
  points INTEGER NOT NULL DEFAULT 0,
  message_cnt INTEGER NOT NULL DEFAULT 0,
  last_signin TEXT,
  PRIMARY KEY(user_id, chat_id)
);
CREATE INDEX IF NOT EXISTS idx_scores_chat_points ON scores(chat_id, points DESC);
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER NOT NULL,
  chat_id INTEGER NOT NULL,
  first_name TEXT,
  last_name  TEXT,
  username   TEXT,
  PRIMARY KEY(user_id, chat_id)
);
"""

_init_lock = asyncio.Lock()
_initialized = False


async def init_db() -> None:
    """Initialize the database schema if it has not been created."""

    global _initialized
    if _initialized:
        return
    async with _init_lock:
        if _initialized:
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript(INIT_SQL)
            await db.commit()
        _initialized = True


@asynccontextmanager
async def get_db() -> aiosqlite.Connection:
    """Yield a database connection with row factory enabled."""

    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def ensure_row(db: aiosqlite.Connection, user_id: int, chat_id: int) -> None:
    """Ensure a score row exists for the given user and chat."""

    await db.execute(
        """
        INSERT INTO scores(user_id, chat_id, points, message_cnt, last_signin)
        VALUES(?, ?, 0, 0, NULL)
        ON CONFLICT(user_id, chat_id) DO NOTHING
        """,
        (user_id, chat_id),
    )
    await db.commit()


async def upsert_user(
    db: aiosqlite.Connection, user: TelegramUser, chat_id: int
) -> None:
    """Insert or update cached Telegram user metadata."""

    await db.execute(
        """
        INSERT INTO users(user_id, chat_id, first_name, last_name, username)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
          first_name=excluded.first_name,
          last_name=excluded.last_name,
          username=excluded.username
        """,
        (
            user.id,
            chat_id,
            user.first_name,
            user.last_name,
            user.username,
        ),
    )
    await db.commit()


async def add_message_point(
    db: aiosqlite.Connection, user_id: int, chat_id: int, points: int
) -> None:
    """Increment message count and add points for a chat message."""

    await db.execute(
        """
        UPDATE scores
        SET points = points + ?, message_cnt = message_cnt + 1
        WHERE user_id = ? AND chat_id = ?
        """,
        (points, user_id, chat_id),
    )
    await db.commit()


async def signin(
    db: aiosqlite.Connection, user_id: int, chat_id: int, bonus: int
) -> bool:
    """Apply a daily sign-in bonus. Returns True if the bonus was granted."""

    async with db.execute(
        "SELECT last_signin FROM scores WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    ) as cursor:
        row = await cursor.fetchone()
    last = _parse_datetime(row["last_signin"]) if row and row["last_signin"] else None
    today = datetime.now(timezone.utc).date()
    if last and last.date() == today:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        UPDATE scores
        SET points = points + ?, last_signin = ?
        WHERE user_id = ? AND chat_id = ?
        """,
        (bonus, now_iso, user_id, chat_id),
    )
    await db.commit()
    return True


async def get_user_score(
    db: aiosqlite.Connection, user_id: int, chat_id: int
) -> Score | None:
    """Return the score entry for a user within a chat."""

    async with db.execute(
        """
        SELECT s.user_id, s.chat_id, s.points, s.message_cnt, s.last_signin,
               u.first_name, u.last_name, u.username
        FROM scores AS s
        LEFT JOIN users AS u ON u.user_id = s.user_id AND u.chat_id = s.chat_id
        WHERE s.user_id = ? AND s.chat_id = ?
        """,
        (user_id, chat_id),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_score(row)


async def get_rank(db: aiosqlite.Connection, user_id: int, chat_id: int) -> int | None:
    """Return the 1-based ranking for the user within a chat."""

    async with db.execute(
        """
        SELECT user_id
        FROM scores
        WHERE chat_id = ?
        ORDER BY points DESC, message_cnt DESC, user_id ASC
        """,
        (chat_id,),
    ) as cursor:
        rank = 1
        async for row in cursor:
            if row["user_id"] == user_id:
                return rank
            rank += 1
    return None


async def get_top(
    db: aiosqlite.Connection, chat_id: int, limit: int = 10
) -> list[Score]:
    """Return the leaderboard for a chat ordered by points."""

    async with db.execute(
        """
        SELECT s.user_id, s.chat_id, s.points, s.message_cnt, s.last_signin,
               u.first_name, u.last_name, u.username
        FROM scores AS s
        LEFT JOIN users AS u ON u.user_id = s.user_id AND u.chat_id = s.chat_id
        WHERE s.chat_id = ?
        ORDER BY s.points DESC, s.message_cnt DESC, s.user_id ASC
        LIMIT ?
        """,
        (chat_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_score(row) for row in rows]


def _row_to_score(row: aiosqlite.Row) -> Score:
    last_signin = _parse_datetime(row["last_signin"]) if row["last_signin"] else None
    return Score(
        user_id=row["user_id"],
        chat_id=row["chat_id"],
        points=row["points"],
        message_cnt=row["message_cnt"],
        last_signin=last_signin,
        first_name=row["first_name"],
        last_name=row["last_name"],
        username=row["username"],
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


__all__ = [
    "init_db",
    "get_db",
    "ensure_row",
    "upsert_user",
    "add_message_point",
    "signin",
    "get_user_score",
    "get_rank",
    "get_top",
]
