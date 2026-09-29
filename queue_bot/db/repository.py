"""All SQL used by the bot.

Each public method runs in its own transaction (see :class:`Database`), so a
queue operation reads the current state and applies its change atomically.
"""

from __future__ import annotations

from collections.abc import Sequence

import aiosqlite

from queue_bot.db.database import Database
from queue_bot.models import Chat, Member, OpStatus, Queue

_QUEUE_COLUMNS = (
    "q.id, q.admin_id, q.chat_id, c.title AS chat_title, q.name, q.start_at, q.message_id, q.legacy_pending"
)
_QUEUE_SELECT = f"SELECT {_QUEUE_COLUMNS} FROM queues q JOIN chats c ON c.chat_id = q.chat_id"


def _queue(row: aiosqlite.Row) -> Queue:
    return Queue(
        id=row["id"],
        admin_id=row["admin_id"],
        chat_id=row["chat_id"],
        chat_title=row["chat_title"],
        name=row["name"],
        start_at=row["start_at"],
        message_id=row["message_id"],
        legacy_pending=bool(row["legacy_pending"]),
    )


def _member(row: aiosqlite.Row) -> Member:
    return Member(user_id=row["user_id"], first_name=row["first_name"], username=row["username"])


class Repository:
    def __init__(self, db: Database) -> None:
        self._db = db

    # ----------------------------------------------------------------- admins & chats

    async def upsert_admin(self, user_id: int, username: str | None) -> None:
        async with self._db.transaction() as conn:
            await self._upsert_admin(conn, user_id, username)

    @staticmethod
    async def _upsert_admin(conn: aiosqlite.Connection, user_id: int, username: str | None) -> None:
        await conn.execute(
            "INSERT INTO admins (user_id, username) VALUES (?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET username = excluded.username",
            (user_id, username),
        )

    async def add_chat(self, chat_id: int, title: str, admin_id: int, admin_username: str | None) -> None:
        async with self._db.transaction() as conn:
            await self._upsert_admin(conn, admin_id, admin_username)
            await conn.execute(
                "INSERT INTO chats (chat_id, title, admin_id) VALUES (?, ?, ?) "
                "ON CONFLICT (chat_id) DO UPDATE SET title = excluded.title, admin_id = excluded.admin_id",
                (chat_id, title, admin_id),
            )

    async def remove_chat(self, chat_id: int) -> list[int]:
        """Forget the chat and all its queues. Returns ids of the deleted queues."""
        async with self._db.transaction() as conn:
            cursor = await conn.execute("SELECT id FROM queues WHERE chat_id = ?", (chat_id,))
            queue_ids = [row["id"] for row in await cursor.fetchall()]
            await conn.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        return queue_ids

    async def rename_chat(self, chat_id: int, title: str) -> None:
        async with self._db.transaction() as conn:
            await conn.execute("UPDATE chats SET title = ? WHERE chat_id = ?", (title, chat_id))

    async def migrate_chat(self, old_chat_id: int, new_chat_id: int) -> None:
        """A group was upgraded to a supergroup and got a new id."""
        async with self._db.transaction() as conn:
            cursor = await conn.execute("SELECT 1 FROM chats WHERE chat_id = ?", (new_chat_id,))
            if await cursor.fetchone() is None:
                # ON UPDATE CASCADE moves the queues as well.
                await conn.execute("UPDATE chats SET chat_id = ? WHERE chat_id = ?", (new_chat_id, old_chat_id))
            else:
                await conn.execute("UPDATE queues SET chat_id = ? WHERE chat_id = ?", (new_chat_id, old_chat_id))
                await conn.execute("DELETE FROM chats WHERE chat_id = ?", (old_chat_id,))

    async def list_admin_chats(self, admin_id: int) -> list[Chat]:
        async with self._db.read() as conn:
            cursor = await conn.execute(
                "SELECT chat_id, title, admin_id FROM chats WHERE admin_id = ? ORDER BY title", (admin_id,)
            )
            rows = await cursor.fetchall()
        return [Chat(chat_id=r["chat_id"], title=r["title"], admin_id=r["admin_id"]) for r in rows]

    async def get_admin_chat(self, chat_id: int, admin_id: int) -> Chat | None:
        async with self._db.read() as conn:
            cursor = await conn.execute(
                "SELECT chat_id, title, admin_id FROM chats WHERE chat_id = ? AND admin_id = ?", (chat_id, admin_id)
            )
            row = await cursor.fetchone()
        return Chat(chat_id=row["chat_id"], title=row["title"], admin_id=row["admin_id"]) if row else None

    # ----------------------------------------------------------------- queues

    async def create_queue(self, admin_id: int, chat_id: int, name: str, start_at: int) -> Queue | None:
        """Create a planned queue. Returns None if the chat is not managed by the admin anymore."""
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                "INSERT INTO queues (admin_id, chat_id, name, start_at) "
                "SELECT ?, chat_id, ?, ? FROM chats WHERE chat_id = ? AND admin_id = ?",
                (admin_id, name, start_at, chat_id, admin_id),
            )
            if cursor.rowcount != 1:
                return None
            return await self._get_queue(conn, cursor.lastrowid)

    @staticmethod
    async def _get_queue(conn: aiosqlite.Connection, queue_id: int | None) -> Queue | None:
        cursor = await conn.execute(f"{_QUEUE_SELECT} WHERE q.id = ?", (queue_id,))
        row = await cursor.fetchone()
        return _queue(row) if row else None

    async def get_queue(self, queue_id: int) -> Queue | None:
        async with self._db.read() as conn:
            return await self._get_queue(conn, queue_id)

    async def find_queue_by_message(self, chat_id: int, message_id: int) -> Queue | None:
        async with self._db.read() as conn:
            cursor = await conn.execute(
                f"{_QUEUE_SELECT} WHERE q.chat_id = ? AND q.message_id = ?", (chat_id, message_id)
            )
            row = await cursor.fetchone()
        return _queue(row) if row else None

    async def list_admin_queues(self, admin_id: int) -> list[Queue]:
        async with self._db.read() as conn:
            cursor = await conn.execute(f"{_QUEUE_SELECT} WHERE q.admin_id = ? ORDER BY q.start_at, q.id", (admin_id,))
            rows = await cursor.fetchall()
        return [_queue(r) for r in rows]

    async def list_planned_queues(self) -> list[Queue]:
        async with self._db.read() as conn:
            cursor = await conn.execute(f"{_QUEUE_SELECT} WHERE q.message_id IS NULL ORDER BY q.start_at")
            rows = await cursor.fetchall()
        return [_queue(r) for r in rows]

    async def mark_launched(self, queue_id: int, message_id: int) -> bool:
        """Bind the posted message to a planned queue. False if the queue was deleted meanwhile."""
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                "UPDATE queues SET message_id = ? WHERE id = ? AND message_id IS NULL", (message_id, queue_id)
            )
            return cursor.rowcount == 1

    async def delete_queue(self, queue_id: int, admin_id: int) -> Queue | None:
        async with self._db.transaction() as conn:
            queue = await self._get_queue(conn, queue_id)
            if queue is None or queue.admin_id != admin_id:
                return None
            await conn.execute("DELETE FROM queues WHERE id = ?", (queue_id,))
            return queue

    # ----------------------------------------------------------------- members

    async def get_members(self, queue_id: int) -> list[Member]:
        async with self._db.read() as conn:
            return await self._members(conn, queue_id)

    async def get_queue_with_members(self, queue_id: int) -> tuple[Queue, list[Member]] | None:
        async with self._db.read() as conn:
            queue = await self._get_queue(conn, queue_id)
            if queue is None:
                return None
            return queue, await self._members(conn, queue_id)

    @staticmethod
    async def _members(conn: aiosqlite.Connection, queue_id: int) -> list[Member]:
        cursor = await conn.execute(
            "SELECT user_id, first_name, username FROM queue_members WHERE queue_id = ? ORDER BY position, id",
            (queue_id,),
        )
        return [_member(r) for r in await cursor.fetchall()]

    async def import_legacy_members(self, queue_id: int, labels: Sequence[str]) -> None:
        """Import members of a pre-v1 queue parsed from its message text (only once)."""
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                "UPDATE queues SET legacy_pending = 0 WHERE id = ? AND legacy_pending = 1", (queue_id,)
            )
            if cursor.rowcount != 1:
                return
            await conn.executemany(
                "INSERT INTO queue_members (queue_id, user_id, first_name, username, position) "
                "VALUES (?, NULL, ?, NULL, ?)",
                [(queue_id, label, position) for position, label in enumerate(labels, start=1)],
            )

    @staticmethod
    async def _find_member(conn: aiosqlite.Connection, queue_id: int, user: Member) -> tuple[int, int] | None:
        """Return (row id, position) of the user in the queue."""
        cursor = await conn.execute(
            "SELECT id, position FROM queue_members WHERE queue_id = ? AND user_id = ?", (queue_id, user.user_id)
        )
        row = await cursor.fetchone()
        if row is not None:
            return row["id"], row["position"]

        # Members imported from a pre-v1 message are known only by their label
        # (the old bot rendered a missing username as "@None").
        cursor = await conn.execute(
            "SELECT id, position FROM queue_members "
            "WHERE queue_id = ? AND user_id IS NULL AND first_name IN (?, ?) ORDER BY position LIMIT 1",
            (queue_id, user.label, f"{user.first_name} (@{user.username})"),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        await conn.execute(
            "UPDATE queue_members SET user_id = ?, first_name = ?, username = ? WHERE id = ?",
            (user.user_id, user.first_name, user.username, row["id"]),
        )
        return row["id"], row["position"]

    @staticmethod
    async def _queue_is_active(conn: aiosqlite.Connection, queue_id: int) -> bool:
        cursor = await conn.execute("SELECT 1 FROM queues WHERE id = ? AND message_id IS NOT NULL", (queue_id,))
        return await cursor.fetchone() is not None

    @staticmethod
    async def _count(conn: aiosqlite.Connection, queue_id: int) -> int:
        cursor = await conn.execute("SELECT COUNT(*) FROM queue_members WHERE queue_id = ?", (queue_id,))
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    async def _next_position(conn: aiosqlite.Connection, queue_id: int) -> int:
        cursor = await conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM queue_members WHERE queue_id = ?", (queue_id,)
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 1

    @staticmethod
    async def _member_after(
        conn: aiosqlite.Connection, queue_id: int, row_id: int, position: int
    ) -> tuple[int, int] | None:
        cursor = await conn.execute(
            "SELECT id, position FROM queue_members "
            "WHERE queue_id = ? AND (position > ? OR (position = ? AND id > ?)) "
            "ORDER BY position, id LIMIT 1",
            (queue_id, position, position, row_id),
        )
        row = await cursor.fetchone()
        return (row["id"], row["position"]) if row else None

    async def join(self, queue_id: int, user: Member) -> OpStatus:
        async with self._db.transaction() as conn:
            if not await self._queue_is_active(conn, queue_id):
                return OpStatus.QUEUE_NOT_FOUND
            if await self._find_member(conn, queue_id, user) is not None:
                return OpStatus.ALREADY_IN
            await conn.execute(
                "INSERT INTO queue_members (queue_id, user_id, first_name, username, position) VALUES (?, ?, ?, ?, ?)",
                (queue_id, user.user_id, user.first_name, user.username, await self._next_position(conn, queue_id)),
            )
            return OpStatus.OK

    async def leave(self, queue_id: int, user: Member) -> OpStatus:
        async with self._db.transaction() as conn:
            if not await self._queue_is_active(conn, queue_id):
                return OpStatus.QUEUE_NOT_FOUND
            if await self._count(conn, queue_id) == 0:
                return OpStatus.NO_QUEUERS
            found = await self._find_member(conn, queue_id, user)
            if found is None:
                return OpStatus.NOT_QUEUER
            await conn.execute("DELETE FROM queue_members WHERE id = ?", (found[0],))
            return OpStatus.OK

    async def _check_movable(
        self, conn: aiosqlite.Connection, queue_id: int, user: Member
    ) -> OpStatus | tuple[tuple[int, int], tuple[int, int]]:
        """Common checks of "skip ahead" and "to the tail". Returns the user and the member after them."""
        if not await self._queue_is_active(conn, queue_id):
            return OpStatus.QUEUE_NOT_FOUND
        count = await self._count(conn, queue_id)
        if count == 0:
            return OpStatus.NO_QUEUERS
        if count == 1:
            return OpStatus.ONE_QUEUER
        me = await self._find_member(conn, queue_id, user)
        if me is None:
            return OpStatus.NOT_QUEUER
        after = await self._member_after(conn, queue_id, *me)
        if after is None:
            return OpStatus.NO_AFTER
        return me, after

    async def skip_ahead(self, queue_id: int, user: Member) -> OpStatus:
        """Let the next person go ahead: swap the user with the one behind them."""
        async with self._db.transaction() as conn:
            checked = await self._check_movable(conn, queue_id, user)
            if isinstance(checked, OpStatus):
                return checked
            (my_id, my_pos), (next_id, next_pos) = checked
            await conn.execute("UPDATE queue_members SET position = ? WHERE id = ?", (next_pos, my_id))
            await conn.execute("UPDATE queue_members SET position = ? WHERE id = ?", (my_pos, next_id))
            return OpStatus.OK

    async def push_tail(self, queue_id: int, user: Member) -> OpStatus:
        """Move the user to the end of the queue."""
        async with self._db.transaction() as conn:
            checked = await self._check_movable(conn, queue_id, user)
            if isinstance(checked, OpStatus):
                return checked
            (my_id, _), _ = checked
            await conn.execute(
                "UPDATE queue_members SET position = ? WHERE id = ?", (await self._next_position(conn, queue_id), my_id)
            )
            return OpStatus.OK
