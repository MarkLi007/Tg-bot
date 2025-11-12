"""Async SQLite storage helpers for the points bot."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiosqlite
from telegram import User as TelegramUser

from . import models


class Storage:
    """Wrapper around SQLite operations using aiosqlite."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database with WAL mode and required tables."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(models.ENABLE_WAL)
                await db.execute(models.CREATE_SCORES_TABLE)
                await db.execute(models.CREATE_USERS_TABLE)
                await db.commit()
            self._initialized = True

    async def upsert_user(self, user: TelegramUser, chat_id: int) -> None:
        """Insert or update basic user information."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, chat_id, first_name, last_name, username)
                VALUES (?, ?, ?, ?, ?)
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

    async def ensure_row(self, user_id: int, chat_id: int) -> None:
        """Ensure a score row exists for given user and chat."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scores (user_id, chat_id, points, message_cnt, last_signin)
                VALUES (?, ?, 0, 0, NULL)
                ON CONFLICT(user_id, chat_id) DO NOTHING
                """,
                (user_id, chat_id),
            )
            await db.commit()

    async def add_message_point(self, user_id: int, chat_id: int, points: int = 1) -> models.Score:
        """Add points for a user message and return updated score."""
        await self.ensure_row(user_id, chat_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scores
                SET points = points + ?, message_cnt = message_cnt + 1
                WHERE user_id = ? AND chat_id = ?
                """,
                (points, user_id, chat_id),
            )
            await db.commit()
        score = await self.get_user_score(user_id, chat_id)
        if score is None:  # pragma: no cover - safeguard, shouldn't happen
            raise RuntimeError("Score row missing after add_message_point")
        return score

    async def signin(self, user_id: int, chat_id: int, bonus: int) -> bool:
        """Apply a daily sign-in bonus; return True if applied."""
        await self.ensure_row(user_id, chat_id)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT last_signin FROM scores WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            ) as cursor:
                row = await cursor.fetchone()
        last_signin = _parse_datetime(row["last_signin"]) if row else None
        today = datetime.now(timezone.utc).date()
        if last_signin is not None and last_signin.date() == today:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE scores
                SET points = points + ?, last_signin = ?
                WHERE user_id = ? AND chat_id = ?
                """,
                (bonus, datetime.now(timezone.utc).isoformat(), user_id, chat_id),
            )
            await db.commit()
        return True

    async def get_user_score(self, user_id: int, chat_id: int) -> models.Score | None:
        """Retrieve a user's score information."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT s.user_id, s.chat_id, s.points, s.message_cnt, s.last_signin,
                       u.first_name, u.last_name, u.username
                FROM scores AS s
                LEFT JOIN users AS u ON s.user_id = u.user_id AND s.chat_id = u.chat_id
                WHERE s.user_id = ? AND s.chat_id = ?
                """,
                (user_id, chat_id),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_score(row)

    async def get_rank(self, user_id: int, chat_id: int) -> int | None:
        """Get rank (1-based) of user in chat by points and message count."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = (
                "SELECT user_id FROM scores WHERE chat_id = ? ORDER BY points DESC,"
                " message_cnt DESC, user_id ASC"
            )
            async with db.execute(query, (chat_id,)) as cursor:
                rank = 1
                async for row in cursor:
                    if row["user_id"] == user_id:
                        return rank
                    rank += 1
        return None

    async def get_top(self, chat_id: int, limit: int = 10) -> list[models.Score]:
        """Return the top N scores for a chat."""
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = (
                """
                SELECT s.user_id, s.chat_id, s.points, s.message_cnt, s.last_signin,
                       u.first_name, u.last_name, u.username
                FROM scores AS s
                LEFT JOIN users AS u ON s.user_id = u.user_id AND s.chat_id = u.chat_id
                WHERE s.chat_id = ?
                ORDER BY s.points DESC, s.message_cnt DESC, s.user_id ASC
                LIMIT ?
                """
            )
            async with db.execute(query, (chat_id, limit)) as cursor:
                rows = await cursor.fetchall()
        return [_row_to_score(row) for row in rows]


def _row_to_score(row: aiosqlite.Row) -> models.Score:
    last_signin = _parse_datetime(row["last_signin"])
    keys = row.keys()
    return models.Score(
        user_id=row["user_id"],
        chat_id=row["chat_id"],
        points=row["points"],
        message_cnt=row["message_cnt"],
        last_signin=last_signin,
        first_name=row["first_name"] if "first_name" in keys else None,
        last_name=row["last_name"] if "last_name" in keys else None,
        username=row["username"] if "username" in keys else None,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
