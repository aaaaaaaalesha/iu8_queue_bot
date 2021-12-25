# Copyright 2021 aaaaaaaalesha


from datetime import datetime, timedelta
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from src.create_bot import dp, bot


class FSMAdmin(StatesGroup):
    queue_name = State()
    start_time = State()


async def queue_creation_start(message: types.Message):
    await FSMAdmin.queue_name.set()
    await bot.send_message(message.from_user.id, "Задайте название очереди")


async def set_queue_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['queue_name'] = message.text
    await FSMAdmin.next()
    await bot.send_message(
        message.from_user.id,
        'Теперь задайте время запуска очереди одним из способов:\n- в формате: "дд.мм.гг чч:мм" ('
        'ex. "21.01.2022 15:40")\n- "сегодня в чч:мм"\n- "завтра в чч:мм"\n '
    )


def parse_str_to_datetime(text: str) -> datetime:
    resulted_dt: datetime
    if text.startswith("сегодня в "):
        h, m = tuple(map(int, text[-5:].split(':')))
        resulted_dt = datetime.now().replace(hour=h, minute=m, second=0)
    elif text.startswith("завтра в "):
        h, m = tuple(map(int, text[-5:].split(':')))
        tomorrow_dt = datetime.now() + timedelta(days=1)
        resulted_dt = tomorrow_dt.replace(hour=h, minute=m, second=0)
    else:
        resulted_dt = datetime.strptime(text, '%d.%m.%Y %H:%M')

    return resulted_dt


async def set_start_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        try:
            # TODO: work with logic here
            dt = parse_str_to_datetime(message.text)
        except ValueError as e:
            pass
        data['start_date'] = message.text
    await FSMAdmin.next()
    await bot.send_message(message.from_user.id, "hui")


def register_admin_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for admin.
    :param dp: current dispatcher;
    :return: None
    """
    dp.register_message_handler(queue_creation_start, commands='create_queue', state=None)
    dp.register_message_handler(set_queue_name, content_types='text', state=FSMAdmin.queue_name)
    dp.register_message_handler(set_start_time, content_types='text', state=FSMAdmin.start_time)
