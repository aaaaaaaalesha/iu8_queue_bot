"""Coalescing updater of queue messages.

Pressing a button changes the database immediately, but the queue message is
not edited once per press: for every queue a single background task edits the
message with the *latest* state, then waits ``interval`` seconds. Presses that
arrive meanwhile are merged into the next edit. This keeps the number of
Telegram API calls per queue bounded (no flood-control bans with dozens of
simultaneous presses) and the message always ends up showing the actual queue.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramNetworkError, TelegramRetryAfter

from queue_bot.keyboards.client import queue_keyboard
from queue_bot.services.rendering import render_queue

if TYPE_CHECKING:
    from aiogram import Bot

    from queue_bot.db.repository import Repository

logger = logging.getLogger(__name__)

_NETWORK_RETRY_DELAY = 2.0


class QueueMessageUpdater:
    def __init__(self, bot: Bot, repo: Repository, interval: float = 1.0) -> None:
        self._bot = bot
        self._repo = repo
        self._interval = interval
        self._pending: set[int] = set()
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._last_text: dict[int, str] = {}

    def request(self, queue_id: int) -> None:
        """Ask to bring the message of the queue up to date (non-blocking)."""
        self._pending.add(queue_id)
        if queue_id not in self._tasks:
            task = asyncio.create_task(self._run(queue_id), name=f"queue-updater-{queue_id}")
            self._tasks[queue_id] = task

    def remember(self, queue_id: int, text: str) -> None:
        """Remember the text the message was sent with to skip no-op edits."""
        self._last_text[queue_id] = text

    def forget(self, queue_id: int) -> None:
        self._pending.discard(queue_id)
        self._last_text.pop(queue_id, None)
        task = self._tasks.pop(queue_id, None)
        if task is not None:
            task.cancel()

    async def wait_idle(self) -> None:
        """Wait until all requested edits are done (used in tests and on shutdown)."""
        while self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run(self, queue_id: int) -> None:
        try:
            # No awaits between the loop check and the removal of the task in
            # ``finally``, so a request made at any moment is never lost.
            while queue_id in self._pending:
                self._pending.discard(queue_id)
                if not await self._edit(queue_id):
                    return
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to update message of queue %s", queue_id)
        finally:
            if self._tasks.get(queue_id) is asyncio.current_task():
                del self._tasks[queue_id]

    async def _edit(self, queue_id: int) -> bool:
        """Edit the message once. Returns False if the queue can't be updated anymore."""
        data = await self._repo.get_queue_with_members(queue_id)
        if data is None or data[0].message_id is None:
            self._last_text.pop(queue_id, None)
            return False
        queue, members = data
        text = render_queue(queue.name, members)
        if self._last_text.get(queue_id) == text:
            return True

        try:
            await self._bot.edit_message_text(
                text=text, chat_id=queue.chat_id, message_id=queue.message_id, reply_markup=queue_keyboard()
            )
        except TelegramRetryAfter as e:
            logger.warning("Flood control for queue %s: retry after %s s", queue_id, e.retry_after)
            await asyncio.sleep(e.retry_after)
            # The state could change while waiting: edit again with the latest one.
            self._pending.add(queue_id)
            return True
        except TelegramNetworkError as e:
            logger.warning("Network error while editing queue %s: %s", queue_id, e)
            await asyncio.sleep(_NETWORK_RETRY_DELAY)
            self._pending.add(queue_id)
            return True
        except TelegramBadRequest as e:
            if "message is not modified" not in e.message:
                logger.warning("Can't edit message of queue %s: %s", queue_id, e.message)
                return False
        except TelegramAPIError as e:
            logger.warning("Can't edit message of queue %s: %s", queue_id, e)
            return False

        self._last_text[queue_id] = text
        return True
