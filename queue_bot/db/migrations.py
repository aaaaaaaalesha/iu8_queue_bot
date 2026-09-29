"""Schema migrations tracked with ``PRAGMA user_version``."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Awaitable, Callable
from datetime import datetime
from zoneinfo import ZoneInfo

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS admins
(
    user_id  INTEGER PRIMARY KEY,
    username TEXT
);

CREATE TABLE IF NOT EXISTS chats
(
    chat_id  INTEGER PRIMARY KEY,
    title    TEXT    NOT NULL DEFAULT '',
    admin_id INTEGER NOT NULL REFERENCES admins (user_id)
);
CREATE INDEX IF NOT EXISTS idx_chats_admin ON chats (admin_id);

CREATE TABLE IF NOT EXISTS queues
(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id       INTEGER NOT NULL REFERENCES admins (user_id),
    chat_id        INTEGER NOT NULL REFERENCES chats (chat_id) ON DELETE CASCADE ON UPDATE CASCADE,
    name           TEXT    NOT NULL,
    -- Unix timestamp (UTC) of the planned launch.
    start_at       INTEGER NOT NULL,
    -- Id of the queue message in the chat, NULL while the queue is only planned.
    message_id     INTEGER,
    -- 1 for queues launched by the pre-v1 bot: their members live only in the
    -- message text and are imported on the first button press.
    legacy_pending INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_queues_message ON queues (chat_id, message_id)
    WHERE message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_queues_admin ON queues (admin_id, start_at);
CREATE INDEX IF NOT EXISTS idx_queues_planned ON queues (start_at) WHERE message_id IS NULL;

CREATE TABLE IF NOT EXISTS queue_members
(
    id         INTEGER PRIMARY KEY,
    queue_id   INTEGER NOT NULL REFERENCES queues (id) ON DELETE CASCADE,
    -- NULL only for members imported from a pre-v1 queue message.
    user_id    INTEGER,
    first_name TEXT    NOT NULL,
    username   TEXT,
    -- Ordering key, not a displayed number: gaps are fine.
    position   INTEGER NOT NULL,
    UNIQUE (queue_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_members_order ON queue_members (queue_id, position);
"""


async def _table_exists(conn: aiosqlite.Connection, name: str) -> bool:
    cursor = await conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,))
    return await cursor.fetchone() is not None


# The pre-v1 bot worked only in Moscow time.
_LEGACY_TZ = ZoneInfo("Europe/Moscow")


def _parse_legacy_datetime(value: object) -> int | None:
    """Convert a legacy start time to a Unix timestamp.

    The old bot attached pytz time zones incorrectly (LMT, +02:30), so the
    stored offset is ignored and the wall-clock time is read as Moscow time,
    which is what the admin actually entered.
    """
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return int(dt.replace(tzinfo=_LEGACY_TZ).timestamp())


async def _import_legacy_data(conn: aiosqlite.Connection) -> None:
    """Move data from the tables of the pre-v1 bot and drop them."""
    if not await _table_exists(conn, "queues_list"):
        return
    logger.info("Importing data from the legacy schema")

    await conn.execute(
        "INSERT OR IGNORE INTO admins (user_id, username) "
        "SELECT admin_id, username FROM admin WHERE admin_id IS NOT NULL"
    )
    await conn.execute(
        "INSERT OR IGNORE INTO admins (user_id) SELECT DISTINCT assignee_id FROM chat WHERE assignee_id IS NOT NULL"
    )
    # The legacy table allowed duplicate chats: the latest row wins.
    await conn.execute(
        "INSERT OR REPLACE INTO chats (chat_id, title, admin_id) "
        "SELECT chat_id, COALESCE(chat_title, ''), assignee_id FROM chat "
        "WHERE chat_id IS NOT NULL AND assignee_id IS NOT NULL ORDER BY id"
    )

    cursor = await conn.execute(
        "SELECT ql.id, ql.assignee_id, ql.queue_name, ql.start, ql.chat_id, ql.chat_title, "
        "       (SELECT q.msg_id FROM queue q WHERE q.id = ql.id) AS msg_id "
        "FROM queues_list ql"
    )
    for row in await cursor.fetchall():
        start_at = _parse_legacy_datetime(row["start"])
        if start_at is None or row["assignee_id"] is None or row["chat_id"] is None:
            continue
        await conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (row["assignee_id"],))
        await conn.execute(
            "INSERT OR IGNORE INTO chats (chat_id, title, admin_id) VALUES (?, ?, ?)",
            (row["chat_id"], row["chat_title"] or "", row["assignee_id"]),
        )
        await conn.execute(
            "INSERT OR IGNORE INTO queues (admin_id, chat_id, name, start_at, message_id, legacy_pending) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["assignee_id"],
                row["chat_id"],
                row["queue_name"] or "",
                start_at,
                row["msg_id"],
                int(row["msg_id"] is not None),
            ),
        )

    for table in ("queue", "queues_list", "chat", "admin"):
        await conn.execute(f"DROP TABLE IF EXISTS {table}")


async def _migrate_v1(conn: aiosqlite.Connection) -> None:
    for statement in _split_script(SCHEMA_V1):
        await conn.execute(statement)
    await _import_legacy_data(conn)


def _split_script(script: str) -> list[str]:
    # executescript() would commit the surrounding transaction, so statements
    # are executed one by one.
    statements, current = [], ""
    for line in script.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            statements.append(current.strip())
            current = ""
    if current.strip():
        raise ValueError(f"Incomplete SQL statement: {current!r}")
    return statements


MIGRATIONS: list[Callable[[aiosqlite.Connection], Awaitable[None]]] = [_migrate_v1]


async def apply_migrations(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    version = int(row[0]) if row else 0

    for target, migration in enumerate(MIGRATIONS[version:], start=version + 1):
        logger.info("Applying database migration v%d", target)
        await migration(conn)
        await conn.execute(f"PRAGMA user_version = {target}")
