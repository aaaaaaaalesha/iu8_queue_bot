"""Planning, listing and deleting queues (private chat with the bot)."""

from __future__ import annotations

import logging
from datetime import date, datetime

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from queue_bot.config import Settings
from queue_bot.db.repository import Repository
from queue_bot.keyboards import admin as kb
from queue_bot.keyboards.calendar import CalendarAction, CalendarCallback, calendar_keyboard, navigate
from queue_bot.keyboards.client import DELETE_QUEUE_TEXT, MAIN_MENU_TEXTS, PLAN_QUEUE_TEXT, PLANNED_QUEUES_TEXT
from queue_bot.models import Queue
from queue_bot.services.planning import EarlierError, parse_start
from queue_bot.services.rendering import MAX_MESSAGE_LENGTH, format_start
from queue_bot.services.scheduler import QueueScheduler
from queue_bot.services.updater import QueueMessageUpdater

logger = logging.getLogger(__name__)


class FSMPlanning(StatesGroup):
    choose_chat = State()
    queue_name = State()
    start_date = State()
    start_datetime = State()


class FSMDeletion(StatesGroup):
    queue_choice = State()


async def _delete_messages(bot: Bot, chat_id: int, message_ids: list[int]) -> None:
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except TelegramAPIError:
            pass


async def cancel_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if isinstance(callback.message, Message):
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer("🚫 Действие отменено")


# ------------------------------------------------------------------- list of queues


def _queues_list_texts(queues: list[Queue], settings: Settings) -> list[str]:
    """The list split into messages that fit into the Telegram limit."""
    texts = []
    current = "⤵️ Вот запланированные вами очереди:\n"
    for queue in queues:
        line = f"📌«{queue.name}» в чате «{queue.chat_title}» {format_start(queue.start_at, settings.timezone)}\n"
        if len(current) + len(line) > MAX_MESSAGE_LENGTH:
            texts.append(current)
            current = ""
        current += line
    texts.append(current)
    return texts


async def _send_queues_list(
    message: Message, bot: Bot, repo: Repository, settings: Settings
) -> tuple[list[Queue], list[int]]:
    """Send the admin's queues. Returns the queues and the ids of the sent messages."""
    assert message.from_user is not None
    user_id = message.from_user.id
    queues = await repo.list_admin_queues(user_id)
    if not queues:
        await bot.send_message(
            user_id,
            "🙊 У вас пока нет запланированных очередей.\nЗапланируем одну?",
            reply_markup=kb.plan_keyboard(),
        )
        return queues, []

    sent = [await bot.send_message(user_id, text) for text in _queues_list_texts(queues, settings)]
    return queues, [m.message_id for m in sent]


async def queues_list_handler(message: Message, bot: Bot, repo: Repository, settings: Settings) -> None:
    if message.from_user is not None:
        await _send_queues_list(message, bot, repo, settings)


# ------------------------------------------------------------------- planning


async def _start_planning(user_id: int, username: str | None, bot: Bot, repo: Repository, state: FSMContext) -> None:
    chats = await repo.list_admin_chats(user_id)
    if not chats:
        await bot.send_message(
            user_id,
            "🙊 Вы пока не добавили меня ни в один групповой чат.\nЯ могу организовывать очереди только там 💁‍♂️",
        )
        return

    await repo.upsert_admin(user_id, username)
    await state.set_state(FSMPlanning.choose_chat)
    await bot.send_message(
        user_id, "⤵️Для начала выберите чат, в который вы добавили бота:", reply_markup=kb.chats_keyboard(chats)
    )


