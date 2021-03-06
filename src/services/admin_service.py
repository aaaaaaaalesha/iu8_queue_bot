# Copyright 2021 aaaaaaaalesha

from datetime import datetime, timedelta
from pytz import timezone
import asyncio
from aiogram.utils.exceptions import BadRequest

from src.create_bot import bot
from src.db.sqlite_db import sql_get_queue_from_list, sql_post_queue_msg_id
from src.keyboards import client_kb


class EarlierException(Exception):
    pass


async def wait_for_queue_launch(start_dt: datetime, chat_id: int, queue_id: int) -> None:
    await asyncio.sleep((start_dt - datetime.now(timezone('Europe/Moscow'))).seconds)
    # Check that queue has not been deleted.
    queue_data = await sql_get_queue_from_list(queue_id)
    if not queue_data:
        await bot.send_message(chat_id,
                               f"🗑 Кажется, запланированную на это время очередь, удалили :(")
        return

    msg = await bot.send_message(chat_id,
                                 f"🆕 🅠🅤🅔🅤🅔 🆕\n"
                                 f"Очередь «{queue_data[2]}» запущена!\n"
                                 f"",
                                 reply_markup=client_kb.queue_inl_kb
                                 )
    try:
        await msg.pin(disable_notification=False)
    except BadRequest:
        pass

    await sql_post_queue_msg_id(queue_id, msg.message_id)


def parse_to_datetime(date: datetime, text: str) -> datetime:
    dt_now = datetime.now(timezone('Europe/Moscow'))
    h, m = tuple(map(int, text.split(':')))

    resulted_date = date
    if resulted_date.replace(hour=h, minute=m, second=0) < dt_now:
        raise EarlierException(f"❌ Введённое время раньше текущего!\nСейчас {dt_now.strftime('%H:%M')}")

    return date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo)
