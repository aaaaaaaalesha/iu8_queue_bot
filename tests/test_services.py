from __future__ import annotations

import asyncio
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import DeleteMessage, EditMessageText, PinChatMessage, SendMessage

from queue_bot.db.repository import Repository
from queue_bot.models import Member
from queue_bot.services.scheduler import QueueScheduler
from queue_bot.services.updater import QueueMessageUpdater
from tests.conftest import ADMIN_ID, CHAT_ID, FakeSession, make_active_queue


def edit_texts(session: FakeSession) -> list[str]:
    return [r.text for r in session.of_type(EditMessageText)]


async def test_updater_coalesces_edits(bot: Bot, session: FakeSession, repo: Repository) -> None:
    session.delay = 0.02
    queue = await make_active_queue(repo)
    updater = QueueMessageUpdater(bot, repo, interval=0.05)

    async def press(n: int) -> None:
        await repo.join(queue.id, Member(n, f"U{n}", None))
        updater.request(queue.id)

    await asyncio.gather(*(press(n) for n in range(100)))
    await updater.wait_idle()

    texts = edit_texts(session)
    assert 1 <= len(texts) <= 3, "100 presses must produce only a few edits"
    assert texts[-1].splitlines()[2:] == [f"{i}. U{i - 1}" for i in range(1, 101)]


async def test_updater_skips_unchanged_text(bot: Bot, session: FakeSession, repo: Repository) -> None:
    queue = await make_active_queue(repo)
    updater = QueueMessageUpdater(bot, repo, interval=0)
    updater.request(queue.id)
    await updater.wait_idle()
    updater.request(queue.id)
    await updater.wait_idle()
    assert len(edit_texts(session)) == 1


async def test_updater_waits_on_flood_control(bot: Bot, session: FakeSession, repo: Repository) -> None:
    queue = await make_active_queue(repo)
    await repo.join(queue.id, Member(1, "Ann", None))
    method = EditMessageText(text="", chat_id=CHAT_ID, message_id=777)
    session.fail_with = [
        TelegramRetryAfter(method=method, message="Too Many Requests", retry_after=0),
        TelegramBadRequest(method=method, message="Bad Request: message is not modified"),
    ]
    updater = QueueMessageUpdater(bot, repo, interval=0)
    updater.request(queue.id)
    await updater.wait_idle()
    # Both failures are handled; a later change is still delivered.
    await repo.join(queue.id, Member(2, "Bob", None))
    updater.request(queue.id)
    await updater.wait_idle()
    assert edit_texts(session)[-1].endswith("1. Ann\n2. Bob")


async def test_updater_stops_for_deleted_queue(bot: Bot, session: FakeSession, repo: Repository) -> None:
    queue = await make_active_queue(repo)
    await repo.delete_queue(queue.id, ADMIN_ID)
    updater = QueueMessageUpdater(bot, repo, interval=0)
    updater.request(queue.id)
    await updater.wait_idle()
    assert edit_texts(session) == []


async def test_scheduler_launches_queue(bot: Bot, session: FakeSession, repo: Repository) -> None:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    queue = await repo.create_queue(ADMIN_ID, CHAT_ID, "Лаба", int(time.time()) + 1)
    assert queue is not None
    scheduler = QueueScheduler(bot, repo, QueueMessageUpdater(bot, repo))
    await scheduler.restore()
    await asyncio.sleep(1.5)

    sent = session.of_type(SendMessage)
    assert [m.text for m in sent] == ["🆕 🅠🅤🅔🅤🅔 🆕\nОчередь «Лаба» запущена!"]
    assert session.of_type(PinChatMessage)
    launched = await repo.get_queue(queue.id)
    assert launched is not None and launched.message_id is not None
    assert await repo.list_planned_queues() == []
    await scheduler.close()


async def test_scheduler_cancel(bot: Bot, session: FakeSession, repo: Repository) -> None:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    queue = await repo.create_queue(ADMIN_ID, CHAT_ID, "Лаба", int(time.time()) + 1)
    assert queue is not None
    scheduler = QueueScheduler(bot, repo, QueueMessageUpdater(bot, repo))
    scheduler.schedule(queue)
    scheduler.cancel(queue.id)
    await asyncio.sleep(1.2)
    assert session.of_type(SendMessage) == []


async def test_queue_deleted_during_launch(bot: Bot, session: FakeSession, repo: Repository) -> None:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    queue = await repo.create_queue(ADMIN_ID, CHAT_ID, "Лаба", int(time.time()))
    assert queue is not None
    scheduler = QueueScheduler(bot, repo, QueueMessageUpdater(bot, repo))
    session.delay = 0.1

    launch = asyncio.create_task(scheduler.launch(queue.id))
    await asyncio.sleep(0.05)  # the message is being sent
    await repo.delete_queue(queue.id, ADMIN_ID)
    await launch

    assert len(session.of_type(SendMessage)) == 1
    assert len(session.of_type(DeleteMessage)) == 1, "the orphan message is removed"
