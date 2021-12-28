# Copyright 2021 aaaaaaaalesha

from datetime import datetime, timedelta
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from src.create_bot import dp, bot
from src.db.sqlite_db import sql_get_queue_list, sql_add_queue, sql_add_admin
from src.keyboards import admin_kb
from src.keyboards.client_kb import main_kb
from src.services.admin_service import EarlierException, parse_to_datetime


class FSMAdmin(StatesGroup):
    queue_name = State()
    start_datetime = State()


async def queues_list_handler(message: types.Message) -> None:
    found_queues = sql_get_queue_list(message.from_user.id)
    if not found_queues:
        await bot.send_message(
            message.from_user.id,
            "🙊 У вас пока нет запланированных очередей.\nЗапланируем одну?",
            reply_markup=admin_kb.inl_plan_kb
        )
        return

    out_str = str()
    for queue_name, dt in found_queues:
        out_str += f"📌«{queue_name}» {datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y в %H:%M')}\n"

    await bot.send_message(message.from_user.id, f"⤵️ Вот запланированные вами очереди:\n{out_str}")


async def queue_plan_inlbutton_handler(callback: types.CallbackQuery) -> None:
    await callback.answer('📑 Переходим к планированию очереди...')
    await FSMAdmin.queue_name.set()

    await sql_add_admin(callback.from_user.id, callback.from_user.username)

    await bot.send_message(callback.from_user.id, "📝 Задайте название очереди",
                           reply_markup=admin_kb.inl_cancel_kb)


async def queue_plan_handler(message: types.Message) -> None:
    await FSMAdmin.queue_name.set()

    await sql_add_admin(message.from_user.id, message.from_user.username)

    await bot.send_message(message.from_user.id, "📝 Задайте название очереди",
                           reply_markup=admin_kb.inl_cancel_kb)


async def cancel_plan_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer('🚫 Создание очереди отменено')
    await state.finish()


async def set_queue_name_handler(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await bot.send_message(
            message.from_user.id, '❌ Кажется, вы ничего не написали! Задайте название очереди',
            reply_markup=admin_kb.inl_cancel_kb
        )
        return
    async with state.proxy() as data:
        data['queue_name'] = message.text
    await FSMAdmin.next()
    await bot.send_message(
        message.from_user.id,
        '🕘 Теперь задайте время запуска очереди одним из способов:\n- в формате: "дд.мм.гг чч:мм" ('
        'ex. "21.01.2022 15:40")\n- "сегодня в чч:мм"\n- "завтра в чч:мм"\n',
        reply_markup=admin_kb.inl_cancel_kb
    )


async def set_datetime_handler(message: types.Message, state: FSMContext) -> None:
    start_datetime: datetime
    async with state.proxy() as data:
        try:
            start_datetime = parse_to_datetime(message.text)
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                '❌ Время задано неверно! Проверьте правильность формата:\n- "дд.мм.гг чч:мм" ('
                'ex. "21.01.2022 15:40")\n- "сегодня в чч:мм"\n- "завтра в чч:мм"\n',
                reply_markup=admin_kb.inl_cancel_kb
            )
            return
        except EarlierException as e:
            await bot.send_message(
                message.from_user.id, e,
                reply_markup=admin_kb.inl_cancel_kb
            )
            return

        data['start_datetime'] = start_datetime

    # Добавление собранных данных в бд.
    queue_name = data['queue_name']
    await sql_add_queue(message.from_user.id, queue_name, start_datetime)

    await bot.send_message(
        message.from_user.id,
        f"✅Очередь «{queue_name}» создана!\nНачало очереди: {start_datetime.strftime('%d.%m.%Y в %H:%M')}"
    )
    await state.finish()


def register_admin_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for admin.
    :return: None
    """
    dp.register_message_handler(queue_plan_handler, commands='create_queue', state=None)
    dp.register_callback_query_handler(queue_plan_inlbutton_handler, text="plan_queue")
    dp.register_message_handler(queue_plan_handler, Text(equals='📌 Запланировать очередь'))
    dp.register_callback_query_handler(queue_plan_inlbutton_handler, text="plan_queue")
    dp.register_message_handler(queues_list_handler, Text(equals='🗒 Список запланированных очередей'))
    dp.register_callback_query_handler(cancel_plan_handler, text="cancel_call", state="*")
    dp.register_message_handler(set_queue_name_handler, content_types='text', state=FSMAdmin.queue_name)
    dp.register_message_handler(set_datetime_handler, content_types='text', state=FSMAdmin.start_datetime)
