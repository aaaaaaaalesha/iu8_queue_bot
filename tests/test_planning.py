from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from queue_bot.keyboards.calendar import CalendarCallback, calendar_keyboard, navigate, shift_month
from queue_bot.models import Member
from queue_bot.services.planning import EarlierError, parse_start
from queue_bot.services.rendering import format_start, parse_legacy_members, render_queue

MSK = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 9, 29, 12, 30, 15, tzinfo=MSK)


def test_parse_start() -> None:
    start = parse_start(date(2026, 10, 3), "15:40", MSK, now=NOW)
    assert start == datetime(2026, 10, 3, 15, 40, tzinfo=MSK)
    # The real Moscow offset, not the LMT offset pytz used to produce.
    assert start.utcoffset() is not None and start.utcoffset().total_seconds() == 3 * 3600
    assert parse_start(date(2026, 9, 29), " 9:05 ", MSK, now=NOW.replace(hour=8)).hour == 9
    # The current minute is still allowed.
    assert parse_start(date(2026, 9, 29), "12:30", MSK, now=NOW)


@pytest.mark.parametrize("text", ["", None, "abc", "25:00", "12:60", "12-30", "12:30:00", "1230"])
def test_parse_start_invalid(text: str | None) -> None:
    with pytest.raises(ValueError):
        parse_start(date(2026, 10, 3), text, MSK, now=NOW)


def test_parse_start_in_the_past() -> None:
    with pytest.raises(EarlierError, match="Сейчас 12:30"):
        parse_start(date(2026, 9, 29), "12:29", MSK, now=NOW)


def test_shift_month() -> None:
    assert shift_month(2026, 12, 1) == (2027, 1)
    assert shift_month(2026, 1, -1) == (2025, 12)
    assert shift_month(2026, 5, -12) == (2025, 5)


def test_calendar_callback_format_is_compatible() -> None:
    packed = CalendarCallback(act="DAY", year=2026, month=9, day=29).pack()
    assert packed == "simple_calendar:DAY:2026:9:29"
    assert navigate(CalendarCallback(act="NEXT-MONTH", year=2026, month=12, day=0)) == (2027, 1)
    assert navigate(CalendarCallback(act="DAY", year=2026, month=12, day=1)) is None


def test_calendar_strikes_out_past_days() -> None:
    markup = calendar_keyboard(2026, 9, date(2026, 9, 29))
    buttons = {b.text: b.callback_data for row in markup.inline_keyboard for b in row}
    assert buttons["29"] == "simple_calendar:DAY:2026:9:29"
    assert "28" not in buttons  # rendered struck through
    # The same day number in another month is not affected.
    markup = calendar_keyboard(2026, 10, date(2026, 9, 29))
    assert any(b.text == "1" for row in markup.inline_keyboard for b in row)


def test_render_queue_roundtrip() -> None:
    members = [Member(1, "Ann", "ann"), Member(2, "Bob", None)]
    text = render_queue("Лаба", members)
    assert text == "🆕 🅠🅤🅔🅤🅔 🆕\nОчередь «Лаба» запущена!\n1. Ann (@ann)\n2. Bob"
    assert parse_legacy_members(text) == ["Ann (@ann)", "Bob"]


def test_format_start() -> None:
    assert format_start(int(NOW.timestamp()), MSK) == "29.09.2026 в 12:30"
