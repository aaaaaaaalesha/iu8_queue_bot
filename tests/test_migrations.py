from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from queue_bot.db.database import Database
from queue_bot.db.repository import Repository

LEGACY_SCHEMA = """
CREATE TABLE admin (admin_id PRIMARY KEY, username VARCHAR(255));
CREATE TABLE chat (id INTEGER PRIMARY KEY, assignee_id INTEGER, chat_id INTEGER, chat_title VARCHAR(255));
CREATE TABLE queues_list (id INTEGER PRIMARY KEY, assignee_id INTEGER, queue_name VARCHAR(255),
                          start TIMESTAMP, chat_id INTEGER, chat_title VARCHAR(255));
CREATE TABLE queue (id INTEGER, msg_id INTEGER);
"""


async def test_legacy_database_is_imported(tmp_path: Path) -> None:
    path = tmp_path / "queue_bot.db"
    start = datetime(2030, 5, 1, 15, 40, tzinfo=ZoneInfo("Europe/Moscow"))
    with sqlite3.connect(path) as conn:
        conn.executescript(LEGACY_SCHEMA)
        conn.execute("INSERT INTO admin VALUES (1, 'admin')")
        conn.execute("INSERT INTO chat (assignee_id, chat_id, chat_title) VALUES (1, -100, 'Old title')")
        conn.execute("INSERT INTO chat (assignee_id, chat_id, chat_title) VALUES (1, -100, 'New title')")
        conn.execute("INSERT INTO queues_list VALUES (1, 1, 'Planned', ?, -100, 'New title')", (str(start),))
        # pytz produced the LMT offset for Moscow; the wall-clock time is what matters.
        conn.execute(
            "INSERT INTO queues_list VALUES (2, 1, 'Active', ?, -100, 'New title')", ("2030-05-01 15:40:00+02:30",)
        )
        conn.execute("INSERT INTO queue VALUES (2, 555)")
    conn.close()

    db = Database(str(path))
    await db.connect()
    try:
        repo = Repository(db)
        chats = await repo.list_admin_chats(1)
        assert [(c.chat_id, c.title) for c in chats] == [(-100, "New title")]

        queues = {q.name: q for q in await repo.list_admin_queues(1)}
        assert queues["Planned"].start_at == int(start.timestamp())
        assert queues["Planned"].message_id is None
        assert not queues["Planned"].legacy_pending
        assert queues["Active"].start_at == int(start.timestamp())
        assert queues["Active"].message_id == 555
        assert queues["Active"].legacy_pending

        async with db.read() as conn:
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE name = 'queues_list'")
            assert await cursor.fetchone() is None
    finally:
        await db.close()

    # Reopening doesn't apply migrations again.
    db = Database(str(path))
    await db.connect()
    await db.close()
