# Copyright 2021 aaaaaaaalesha

from datetime import datetime, timedelta


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
