"""Async SQLite helpers for the Telegram points bot."""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

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

_DB_PATH = DB_PATH
_INIT_LOCK = asyncio.Lock()
_INITIALIZED = False


async def init_db(db_path: str | None = None) -> None:
    """Initialize the SQLite database if it has not been set up."""
    global _INITIALIZED, _DB_PATH
    if db_path is not None and db_path != _DB_PATH:
        _INITIALIZED = False
        _DB_PATH = db_path
    if _INITIALIZED:
        return
    async with _INIT_LOCK:
        if _INITIALIZED:
            return
        await asyncio.to_thread(_initialize_database, _DB_PATH)
        _INITIALIZED = True


def _initialize_database(path: str) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(INIT_SQL)
        db.commit()


@asynccontextmanager
async def get_db() -> AsyncIterator[sqlite3.Connection]:
    """Yield an initialized database connection."""
    await init_db()
    db = sqlite3.connect(_DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        await asyncio.to_thread(db.close)


async def db_execute(db: sqlite3.Connection, query: str, params: tuple = ()) -> None:
    """Execute a query that does not return rows."""

    def _exec() -> None:
        db.execute(query, params)
        db.commit()

    await asyncio.to_thread(_exec)


async def db_fetchone(db: sqlite3.Connection, query: str, params: tuple = ()) -> sqlite3.Row | None:
    """Execute a query and return a single row."""

    def _exec() -> sqlite3.Row | None:
        cursor = db.execute(query, params)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    return await asyncio.to_thread(_exec)


async def db_fetchall(db: sqlite3.Connection, query: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Execute a query and return all rows."""

    def _exec() -> list[sqlite3.Row]:
        cursor = db.execute(query, params)
        try:
            return cursor.fetchall()
        finally:
            cursor.close()

    return await asyncio.to_thread(_exec)


async def ensure_row(db: sqlite3.Connection, user_id: int, chat_id: int) -> None:
    """Ensure that a score row exists for the user in the chat."""
    await db_execute(
        db,
        """
        INSERT INTO scores(user_id, chat_id, points, message_cnt, last_signin)
        VALUES (?, ?, 0, 0, NULL)
        ON CONFLICT(user_id, chat_id) DO NOTHING
        """,
        (user_id, chat_id),
    )


async def upsert_user(db: sqlite3.Connection, user, chat_id: int) -> None:
    """Insert or update Telegram user metadata for the chat."""
    await db_execute(
        db,
        """
        INSERT INTO users(user_id, chat_id, first_name, last_name, username)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
          first_name=excluded.first_name,
          last_name=excluded.last_name,
          username=excluded.username
        """,
        (user.id, chat_id, user.first_name, user.last_name, user.username),
    )


async def add_message_point(
    db: sqlite3.Connection, user_id: int, chat_id: int, points: int
) -> None:
    """Increase message counters and award points for a user."""
    await db_execute(
        db,
        """
        UPDATE scores
        SET points = points + ?, message_cnt = message_cnt + 1
        WHERE user_id = ? AND chat_id = ?
        """,
        (points, user_id, chat_id),
    )


async def signin(db: sqlite3.Connection, user_id: int, chat_id: int, bonus: int) -> bool:
    """Apply a daily sign-in bonus once per UTC day."""
    row = await db_fetchone(
        db,
        "SELECT last_signin FROM scores WHERE user_id=? AND chat_id=?",
        (user_id, chat_id),
    )
    last_signin = row[0] if row else None
    today = datetime.now(timezone.utc).date().isoformat()
    if last_signin == today:
        return False
    if last_signin:
        try:
            previous = datetime.fromisoformat(last_signin)
        except ValueError:
            previous = None
        if previous is not None:
            previous_date = (
                (previous if previous.tzinfo is None else previous.astimezone(timezone.utc))
                .date()
                .isoformat()
            )
            if previous_date == today:
                return False
    await db_execute(
        db,
        """
        UPDATE scores
        SET points = points + ?, last_signin = ?
        WHERE user_id = ? AND chat_id = ?
        """,
        (bonus, today, user_id, chat_id),
    )
    return True


async def get_user_score(db: sqlite3.Connection, user_id: int, chat_id: int):
    """Return the score row for a user in a chat."""
    return await db_fetchone(
        db,
        """
        SELECT s.points, s.message_cnt, s.last_signin,
               u.first_name, u.last_name, u.username
        FROM scores AS s
        LEFT JOIN users AS u ON u.user_id = s.user_id AND u.chat_id = s.chat_id
        WHERE s.user_id = ? AND s.chat_id = ?
        """,
        (user_id, chat_id),
    )


async def get_rank(db: sqlite3.Connection, user_id: int, chat_id: int) -> int | None:
    """Compute a user's rank within a chat based on points and message count."""
    rows = await db_fetchall(
        db,
        """
        SELECT user_id
        FROM scores
        WHERE chat_id = ?
        ORDER BY points DESC, message_cnt DESC, user_id ASC
        """,
        (chat_id,),
    )
    index = 1
    for row in rows:
        if row[0] == user_id:
            return index
        index += 1
    return None


async def get_top(db: sqlite3.Connection, chat_id: int, *, limit: int = 10) -> list[sqlite3.Row]:
    """Return the top N score rows for a chat including user metadata."""
    return await db_fetchall(
        db,
        """
        SELECT s.user_id, s.points, s.message_cnt,
               u.username, u.first_name, u.last_name
        FROM scores AS s
        LEFT JOIN users AS u ON u.user_id = s.user_id AND u.chat_id = s.chat_id
        WHERE s.chat_id = ?
        ORDER BY s.points DESC, s.message_cnt DESC, s.user_id ASC
        LIMIT ?
        """,
        (chat_id, limit),
    )
