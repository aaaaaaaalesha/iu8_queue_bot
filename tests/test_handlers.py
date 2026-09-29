"""End-to-end tests: updates go through the real dispatcher, Bot API calls are faked."""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import AnswerCallbackQuery, DeleteMessage, EditMessageText, SendMessage
from aiogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Message,
    Update,
    User,
)

from queue_bot.app import build_dispatcher
from queue_bot.config import Settings
from queue_bot.db.repository import Repository
from queue_bot.keyboards.admin import ChooseChatCallback, DeleteQueueCallback
from queue_bot.keyboards.calendar import CalendarCallback
from queue_bot.keyboards.client import PLAN_QUEUE_TEXT
from tests.conftest import ADMIN_ID, BOT_ID, CHAT_ID, FakeSession

MSK = ZoneInfo("Europe/Moscow")
_ids = itertools.count(1)

GROUP = Chat(id=CHAT_ID, type="supergroup", title="ИУ8-51")
ADMIN = User(id=ADMIN_ID, is_bot=False, first_name="Admin", username="admin")
BOT_USER = User(id=BOT_ID, is_bot=True, first_name="Bot", username="queue_bot")


def private(user: User) -> Chat:
    return Chat(id=user.id, type="private")


def student(n: int) -> User:
    return User(id=1000 + n, is_bot=False, first_name=f"Student{n}", username=f"s{n}")


@dataclass
class App:
    dp: Dispatcher
    bot: Bot
    session: FakeSession
    repo: Repository

    async def feed(self, **kwargs: object) -> None:
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), **kwargs))

    async def message(self, user: User, text: str, chat: Chat | None = None) -> None:
        msg = Message(message_id=next(_ids), date=datetime.now(), chat=chat or private(user), from_user=user, text=text)
        await self.feed(message=msg)

    async def callback(self, user: User, data: str, chat: Chat, message_id: int, text: str = "x") -> None:
        msg = Message(message_id=message_id, date=datetime.now(), chat=chat, from_user=BOT_USER, text=text)
        query = CallbackQuery(id=str(next(_ids)), from_user=user, chat_instance="ci", message=msg, data=data)
        await self.feed(callback_query=query)

    def sent_to(self, chat_id: int) -> list[str]:
        return [m.text for m in self.session.of_type(SendMessage) if m.chat_id == chat_id]

    def answers(self) -> list[str | None]:
        return [a.text for a in self.session.of_type(AnswerCallbackQuery)]


@pytest.fixture
async def app(tmp_path: Path, session: FakeSession, bot: Bot) -> AsyncIterator[App]:
    settings = Settings(
        bot_token="unused",
        database_path=str(tmp_path / "bot.db"),
        timezone=MSK,
        edit_interval=0.01,
        log_level="INFO",
    )
    dp = build_dispatcher(settings, bot)
    await dp.emit_startup(bot=bot)
    yield App(dp=dp, bot=bot, session=session, repo=dp["repo"])
    await dp.emit_shutdown(bot=bot)


async def add_bot_to_group(app: App) -> None:
    await app.feed(
        my_chat_member=ChatMemberUpdated(
            chat=GROUP,
            from_user=ADMIN,
            date=datetime.now(),
            old_chat_member=ChatMemberLeft(user=BOT_USER),
            new_chat_member=ChatMemberMember(user=BOT_USER),
        )
    )


async def plan_queue(app: App, name: str, start: datetime) -> None:
    admin_chat = private(ADMIN)
    await app.message(ADMIN, PLAN_QUEUE_TEXT)
    await app.callback(ADMIN, ChooseChatCallback(chat_id=CHAT_ID).pack(), admin_chat, 1)
    await app.message(ADMIN, name)
    day = CalendarCallback(act="DAY", year=start.year, month=start.month, day=start.day).pack()
    await app.callback(ADMIN, day, admin_chat, 2)
    await app.message(ADMIN, start.strftime("%H:%M"))


async def launched_queue_message_id(app: App) -> int:
    queues = await app.repo.list_admin_queues(ADMIN_ID)
    assert queues and queues[-1].message_id is not None
    return queues[-1].message_id


async def test_full_flow_with_concurrent_presses(app: App) -> None:
    await add_bot_to_group(app)
    assert any("Admin (@admin) – администратор очередей" in t for t in app.sent_to(CHAT_ID))

    start = datetime.now(MSK).replace(second=0, microsecond=0) + timedelta(minutes=1)
    await plan_queue(app, "Лаба 1", start)
    assert f"✅Очередь «Лаба 1» запланирована в чате «ИУ8-51»!\nНачало очереди: {start:%d.%m.%Y в %H:%M}" in (
        app.sent_to(ADMIN_ID)
    )
    queue = (await app.repo.list_admin_queues(ADMIN_ID))[0]
    await app.dp["scheduler"].launch(queue.id)
    message_id = await launched_queue_message_id(app)

    # 60 students press "sign in" at the same moment, some of them twice.
    presses = [app.callback(student(n), "sign_in", GROUP, message_id) for n in range(60)]
    presses += [app.callback(student(n), "sign_in", GROUP, message_id) for n in range(0, 60, 3)]
    await asyncio.gather(*presses)
    # Some of them immediately leave or let others go ahead.
    await asyncio.gather(
        *(app.callback(student(n), "sign_out", GROUP, message_id) for n in range(0, 60, 2)),
        *(app.callback(student(n), "skip_ahead", GROUP, message_id) for n in range(1, 60, 4)),
    )
    await app.dp["updater"].wait_idle()

    members = await app.repo.get_members(queue.id)
    assert sorted(m.user_id for m in members if m.user_id) == [1000 + n for n in range(1, 60, 2)]
    assert app.answers().count("❕ Вы уже в очереди.") == 20

    edits = app.session.of_type(EditMessageText)
    assert len(edits) < 20, "edits are coalesced"
    lines = edits[-1].text.splitlines()
    assert lines[:2] == ["🆕 🅠🅤🅔🅤🅔 🆕", "Очередь «Лаба 1» запущена!"]
    assert lines[2:] == [f"{i}. {m.label}" for i, m in enumerate(members, 1)]


