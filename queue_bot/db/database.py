"""Thin async wrapper over a single SQLite connection.

All access goes through one connection guarded by an :class:`asyncio.Lock`.
Every write is executed inside ``BEGIN IMMEDIATE`` so each queue operation is
atomic: concurrent button presses are applied one after another to the
current state of the database and can never overwrite each other.
SQLite statements used by the bot take microseconds, so the lock is never a
bottleneck for a Telegram bot.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite

from queue_bot.db.migrations import apply_migrations

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        # isolation_level=None: transactions are controlled explicitly.
        conn = await aiosqlite.connect(self._path, isolation_level=None)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA busy_timeout = 5000")
        if self._path != ":memory:":
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")
        self._conn = conn

        async with self.transaction() as tx:
            await apply_migrations(tx)
        logger.info("Database %s is ready", self._path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def _connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Serialized read-write transaction."""
        async with self._lock:
            conn = self._connection
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                await conn.rollback()
                raise
            else:
                await conn.commit()

    @asynccontextmanager
    async def read(self) -> AsyncIterator[aiosqlite.Connection]:
        """Consistent read: never observes another operation half-applied."""
        async with self._lock:
            yield self._connection
