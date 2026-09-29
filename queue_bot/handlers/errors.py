from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


async def flood_handler(event: ErrorEvent) -> None:
    assert isinstance(event.exception, TelegramRetryAfter)
    logger.warning("Flood control: %s", event.exception)
    callback = event.update.callback_query
    if callback is not None:
        try:
            await callback.answer(f"Не так быстро! Подождите {event.exception.retry_after} секунд")
        except TelegramAPIError:
            pass


async def error_handler(event: ErrorEvent) -> None:
    logger.error("Error while handling update %s", event.update.update_id, exc_info=event.exception)


def build_router() -> Router:
    router = Router(name="errors")
    router.errors.register(flood_handler, ExceptionTypeFilter(TelegramRetryAfter))
    router.errors.register(error_handler)
    return router
