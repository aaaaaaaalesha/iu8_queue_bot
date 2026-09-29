"""Launching planned queues at their start time.

Planned queues live in the database, so they survive restarts: on startup
every planned queue is scheduled again, and the ones whose time has passed
while the bot was offline are launched immediately.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramRetryAfter, TelegramServerError

from queue_bot.keyboards.client import queue_keyboard
from queue_bot.services.rendering import render_queue

if TYPE_CHECKING:
    from aiogram import Bot

    from queue_bot.db.repository import Repository
    from queue_bot.models import Queue
    from queue_bot.services.updater import QueueMessageUpdater

logger = logging.getLogger(__name__)

# asyncio can't sleep for arbitrarily long periods reliably; long waits are split.
_MAX_SLEEP = 3600.0
_SEND_ATTEMPTS = 5


class QueueScheduler:
    def __init__(self, bot: Bot, repo: Repository, updater: QueueMessageUpdater) -> None:
        self._bot = bot
        self._repo = repo
        self._updater = updater
        self._tasks: dict[int, asyncio.Task[None]] = {}

    async def restore(self) -> None:
        planned = await self._repo.list_planned_queues()
        for queue in planned:
            self.schedule(queue)
        logger.info("Restored %d planned queue(s)", len(planned))

    def schedule(self, queue: Queue) -> None:
        self.cancel(queue.id)
        self._tasks[queue.id] = asyncio.create_task(self._wait_and_launch(queue), name=f"queue-launch-{queue.id}")

    def cancel(self, queue_id: int) -> None:
        task = self._tasks.pop(queue_id, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _wait_and_launch(self, queue: Queue) -> None:
        try:
            while (delay := queue.start_at - time.time()) > 0:
                await asyncio.sleep(min(delay, _MAX_SLEEP))
            # From now on the launch is not cancellable: a queue deleted during
            # the launch is detected by ``mark_launched`` and cleaned up.
            if self._tasks.get(queue.id) is asyncio.current_task():
                del self._tasks[queue.id]
            await self.launch(queue.id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to launch queue %s", queue.id)
        finally:
            if self._tasks.get(queue.id) is asyncio.current_task():
                del self._tasks[queue.id]

    async def launch(self, queue_id: int) -> None:
        queue = await self._repo.get_queue(queue_id)
        if queue is None or queue.is_launched:
            # Deleted or already launched.
            return

        text = render_queue(queue.name, [])
        message = None
        for attempt in range(1, _SEND_ATTEMPTS + 1):
            try:
                message = await self._bot.send_message(queue.chat_id, text, reply_markup=queue_keyboard())
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except (TelegramNetworkError, TelegramServerError) as e:
                logger.warning("Can't launch queue %s (attempt %d): %s", queue_id, attempt, e)
                await asyncio.sleep(attempt * 5)
            except TelegramAPIError as e:
                # The bot was removed from the chat, the chat doesn't exist, etc.
                logger.warning("Can't launch queue %s: %s", queue_id, e)
                return
        if message is None:
            return

        if not await self._repo.mark_launched(queue_id, message.message_id):
            # The queue was deleted while the message was being sent.
            await self._safe_delete(queue.chat_id, message.message_id)
            return
        self._updater.remember(queue_id, text)
        logger.info("Queue %s launched in chat %s", queue_id, queue.chat_id)

        try:
            await self._bot.pin_chat_message(queue.chat_id, message.message_id, disable_notification=False)
        except TelegramAPIError:
            # The bot is not allowed to pin messages in this chat.
            pass

    async def _safe_delete(self, chat_id: int, message_id: int) -> None:
        try:
            await self._bot.delete_message(chat_id, message_id)
        except TelegramAPIError:
            pass