async def queue_plan_handler(message: Message, bot: Bot, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await message.answer("📑 Переходим к планированию очереди...")
    await _start_planning(message.from_user.id, message.from_user.username, bot, repo, state)


async def queue_plan_inline_handler(callback: CallbackQuery, bot: Bot, repo: Repository, state: FSMContext) -> None:
    await callback.answer("📑 Переходим к планированию очереди...")
    await _start_planning(callback.from_user.id, callback.from_user.username, bot, repo, state)


async def queue_set_chat_handler(
    callback: CallbackQuery, callback_data: kb.ChooseChatCallback, bot: Bot, repo: Repository, state: FSMContext
) -> None:
    chat = await repo.get_admin_chat(callback_data.chat_id, callback.from_user.id)
    if chat is None:
        await cancel_handler(callback, state)
        return

    await state.update_data(chat_id=chat.chat_id, chat_title=chat.title)
    await state.set_state(FSMPlanning.queue_name)
    await callback.answer()
    await bot.send_message(callback.from_user.id, "📝 Задайте название очереди", reply_markup=kb.cancel_keyboard())


async def set_queue_name_handler(message: Message, bot: Bot, settings: Settings, state: FSMContext) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if not name or name in MAIN_MENU_TEXTS:
        await bot.send_message(
            message.from_user.id,
            "❌ Кажется, вы ничего не написали! Задайте название очереди",
            reply_markup=kb.cancel_keyboard(),
        )
        return

    await state.update_data(queue_name=name)
    await state.set_state(FSMPlanning.start_date)
    today = datetime.now(settings.timezone).date()
    await bot.send_message(
        message.from_user.id,
        "📅 Теперь задайте дату запуска очереди через календарь:",
        reply_markup=calendar_keyboard(today.year, today.month, today),
    )


async def set_date_handler(
    callback: CallbackQuery, callback_data: CalendarCallback, bot: Bot, settings: Settings, state: FSMContext
) -> None:
    today = datetime.now(settings.timezone).date()
    message = callback.message if isinstance(callback.message, Message) else None

    if callback_data.act == CalendarAction.DAY:
        try:
            chosen = date(callback_data.year, callback_data.month, callback_data.day)
        except ValueError:
            chosen = None
        if chosen is None or chosen < today:
            await callback.answer("Мимо 🤷‍♂️")
            return
        await state.update_data(selected_date=chosen.isoformat())
        await state.set_state(FSMPlanning.start_datetime)
        await callback.answer()
        if message is not None:
            try:
                await message.delete_reply_markup()
            except TelegramBadRequest:
                pass
        await bot.send_message(
            callback.from_user.id,
            '🕓 Теперь задайте время запуска очереди в формате чч:мм (ex. "15:40")',
            reply_markup=kb.cancel_keyboard(),
        )
        return

    shown = navigate(callback_data)
    if shown is None:
        await callback.answer("Мимо 🤷‍♂️", cache_time=60)
        return
    await callback.answer()
    if message is not None:
        try:
            await message.edit_reply_markup(reply_markup=calendar_keyboard(*shown, today))
        except TelegramBadRequest:
            pass


async def set_datetime_handler(
    message: Message,
    bot: Bot,
    repo: Repository,
    scheduler: QueueScheduler,
    settings: Settings,
    state: FSMContext,
) -> None:
    assert message.from_user is not None
    admin_id = message.from_user.id
    data = await state.get_data()
    try:
        start = parse_start(date.fromisoformat(data["selected_date"]), message.text, settings.timezone)
    except EarlierError as e:
        await bot.send_message(admin_id, str(e), reply_markup=kb.cancel_keyboard())
        return
    except ValueError:
        await bot.send_message(
            admin_id,
            '❌ Время задано неверно! Проверьте правильность формата:\n- "чч:мм" (ex. "15:40")',
            reply_markup=kb.cancel_keyboard(),
        )
        return

    await state.clear()
    queue = await repo.create_queue(admin_id, data["chat_id"], data["queue_name"], int(start.timestamp()))
    if queue is None:
        await bot.send_message(admin_id, "🙊 Кажется, меня удалили из выбранного чата. Очередь не запланирована.")
        return
    scheduler.schedule(queue)

    start_text = format_start(queue.start_at, settings.timezone)
    await bot.send_message(
        admin_id, f"✅Очередь «{queue.name}» запланирована в чате «{queue.chat_title}»!\nНачало очереди: {start_text}"
    )
    try:
        await bot.send_message(queue.chat_id, f"✅Очередь «{queue.name}» запланирована!\nНачало очереди: {start_text}")
    except TelegramAPIError as e:
        logger.warning("Can't notify chat %s about queue %s: %s", queue.chat_id, queue.id, e)


# ------------------------------------------------------------------- deletion


async def choose_queue_to_delete_handler(
    message: Message, bot: Bot, repo: Repository, settings: Settings, state: FSMContext
) -> None:
    if message.from_user is None:
        return
    queues, list_message_ids = await _send_queues_list(message, bot, repo, settings)
    if not queues:
        return

    choice = await bot.send_message(
        message.from_user.id,
        "🗑 Выберите очередь, которую хотите удалить:",
        reply_markup=kb.delete_queues_keyboard(queues),
    )
    await state.set_state(FSMDeletion.queue_choice)
    await state.update_data(message_ids=[*list_message_ids, choice.message_id])


async def delete_queue_handler(
    callback: CallbackQuery,
    callback_data: kb.DeleteQueueCallback,
    bot: Bot,
    repo: Repository,
    scheduler: QueueScheduler,
    updater: QueueMessageUpdater,
    settings: Settings,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    await state.clear()

    queue = await repo.delete_queue(callback_data.queue_id, callback.from_user.id)
    if queue is None:
        await callback.answer("❕ Очередь уже удалена.")
    else:
        scheduler.cancel(queue.id)
        updater.forget(queue.id)
        try:
            if queue.message_id is not None:
                await bot.delete_message(queue.chat_id, queue.message_id)
            else:
                await bot.send_message(
                    queue.chat_id,
                    f"🗑 Кажется, запланированную на {format_start(queue.start_at, settings.timezone)} "
                    f"очередь «{queue.name}» удалили :(",
                )
        except TelegramAPIError as e:
            logger.warning("Can't clean up after queue %s in chat %s: %s", queue.id, queue.chat_id, e)
        await callback.answer("💥 Очередь удалена")

    await _delete_messages(bot, callback.from_user.id, data.get("message_ids", []))


def build_router() -> Router:
    router = Router(name="admin")
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)
    router.callback_query.register(cancel_handler, F.data == kb.CANCEL)
    router.message.register(queues_list_handler, F.text == PLANNED_QUEUES_TEXT, StateFilter(None))
    router.message.register(queues_list_handler, Command("queues_list"), StateFilter(None))
    router.message.register(queue_plan_handler, F.text == PLAN_QUEUE_TEXT, StateFilter(None))
    router.message.register(queue_plan_handler, Command("plan_queue"), StateFilter(None))
    router.callback_query.register(queue_plan_inline_handler, F.data == kb.PLAN_QUEUE, StateFilter(None))
    router.callback_query.register(queue_set_chat_handler, kb.ChooseChatCallback.filter(), FSMPlanning.choose_chat)
    router.message.register(set_queue_name_handler, FSMPlanning.queue_name)
    router.callback_query.register(set_date_handler, CalendarCallback.filter(), FSMPlanning.start_date)
    router.message.register(set_datetime_handler, FSMPlanning.start_datetime, F.text)
    router.message.register(choose_queue_to_delete_handler, F.text == DELETE_QUEUE_TEXT, StateFilter(None))
    router.message.register(choose_queue_to_delete_handler, Command("delete_queue"), StateFilter(None))
    router.callback_query.register(delete_queue_handler, kb.DeleteQueueCallback.filter(), FSMDeletion.queue_choice)
    return router
