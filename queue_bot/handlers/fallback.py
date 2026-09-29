"""Handlers for updates nobody else handled."""

from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


async def stale_button_handler(callback: CallbackQuery) -> None:
    """A button of an outdated keyboard: stop the loading indicator."""
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass


def build_router() -> Router:
    router = Router(name="fallback")
    router.callback_query.register(stale_button_handler)
    return router
