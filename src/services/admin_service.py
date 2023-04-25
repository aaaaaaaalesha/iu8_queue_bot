import datetime as dt
from pytz import timezone
import asyncio
from aiogram.utils.exceptions import BadRequest

from src.loader import bot, db
from src.keyboards import client_kb


class EarlierException(Exception):
    pass


async def wait_for_queue_launch(start_dt: dt.datetime, chat_id: int, queue_id: int) -> None:
    """
    Ожидание начала запуска очереди в групповом чате.
    """
    await asyncio.sleep(
        (start_dt - dt.datetime.now(timezone('Europe/Moscow'))).seconds
    )

    # Проверим, что очередь не была удалена.
    queue_data = await db.get_queue_from_list(queue_id)
    if not queue_data:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🗑 Кажется, запланированную на это время очередь, удалили :(",
        )
        return

    msg = await bot.send_message(
        chat_id,
        f"🆕 🅠🅤🅔🅤🅔 🆕\n Очередь «{queue_data[2]}» запущена!\n\n",
        reply_markup=client_kb.queue_inl_kb
    )
    try:
        await msg.pin(disable_notification=False)
    except BadRequest:
        pass

    await db.post_queue_msg_id(queue_id, msg.message_id)


def parse_to_datetime(date: dt.datetime, input_time: str) -> dt.datetime:
    """
    Парсинг времени в формате hh:mm, а также проверка, что введённое время позже указанного.
    """
    dt_now = dt.datetime.now(timezone('Europe/Moscow'))
    h, m = tuple(map(int, input_time.split(':')))

    resulted_date = date
    if resulted_date.replace(hour=h, minute=m, second=0) < dt_now:
        raise EarlierException(
            f"❌ Введённое время раньше текущего!\nСейчас {dt_now.strftime('%H:%M')}"
        )

    return date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo)
