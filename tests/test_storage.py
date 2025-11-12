from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
import pytest_asyncio


@dataclass
class DummyUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


@pytest_asyncio.fixture
async def storage(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "test-token")
    db_path = tmp_path / "points.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    from src.bot import settings

    importlib.reload(settings)

    from src.bot import storage as storage_module

    importlib.reload(storage_module)
    await storage_module.init_db()
    yield storage_module


@pytest.mark.asyncio
async def test_ensure_row_and_user_upsert(storage) -> None:
    async with storage.get_db() as db:
        await storage.ensure_row(db, 1, 100)
        await storage.upsert_user(db, DummyUser(1, "Alice"), 100)
        score = await storage.get_user_score(db, 1, 100)
    assert score is not None
    assert score.points == 0
    assert score.message_cnt == 0
    assert score.first_name == "Alice"


@pytest.mark.asyncio
async def test_add_message_point_updates_score(storage) -> None:
    async with storage.get_db() as db:
        await storage.ensure_row(db, 1, 100)
        await storage.upsert_user(db, DummyUser(1, "Alice"), 100)
        await storage.add_message_point(db, 1, 100, points=2)
        score = await storage.get_user_score(db, 1, 100)
    assert score is not None
    assert score.points == 2
    assert score.message_cnt == 1


@pytest.mark.asyncio
async def test_signin_only_once_per_day(storage, monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = datetime(2024, 1, 1, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return frozen if tz is None else frozen.astimezone(tz)

    monkeypatch.setattr(storage, "datetime", FixedDatetime)

    async with storage.get_db() as db:
        await storage.ensure_row(db, 1, 100)
        await storage.upsert_user(db, DummyUser(1, "Alice"), 100)
        applied = await storage.signin(db, 1, 100, bonus=10)
        again = await storage.signin(db, 1, 100, bonus=10)
        score = await storage.get_user_score(db, 1, 100)
    assert applied is True
    assert again is False
    assert score is not None and score.points == 10


@pytest.mark.asyncio
async def test_rank_and_top(storage) -> None:
    async with storage.get_db() as db:
        await storage.ensure_row(db, 1, 200)
        await storage.upsert_user(db, DummyUser(1, "Alice", username="alice"), 200)
        await storage.ensure_row(db, 2, 200)
        await storage.upsert_user(db, DummyUser(2, "Bob", last_name="Builder"), 200)
        await storage.add_message_point(db, 1, 200, points=5)
        await storage.add_message_point(db, 2, 200, points=2)
        await storage.add_message_point(db, 2, 200, points=1)
        rank_user1 = await storage.get_rank(db, 1, 200)
        rank_user2 = await storage.get_rank(db, 2, 200)
        top = await storage.get_top(db, 200, limit=5)
    assert rank_user1 == 1
    assert rank_user2 == 2
    assert [score.user_id for score in top] == [1, 2]
    assert top[0].username == "alice"
    assert top[1].last_name == "Builder"
