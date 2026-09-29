from __future__ import annotations

import asyncio
import random
import time

from queue_bot.db.database import Database
from queue_bot.db.repository import Repository
from queue_bot.models import Member, OpStatus
from tests.conftest import ADMIN_ID, CHAT_ID, make_active_queue


def user(n: int) -> Member:
    return Member(user_id=n, first_name=f"User{n}", username=f"user{n}")


async def names(repo: Repository, queue_id: int) -> list[str]:
    return [m.first_name for m in await repo.get_members(queue_id)]


async def test_join_and_leave(repo: Repository) -> None:
    queue = await make_active_queue(repo)

    assert await repo.leave(queue.id, user(1)) is OpStatus.NO_QUEUERS
    assert await repo.join(queue.id, user(1)) is OpStatus.OK
    assert await repo.join(queue.id, user(1)) is OpStatus.ALREADY_IN
    assert await repo.join(queue.id, user(2)) is OpStatus.OK
    assert await repo.leave(queue.id, user(3)) is OpStatus.NOT_QUEUER
    assert await names(repo, queue.id) == ["User1", "User2"]

    assert await repo.leave(queue.id, user(1)) is OpStatus.OK
    assert await names(repo, queue.id) == ["User2"]


async def test_skip_ahead_and_tail(repo: Repository) -> None:
    queue = await make_active_queue(repo)

    assert await repo.skip_ahead(queue.id, user(1)) is OpStatus.NO_QUEUERS
    await repo.join(queue.id, user(1))
    assert await repo.skip_ahead(queue.id, user(1)) is OpStatus.ONE_QUEUER
    assert await repo.push_tail(queue.id, user(1)) is OpStatus.ONE_QUEUER
    for n in (2, 3, 4):
        await repo.join(queue.id, user(n))

    assert await repo.skip_ahead(queue.id, user(9)) is OpStatus.NOT_QUEUER
    assert await repo.skip_ahead(queue.id, user(4)) is OpStatus.NO_AFTER
    assert await repo.push_tail(queue.id, user(4)) is OpStatus.NO_AFTER

    assert await repo.skip_ahead(queue.id, user(1)) is OpStatus.OK
    assert await names(repo, queue.id) == ["User2", "User1", "User3", "User4"]

    assert await repo.push_tail(queue.id, user(2)) is OpStatus.OK
    assert await names(repo, queue.id) == ["User1", "User3", "User4", "User2"]

    # Rejoining after leaving puts the user at the end.
    await repo.leave(queue.id, user(1))
    await repo.join(queue.id, user(1))
    assert await names(repo, queue.id) == ["User3", "User4", "User2", "User1"]


async def test_operations_on_unknown_queue(repo: Repository) -> None:
    assert await repo.join(12345, user(1)) is OpStatus.QUEUE_NOT_FOUND
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    planned = await repo.create_queue(ADMIN_ID, CHAT_ID, "Позже", int(time.time()) + 3600)
    assert planned is not None
    # Not launched yet.
    assert await repo.join(planned.id, user(1)) is OpStatus.QUEUE_NOT_FOUND


async def test_concurrent_joins_of_different_users(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    results = await asyncio.gather(*(repo.join(queue.id, user(n)) for n in range(200)))

    assert all(r is OpStatus.OK for r in results)
    members = await repo.get_members(queue.id)
    assert sorted(m.user_id for m in members if m.user_id is not None) == list(range(200))
    # Joins are applied in the order they were issued.
    assert [m.user_id for m in members] == list(range(200))


async def test_concurrent_double_clicks_of_one_user(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    results = await asyncio.gather(*(repo.join(queue.id, user(1)) for _ in range(50)))

    assert results.count(OpStatus.OK) == 1
    assert results.count(OpStatus.ALREADY_IN) == 49
    assert await names(repo, queue.id) == ["User1"]


async def test_concurrent_mixed_operations_keep_queue_consistent(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    for n in range(50):
        await repo.join(queue.id, user(n))

    rng = random.Random(1)
    leaving = set(rng.sample(range(50), 20))
    newcomers = range(50, 80)
    ops = [repo.leave(queue.id, user(n)) for n in leaving]
    ops += [repo.join(queue.id, user(n)) for n in newcomers]
    ops += [repo.skip_ahead(queue.id, user(n)) for n in rng.sample(range(80), 30)]
    ops += [repo.push_tail(queue.id, user(n)) for n in rng.sample(range(80), 30)]
    rng.shuffle(ops)
    await asyncio.gather(*ops)

    members = await repo.get_members(queue.id)
    ids = [m.user_id for m in members]
    assert len(ids) == len(set(ids)), "nobody is in the queue twice"
    assert set(ids) == (set(range(50)) - leaving) | set(newcomers)


async def test_delete_queue_requires_owner(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    assert await repo.delete_queue(queue.id, admin_id=999) is None
    deleted = await repo.delete_queue(queue.id, ADMIN_ID)
    assert deleted is not None and deleted.message_id == 777
    assert await repo.get_queue(queue.id) is None
    assert await repo.delete_queue(queue.id, ADMIN_ID) is None


async def test_mark_launched_after_delete(repo: Repository) -> None:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    queue = await repo.create_queue(ADMIN_ID, CHAT_ID, "Лаба", int(time.time()))
    assert queue is not None
    await repo.delete_queue(queue.id, ADMIN_ID)
    assert not await repo.mark_launched(queue.id, 1)


async def test_create_queue_in_foreign_chat(repo: Repository) -> None:
    await repo.add_chat(CHAT_ID, "Группа", ADMIN_ID, "admin")
    assert await repo.create_queue(999, CHAT_ID, "Лаба", int(time.time())) is None


async def test_remove_chat_cascades(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    await repo.join(queue.id, user(1))
    assert await repo.remove_chat(CHAT_ID) == [queue.id]
    assert await repo.get_queue(queue.id) is None
    assert await repo.get_members(queue.id) == []
    assert await repo.list_admin_chats(ADMIN_ID) == []


async def test_chat_migration_moves_queues(repo: Repository) -> None:
    queue = await make_active_queue(repo)
    await repo.migrate_chat(CHAT_ID, -100999)
    moved = await repo.get_queue(queue.id)
    assert moved is not None and moved.chat_id == -100999
    assert [c.chat_id for c in await repo.list_admin_chats(ADMIN_ID)] == [-100999]


async def test_legacy_members_are_claimed_by_their_owners(db: Database, repo: Repository) -> None:
    queue = await make_active_queue(repo)
    async with db.transaction() as conn:
        await conn.execute("UPDATE queues SET legacy_pending = 1 WHERE id = ?", (queue.id,))
    await repo.import_legacy_members(queue.id, ["Ann (@ann)", "Bob (@None)", "Carl (@carl)"])
    # A second import is ignored.
    await repo.import_legacy_members(queue.id, ["Zed (@zed)"])
    assert await names(repo, queue.id) == ["Ann (@ann)", "Bob (@None)", "Carl (@carl)"]

    assert await repo.join(queue.id, Member(10, "Ann", "ann")) is OpStatus.ALREADY_IN
    assert await repo.skip_ahead(queue.id, Member(11, "Bob", None)) is OpStatus.OK
    members = await repo.get_members(queue.id)
    assert [m.label for m in members] == ["Ann (@ann)", "Carl (@carl)", "Bob"]
    assert [m.user_id for m in members] == [10, None, 11]
