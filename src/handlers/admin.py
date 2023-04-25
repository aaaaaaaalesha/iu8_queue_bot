import datetime as dt

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup

from src.db.sqlite_db import (
    sql_get_queue_list,
    sql_add_queue,
    sql_add_admin,
    sql_delete_queue,
    sql_get_managed_chats,
    sql_get_chat_title,
)
from src.keyboards.client_kb import (
    PLAN_QUEUE_TEXT,
    DELETE_QUEUE_TEXT,
    PLANNED_QUEUES_TEXT,
)
from src.services.admin_service import (
    EarlierException,
    parse_to_datetime,
    wait_for_queue_launch,
)
from src.create_bot import dp, bot
from src.keyboards import admin_kb, calendar_kb


class FSMPlanning(StatesGroup):
    """Конечный автомат для планирования очередей."""
    choose_chat = State()
    queue_name = State()
    start_date = State()
    start_datetime = State()


class FSMDeletion(StatesGroup):
    """Конечный автомат удаления очереди."""
    queue_choice = State()


async def cancel_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Функция-handler отмены действия.
    Прекращает последовательность состояний в конечном автомате, попутно удаляя сообщение.
    """
    await callback.message.delete()
    await callback.answer('🚫 Действие отменено')
    await state.finish()


async def queues_list_handler(msg: types.Message) -> tuple:
    """
    Функция-handler выдачи списка запланированных очередей.
    """
    found_queues = sql_get_queue_list(msg.from_user.id)
    if not found_queues:
        await bot.send_message(
            msg.from_user.id,
            "🙊 У вас пока нет запланированных очередей.\nЗапланируем одну?",
            reply_markup=admin_kb.inl_plan_kb,
        )

        return found_queues, None

    out_str = '\n'.join([
        f"📌«{queue_name}» в чате «{chat_title}» "
        f"{dt.datetime.strptime(time, '%Y-%m-%d %H:%M:%S%z').strftime('%d.%m.%Y в %H:%M')}"
        for _, queue_name, time, _, chat_title in found_queues
    ])

    planned_msg = await bot.send_message(
        msg.from_user.id,
        f"⤵️ Вот запланированные вами очереди:\n{out_str}",
    )

    return found_queues, planned_msg


""" Planning queue zone"""


async def queue_plan_handler(msg: types.Message) -> None:
    await __start_planning(msg)


async def queue_plan_inline_handler(callback: types.CallbackQuery) -> None:
    await __start_planning(callback)


async def __start_planning(action: types.Message | types.CallbackQuery) -> None:
    """
    Функция старта планирования очередей.
    Если бот добавлен вами в групповые чаты, он предложит вам
    выбрать, в каком именно вы хотите запланировать очередь.
    """
    await action.answer('📑 Переходим к планированию очереди...')
    managed_chats = sql_get_managed_chats(action.from_user.id)

    if not managed_chats:
        await bot.send_message(
            action.from_user.id,
            "🙊 Вы пока не добавили меня ни в один групповой чат.\n"
            "Я могу организовывать очереди только там 💁‍♂️",
        )
        return

    await FSMPlanning.choose_chat.set()
    await sql_add_admin(action.from_user.id, action.from_user.username)

    inl_kb_chat_choices = InlineKeyboardMarkup()
    for chat_id, chat_title in managed_chats:
        inl_kb_chat_choices.add(
            types.InlineKeyboardButton(
                text=chat_title,
                callback_data=f"choose_chat_{chat_id}",
            )
        )
    inl_kb_chat_choices.add(admin_kb.cancel_button)

    await bot.send_message(
        action.from_user.id,
        "⤵️Для начала выберите чат, в который вы добавили бота:",
        reply_markup=inl_kb_chat_choices,
    )


async def queue_set_chat_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    """
    Функция-handler сохранения выбранного чата.
    Переводит в состояние выбора названия очереди если всё хорошо,
    иначе отменяет действие.
    """
    async with state.proxy() as data:
        chat_id = int(callback.data[len("choose_chat_"):])
        chat_title = sql_get_chat_title(chat_id)
        if not chat_title:
            await callback.answer(
                "Кажется, бота уже нет в данном чате, попробуйте снова.",
            )
            await cancel_handler(callback, state)
            return

        data['chat_id'] = chat_id
        data['chat_title'] = chat_title[0]

    await FSMPlanning.next()
    await bot.send_message(
        callback.from_user.id,
        "📝 Задайте название очереди",
        reply_markup=admin_kb.inl_cancel_kb,
    )


async def set_queue_name_handler(msg: types.Message, state: FSMContext) -> None:
    """
    Функция-handler сохранения имени очереди. Переводит в состояние выбора даты старта очереди,
    иначе выводит ошибку и просит повторить ввод.
    """
    if not msg.text or msg.text in (PLAN_QUEUE_TEXT, DELETE_QUEUE_TEXT, PLANNED_QUEUES_TEXT):
        await bot.send_message(
            msg.from_user.id,
            '❌ Кажется, вы ничего не написали! Задайте название очереди',
            reply_markup=admin_kb.inl_cancel_kb,
        )
        return

    async with state.proxy() as data:
        data['queue_name'] = msg.text

    await FSMPlanning.next()
    await bot.send_message(
        msg.from_user.id,
        '📅 Теперь задайте дату запуска очереди через календарь:',
        reply_markup=await calendar_kb.Calendar().start_calendar(),
    )


async def set_date_handler(
        callback: types.CallbackQuery,
        callback_data: dict,
        state: FSMContext,
) -> None:
    """
    Функция-handler сохранения выбранной в календаре даты.
    Переводит в состояние выбора времени старта очереди.
    """
    selected, date = await calendar_kb.Calendar().process_selection(
        query=callback,
        data=callback_data,
    )
    if selected:
        async with state.proxy() as data:
            data["selected_date"] = date

        await FSMPlanning.next()
        await bot.send_message(
            callback.from_user.id,
            '🕓 Теперь задайте время запуска очереди в формате чч:мм (ex. "15:40")',
            reply_markup=admin_kb.inl_cancel_kb,
        )


async def set_datetime_handler(msg: types.Message, state: FSMContext) -> None:
    """
    Функция-handler сохранения времени и других собранных данных в БД.
    Выдаёт информационное сообщение о запуске очереди и начинает ожидание.
    """
    async with state.proxy() as data:
        try:
            start_datetime = parse_to_datetime(data["selected_date"], msg.text)
        except ValueError:
            await bot.send_message(
                msg.from_user.id,
                '❌ Время задано неверно! Проверьте правильность формата:\n- "чч:мм" (ex. "15:40")',
                reply_markup=admin_kb.inl_cancel_kb
            )
            return
        except EarlierException as e:
            await bot.send_message(
                msg.from_user.id,
                text=str(e),
                reply_markup=admin_kb.inl_cancel_kb,
            )
            return

        data['start_datetime'] = start_datetime

    # Добавление собранных данных в бд.
    queue_name = data['queue_name']
    chat_id = data['chat_id']
    chat_title = data['chat_title']
    queue_id = await sql_add_queue(
        msg.from_user.id,
        queue_name,
        start_datetime,
        chat_id,
        chat_title,
    )

    await bot.send_message(
        msg.from_user.id,
        f"✅ Очередь «{queue_name}» запланирована в чате «{chat_title}»!\n"
        f"Начало очереди: {start_datetime.strftime('%d.%m.%Y в %H:%M')}",
    )

    await bot.send_message(
        chat_id,
        f"✅ Очередь «{queue_name}» запланирована!\n"
        f"Начало очереди: {start_datetime.strftime('%d.%m.%Y в %H:%M')}",
    )

    await state.finish()
    await wait_for_queue_launch(
        start_datetime,
        chat_id,
        queue_id[0],
    )


""" Deleting queue zone"""


async def choose_queue_to_delete_handler(msg: types.Message) -> None:
    """
    Функция-handler выбора запланированной очереди для удаления.
    """
    planned_queues, del_msg = await queues_list_handler(msg)

    if not planned_queues or del_msg is None:
        return

    inl_kb_choices = InlineKeyboardMarkup()
    for queue_id, queue_name, _, _, _ in planned_queues:
        inl_kb_choices.add(types.InlineKeyboardButton(
            text=queue_name, callback_data=f"delete_queue_{queue_id}")
        )
    inl_kb_choices.add(admin_kb.cancel_button)

    global messages_tuple
    messages_tuple = (
        del_msg,
        await bot.send_message(
            msg.from_user.id,
            '🗑 Выберите очередь, которую хотите удалить:',
            reply_markup=inl_kb_choices,
        )
    )

    await FSMDeletion.queue_choice.set()


@dp.callback_query_handler(Text(startswith='delete_queue_'), state=FSMDeletion.queue_choice)
async def delete_queue_handler(callback: types.CallbackQuery, state: FSMContext):
    """
    Функция-handler удаления запланированной очереди.
    """
    chat_id, msg_id = await sql_delete_queue(int(callback.data[len("delete_queue_"):]))
    try:
        await bot.delete_message(chat_id, msg_id)
        await messages_tuple[0].delete()
        await messages_tuple[1].delete()
    except TypeError:
        pass
    finally:
        await callback.answer('💥 Очередь удалена')
        await state.finish()


def register_admin_handlers(dp_: Dispatcher) -> None:
    """Регистрация всех handler-функций для админа."""
    dp_.register_callback_query_handler(
        cancel_handler, text="cancel_call", state="*"
    )
    dp_.register_message_handler(
        queues_list_handler, Text(equals='🗒 Список запланированных очередей'), state=None
    )
    dp_.register_message_handler(
        queues_list_handler, commands="queues_list", state=None
    )
    # Plan queue.
    dp_.register_message_handler(
        queue_plan_handler, Text(equals='📌 Запланировать очередь'), state=None
    )
    dp_.register_message_handler(
        queue_plan_handler, commands='plan_queue', state=None
    )
    dp_.register_callback_query_handler(
        queue_plan_inline_handler, text="plan_queue", state=None
    )
    dp_.register_callback_query_handler(
        queue_set_chat_handler, Text(startswith='choose_chat_'), state=FSMPlanning.choose_chat
    )
    dp_.register_message_handler(
        set_queue_name_handler, content_types='text', state=FSMPlanning.queue_name
    )
    dp_.register_callback_query_handler(
        set_date_handler, calendar_kb.calendar_callback.filter(), state=FSMPlanning.start_date
    )
    dp_.register_message_handler(
        set_datetime_handler, content_types='text', state=FSMPlanning.start_datetime
    )
    # Delete queue.
    dp_.register_message_handler(
        choose_queue_to_delete_handler, Text(equals='🗑 Удалить очередь'), state=None
    )
    dp_.register_message_handler(
        choose_queue_to_delete_handler, Text(equals='🗑 Удалить очередь'), commands='delete_queue', state=None
    )
    dp_.register_callback_query_handler(
        delete_queue_handler, Text(startswith='delete_queue_'), state=FSMDeletion.queue_choice
    )
