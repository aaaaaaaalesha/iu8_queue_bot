# Copyright 2021 aaaaaaaalesha


from datetime import datetime, timedelta
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from src.create_bot import dp, bot
from src.db.sqlite_db import sql_add_queue, sql_add_admin
from src.keyboards import admin_kb


class FSMAdmin(StatesGroup):
    queue_name = State()
    start_datetime = State()


async def queue_creation_start(message: types.Message) -> None:
    await FSMAdmin.queue_name.set()

    await sql_add_admin(message.from_user.id, message.from_user.username)

    await bot.send_message(message.from_user.id, "Задайте название очереди",
                           reply_markup=admin_kb.inl_cancel)


async def cancel_queue_creation(callback: types.CallbackQuery, state: FSMContext) -> None:
    # await bot.send_message(
    #     message.from_user.id, '🚫Создание очереди отменено',
    # )
    await callback.answer('🚫Создание очереди отменено')
    await state.finish()


async def set_queue_name(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        await bot.send_message(
            message.from_user.id, '❌ Кажется, вы ничего не написали! Задайте название очереди',
            reply_markup=admin_kb.inl_cancel
        )
        return
    async with state.proxy() as data:
        data['queue_name'] = message.text
    await FSMAdmin.next()
    await bot.send_message(
        message.from_user.id,
        'Теперь задайте время запуска очереди одним из способов:\n- в формате: "дд.мм.гг чч:мм" ('
        'ex. "21.01.2022 15:40")\n- "сегодня в чч:мм"\n- "завтра в чч:мм"\n',
        reply_markup=admin_kb.inl_cancel
    )


class EarlierException(Exception):
    pass


def parse_str_to_datetime(text: str) -> datetime:
    resulted_dt: datetime
    dt_now = datetime.now()
    if text.startswith("сегодня в ") or text.startswith("сегодня "):
        h, m = tuple(map(int, text[-5:].split(':')))
        resulted_dt = dt_now.replace(hour=h, minute=m, second=0)
    elif text.startswith("завтра в ") or text.startswith("завтра "):
        h, m = tuple(map(int, text[-5:].split(':')))
        tomorrow_dt = dt_now + timedelta(days=1)
        resulted_dt = tomorrow_dt.replace(hour=h, minute=m, second=0)
    else:
        resulted_dt = datetime.strptime(text, '%d.%m.%Y %H:%M')

    if resulted_dt < dt_now:
        raise EarlierException(f"❌ Введённое время раньше текущего!\nСейчас {dt_now.strftime('%d.%m.%Y %H:%M')}")

    return resulted_dt


async def set_start_time(message: types.Message, state: FSMContext) -> None:
    start_datetime: datetime
    async with state.proxy() as data:
        try:
            start_datetime = parse_str_to_datetime(message.text)
        except ValueError:
            await bot.send_message(
                message.from_user.id,
                '❌ Время задано неверно! Проверьте правильность формата:\n- "дд.мм.гг чч:мм" ('
                'ex. "21.01.2022 15:40")\n- "сегодня в чч:мм"\n- "завтра в чч:мм"\n',
                reply_markup=admin_kb.inl_cancel
            )
            return
        except EarlierException as e:
            await bot.send_message(
                message.from_user.id, e,
                reply_markup=admin_kb.inl_cancel
            )
            return

        data['start_datetime'] = start_datetime

    # Добавление собранных данных в бд.
    queue_name = data['queue_name']
    await sql_add_queue(message.from_user.id, queue_name, start_datetime)

    await bot.send_message(message.from_user.id,
                           f"Очередь {queue_name} создана!\nНачало очереди: {start_datetime.strftime('%d.%m.%Y %H:%M')}\n")
    await state.finish()


def register_admin_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for admin.
    :return: None
    """
    dp.register_message_handler(queue_creation_start, commands='create_queue', state=None)
    dp.register_callback_query_handler(cancel_queue_creation, text="cancel_call", state="*")
    dp.register_message_handler(set_queue_name, content_types='text', state=FSMAdmin.queue_name)
    dp.register_message_handler(set_start_time, content_types='text', state=FSMAdmin.start_datetime)
