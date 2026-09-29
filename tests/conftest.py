from __future__ import annotations

import asyncio
import itertools
import time
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import EditMessageText, SendMessage, TelegramMethod
from aiogram.types import Chat, Message

from queue_bot.db.database import Database
from queue_bot.db.repository import Repository
from queue_bot.models import Queue

BOT_ID = 42
TOKEN = f"{BOT_ID}:TEST-token"
CHAT_ID = -100500
ADMIN_ID = 1


class FakeSession(BaseSession):
    """Answers every Bot API call without network and records the calls."""

    def __init__(self, delay: float = 0.0) -> None:
        super().__init__()
        self.delay = delay
        self.requests: list[TelegramMethod[Any]] = []
        self.fail_with: list[Exception] = []
        self._message_ids = itertools.count(1000)

    def of_type[T](self, method_type: type[T]) -> list[T]:
        return [r for r in self.requests if isinstance(r, method_type)]

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_with:
            raise self.fail_with.pop(0)
        self.requests.append(method)
        if isinstance(method, SendMessage | EditMessageText):
            message_id = getattr(method, "message_id", None) or next(self._message_ids)
            chat_id = int(method.chat_id or 0)
            return Message(
                message_id=message_id,
                date=datetime.now(),
                chat=Chat(id=chat_id, type="supergroup" if chat_id < 0 else "private"),
                text=method.text,
            )
        return True

    async def close(self) -> None:
        pass

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError


@pytest.fixture
def session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def bot(session: FakeSession) -> Bot:
    return Bot(TOKEN, session=session)


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[Database]:
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def repo(db: Database) -> Repository:
    return Repository(db)


async def make_active_queue(repo: Repository, message_id: int = 777, name: str = "Лаба") -> Queue:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    queue = await repo.create_queue(ADMIN_ID, CHAT_ID, name, int(time.time()))
    assert queue is not None
    assert await repo.mark_launched(queue.id, message_id)
    launched = await repo.get_queue(queue.id)
    assert launched is not None
    return launched
