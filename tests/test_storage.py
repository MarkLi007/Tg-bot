"""Tests for storage layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from src.bot import storage


@dataclass
class DummyUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


@pytest_asyncio.fixture(autouse=True)
async def setup_db(tmp_path):
    db_path = tmp_path / "points.db"
    await storage.init_db(str(db_path))
    yield


@pytest.mark.asyncio
async def test_ensure_row_creates_entry() -> None:
    async with storage.get_db() as db:
        await storage.ensure_row(db, 1, 100)
        row = await storage.get_user_score(db, 1, 100)
    assert row is not None
    assert row["points"] == 0
    assert row["message_cnt"] == 0
    assert row["last_signin"] is None


@pytest.mark.asyncio
async def test_add_message_point_updates_score() -> None:
    user = DummyUser(1, "Alice")
    async with storage.get_db() as db:
        await storage.ensure_row(db, user.id, 100)
        await storage.upsert_user(db, user, 100)
        await storage.add_message_point(db, user.id, 100, points=2)
        row = await storage.get_user_score(db, user.id, 100)
    assert row is not None
    assert row["points"] == 2
    assert row["message_cnt"] == 1


@pytest.mark.asyncio
async def test_signin_only_once_per_day(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr("src.bot.storage.datetime", FixedDatetime)
    user = DummyUser(1, "Alice")
    async with storage.get_db() as db:
        await storage.ensure_row(db, user.id, 100)
        await storage.upsert_user(db, user, 100)
        applied = await storage.signin(db, user.id, 100, bonus=10)
        assert applied is True
        applied_again = await storage.signin(db, user.id, 100, bonus=10)
        assert applied_again is False


@pytest.mark.asyncio
async def test_rank_and_top() -> None:
    user1 = DummyUser(1, "Alice", username="alice")
    user2 = DummyUser(2, "Bob", last_name="Builder")
    async with storage.get_db() as db:
        await storage.ensure_row(db, user1.id, 200)
        await storage.ensure_row(db, user2.id, 200)
        await storage.upsert_user(db, user1, 200)
        await storage.upsert_user(db, user2, 200)
        await storage.add_message_point(db, user1.id, 200, points=5)
        await storage.add_message_point(db, user2.id, 200, points=2)
        await storage.add_message_point(db, user2.id, 200, points=1)
        rank_user1 = await storage.get_rank(db, user1.id, 200)
        rank_user2 = await storage.get_rank(db, user2.id, 200)
        rows = await storage.get_top(db, 200, limit=5)
    assert rank_user1 == 1
    assert rank_user2 == 2
    assert [row["user_id"] for row in rows] == [1, 2]
    assert rows[0]["username"] == "alice"
    assert rows[1]["last_name"] == "Builder"
