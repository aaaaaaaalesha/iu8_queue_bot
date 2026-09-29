"""Parsing of the launch time entered by an admin."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

_TIME_RE = re.compile(r"^\s*(\d{1,2})\s*:\s*(\d{2})\s*$")


class EarlierError(ValueError):
    """The entered moment is already in the past."""


def parse_start(day: date, text: str | None, tz: ZoneInfo, now: datetime | None = None) -> datetime:
    """Combine the chosen date with a "HH:MM" string in the given timezone.

    :raises EarlierError: if the moment is in the past.
    :raises ValueError: if the text is not a valid time.
    """
    match = _TIME_RE.match(text or "")
    if match is None:
        raise ValueError(f"Invalid time: {text!r}")
    start = datetime.combine(day, time(int(match.group(1)), int(match.group(2))), tzinfo=tz)

    now = now or datetime.now(tz)
    if start < now.replace(second=0, microsecond=0):
        raise EarlierError(f"❌ Введённое время раньше текущего!\nСейчас {now.astimezone(tz).strftime('%H:%M')}")
    return start
