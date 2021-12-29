# Copyright 2021 aaaaaaaalesha

from datetime import datetime
from src.create_bot import bot
import asyncio


class EarlierException(Exception):
    pass


async def wait_for_queue_launch(start_dt: datetime, chat_id: int) -> None:
    await asyncio.sleep((start_dt - datetime.now()).seconds)
    # TODO: handle queue launching here
    await bot.send_message(chat_id, f"Погнали, чёрт побери! {start_dt.strftime('%d.%m.%Y в %H:%M')}")


def parse_to_datetime(date: datetime, text: str) -> datetime:
    dt_now = datetime.now()
    h, m = tuple(map(int, text.split(':')))

    resulted_date = date
    if resulted_date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo) < datetime.now():
        raise EarlierException(f"❌ Введённое время раньше текущего!\nСейчас {dt_now.strftime('%H:%M')}")

    return date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo)
