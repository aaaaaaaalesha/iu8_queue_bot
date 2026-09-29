"""Commands available to everyone and the buttons of queue messages."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message

from queue_bot.db.repository import Repository
from queue_bot.keyboards import client as kb
from queue_bot.models import Member, OpStatus
from queue_bot.services.rendering import parse_legacy_members
from queue_bot.services.updater import QueueMessageUpdater

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "/start - Начало работы с ботом \n"
    "/help - Вывести доступные команды\n"
    "/plan_queue - Запланировать очередь\n"
    "/queues_list - Вывести список запланированных очередей\n"
    "/delete_queue - Удалить запланированную очередь"
)

_COMMON_ANSWERS = {
    OpStatus.ALREADY_IN: "❕ Вы уже в очереди.",
    OpStatus.NO_QUEUERS: "❕ В очереди ещё нет участников.",
    OpStatus.ONE_QUEUER: "❕ В очереди только один участник.",
    OpStatus.NOT_QUEUER: "❕ Вы ещё не участник очереди.",
    OpStatus.NO_AFTER: "❕ Вы крайний в очереди.",
    OpStatus.QUEUE_NOT_FOUND: "❕ Эта очередь больше не активна.",
}

QueueOperation = Callable[[int, Member], Awaitable[OpStatus]]


async def start_handler(message: Message, bot: Bot) -> None:
    user = message.from_user
    if user is None:
        return
    await bot.send_message(
        user.id,
        f"Привет, {user.first_name} (@{user.username})!\n"
        "Я IU8-QueueBot - бот для создания очередей.\n"
        "Давайте начнём: можете использовать команды (/help) "
        "или кнопки клавиатуры для работы со мной. В случае возникновения проблем, пишите "
        "@aaaaaaaalesha",
        reply_markup=kb.main_keyboard(),
    )


async def help_handler(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    await bot.send_message(message.from_user.id, HELP_TEXT, reply_markup=kb.main_keyboard())


async def _safe_answer(callback: CallbackQuery, text: str | None = None) -> None:
    try:
        await callback.answer(text)
    except TelegramBadRequest:
        # The query is too old to be answered; the action itself is already done.
        pass


async def _handle_queue_button(
    callback: CallbackQuery,
    repo: Repository,
    updater: QueueMessageUpdater,
    operation: QueueOperation,
    answers: dict[OpStatus, str],
) -> None:
    message = callback.message
    if message is None:
        await _safe_answer(callback, _COMMON_ANSWERS[OpStatus.QUEUE_NOT_FOUND])
        return

    queue = await repo.find_queue_by_message(message.chat.id, message.message_id)
    if queue is None:
        await _safe_answer(callback, _COMMON_ANSWERS[OpStatus.QUEUE_NOT_FOUND])
        return

    if queue.legacy_pending and isinstance(message, Message) and message.text:
        await repo.import_legacy_members(queue.id, parse_legacy_members(message.text))

    user = callback.from_user
    status = await operation(queue.id, Member(user.id, user.first_name, user.username))
    if status is OpStatus.OK:
        updater.request(queue.id)
        await _safe_answer(callback)
    else:
        await _safe_answer(callback, answers.get(status) or _COMMON_ANSWERS.get(status, "❕ Что-то пошло не так."))


async def sign_in_queue_handler(callback: CallbackQuery, repo: Repository, updater: QueueMessageUpdater) -> None:
    await _handle_queue_button(callback, repo, updater, repo.join, {})


async def sign_out_queue_handler(callback: CallbackQuery, repo: Repository, updater: QueueMessageUpdater) -> None:
    answers = {OpStatus.NOT_QUEUER: f"❕ @{callback.from_user.username} ещё не участник очереди."}
    await _handle_queue_button(callback, repo, updater, repo.leave, answers)


async def skip_ahead_handler(callback: CallbackQuery, repo: Repository, updater: QueueMessageUpdater) -> None:
    await _handle_queue_button(callback, repo, updater, repo.skip_ahead, {})


async def push_tail_handler(callback: CallbackQuery, repo: Repository, updater: QueueMessageUpdater) -> None:
    await _handle_queue_button(callback, repo, updater, repo.push_tail, {})


def build_router() -> Router:
    router = Router(name="client")
    router.message.register(start_handler, Command("start"), StateFilter(None))
    router.message.register(help_handler, Command("help"), StateFilter(None))
    router.callback_query.register(sign_in_queue_handler, F.data == kb.SIGN_IN)
    router.callback_query.register(sign_out_queue_handler, F.data == kb.SIGN_OUT)
    router.callback_query.register(skip_ahead_handler, F.data == kb.SKIP_AHEAD)
    router.callback_query.register(push_tail_handler, F.data == kb.IN_TAIL)
    return router
