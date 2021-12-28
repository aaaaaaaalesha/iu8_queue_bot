# Copyright 2021 aaaaaaaalesha

from datetime import datetime, timedelta


class EarlierException(Exception):
    pass


def parse_to_datetime(date: datetime, text: str) -> datetime:
    dt_now = datetime.now()
    h, m = tuple(map(int, text.split(':')))

    resulted_date = date
    if resulted_date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo) < datetime.now():
        raise EarlierException(f"❌ Введённое время раньше текущего!\nСейчас {dt_now.strftime('%H:%M')}")

    return date.replace(hour=h, minute=m, second=0, tzinfo=dt_now.tzinfo)
