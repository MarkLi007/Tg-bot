"""Tests for storage layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from src.bot.storage import Storage


@pytest_asyncio.fixture
async def storage(tmp_path):
    db_path = tmp_path / "points.db"
    store = Storage(str(db_path))
    await store.initialize()
    yield store


@dataclass
class DummyUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


@pytest.mark.asyncio
async def test_ensure_row_creates_entry(storage: Storage) -> None:
    await storage.upsert_user(DummyUser(1, "Alice"), 100)
    await storage.ensure_row(1, 100)
    score = await storage.get_user_score(1, 100)
    assert score is not None
    assert score.points == 0
    assert score.message_cnt == 0
    assert score.last_signin is None


@pytest.mark.asyncio
async def test_add_message_point_updates_score(storage: Storage) -> None:
    await storage.upsert_user(DummyUser(1, "Alice"), 100)
    await storage.add_message_point(1, 100, points=2)
    score = await storage.get_user_score(1, 100)
    assert score is not None
    assert score.points == 2
    assert score.message_cnt == 1


@pytest.mark.asyncio
async def test_signin_only_once_per_day(storage: Storage, monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr("src.bot.storage.datetime", FixedDatetime)
    await storage.upsert_user(DummyUser(1, "Alice"), 100)
    # first signin should succeed
    applied = await storage.signin(1, 100, bonus=10)
    assert applied is True
    score = await storage.get_user_score(1, 100)
    assert score is not None
    assert score.points == 10
    # second signin same day should fail
    applied_again = await storage.signin(1, 100, bonus=10)
    assert applied_again is False


@pytest.mark.asyncio
async def test_rank_and_top(storage: Storage) -> None:
    await storage.upsert_user(DummyUser(1, "Alice", username="alice"), 200)
    await storage.upsert_user(DummyUser(2, "Bob", last_name="Builder"), 200)
    await storage.add_message_point(1, 200, points=5)
    await storage.add_message_point(2, 200, points=2)
    await storage.add_message_point(2, 200, points=1)

    rank_user1 = await storage.get_rank(1, 200)
    rank_user2 = await storage.get_rank(2, 200)
    assert rank_user1 == 1
    assert rank_user2 == 2

    top = await storage.get_top(200, limit=5)
    assert [score.user_id for score in top] == [1, 2]
    assert top[0].username == "alice"
    assert top[1].last_name == "Builder"