async def test_status_answers(app: App) -> None:
    await add_bot_to_group(app)
    await plan_queue(app, "Лаба", datetime.now(MSK) + timedelta(minutes=5))
    queue = (await app.repo.list_admin_queues(ADMIN_ID))[0]
    await app.dp["scheduler"].launch(queue.id)
    mid = await launched_queue_message_id(app)
    before = len(app.answers())

    await app.callback(student(1), "sign_out", GROUP, mid)
    await app.callback(student(1), "sign_in", GROUP, mid)
    await app.callback(student(1), "skip_ahead", GROUP, mid)
    await app.callback(student(2), "sign_out", GROUP, mid)
    await app.callback(student(2), "sign_in", GROUP, mid)
    await app.callback(student(3), "in_tail", GROUP, mid)
    await app.callback(student(2), "in_tail", GROUP, mid)
    await app.callback(student(1), "sign_in", GROUP, 123456)  # unknown message

    assert app.answers()[before:] == [
        "❕ В очереди ещё нет участников.",
        None,
        "❕ В очереди только один участник.",
        "❕ @s2 ещё не участник очереди.",
        None,
        "❕ Вы ещё не участник очереди.",
        "❕ Вы крайний в очереди.",
        "❕ Эта очередь больше не активна.",
    ]


async def test_invalid_time_and_cancel(app: App) -> None:
    await add_bot_to_group(app)
    await app.message(ADMIN, PLAN_QUEUE_TEXT)
    await app.callback(ADMIN, ChooseChatCallback(chat_id=CHAT_ID).pack(), private(ADMIN), 1)
    await app.message(ADMIN, "Лаба")
    today = datetime.now(MSK)
    day = CalendarCallback(act="DAY", year=today.year, month=today.month, day=today.day).pack()
    await app.callback(ADMIN, day, private(ADMIN), 2)
    await app.message(ADMIN, "25:99")
    assert app.sent_to(ADMIN_ID)[-1].startswith("❌ Время задано неверно!")

    await app.callback(ADMIN, "cancel_call", private(ADMIN), 3)
    assert app.answers()[-1] == "🚫 Действие отменено"
    await app.message(ADMIN, "15:40")  # not in the planning state anymore
    assert await app.repo.list_admin_queues(ADMIN_ID) == []


async def test_foreign_chat_cannot_be_chosen(app: App) -> None:
    await add_bot_to_group(app)
    stranger = User(id=5, is_bot=False, first_name="Eve", username="eve")
    await app.repo.add_chat(-1, "Своя", stranger.id, "eve")
    await app.message(stranger, PLAN_QUEUE_TEXT)
    await app.callback(stranger, ChooseChatCallback(chat_id=CHAT_ID).pack(), private(stranger), 1)
    assert app.answers()[-1] == "🚫 Действие отменено"


async def test_delete_launched_queue(app: App) -> None:
    await add_bot_to_group(app)
    await plan_queue(app, "Лаба", datetime.now(MSK) + timedelta(minutes=5))
    queue = (await app.repo.list_admin_queues(ADMIN_ID))[0]
    await app.dp["scheduler"].launch(queue.id)
    mid = await launched_queue_message_id(app)

    await app.message(ADMIN, "/delete_queue")
    await app.callback(ADMIN, DeleteQueueCallback(queue_id=queue.id).pack(), private(ADMIN), 50)
    assert app.answers()[-1] == "💥 Очередь удалена"
    deleted = {(d.chat_id, d.message_id) for d in app.session.of_type(DeleteMessage)}
    assert (CHAT_ID, mid) in deleted
    assert await app.repo.list_admin_queues(ADMIN_ID) == []

    await app.callback(student(1), "sign_in", GROUP, mid)
    assert app.answers()[-1] == "❕ Эта очередь больше не активна."


async def test_bot_removed_from_chat(app: App) -> None:
    await add_bot_to_group(app)
    await plan_queue(app, "Лаба", datetime.now(MSK) + timedelta(minutes=5))
    await app.feed(
        my_chat_member=ChatMemberUpdated(
            chat=GROUP,
            from_user=ADMIN,
            date=datetime.now(),
            old_chat_member=ChatMemberMember(user=BOT_USER),
            new_chat_member=ChatMemberLeft(user=BOT_USER),
        )
    )
    assert await app.repo.list_admin_queues(ADMIN_ID) == []
    assert await app.repo.list_admin_chats(ADMIN_ID) == []
