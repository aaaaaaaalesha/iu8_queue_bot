"""Inline calendar for choosing the launch date."""

from __future__ import annotations

import calendar
from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from queue_bot.keyboards.admin import cancel_button

WEEK_DAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


class CalendarAction:
    IGNORE = "IGNORE"
    DAY = "DAY"
    PREV_YEAR = "PREV-YEAR"
    NEXT_YEAR = "NEXT-YEAR"
    PREV_MONTH = "PREV-MONTH"
    NEXT_MONTH = "NEXT-MONTH"


class CalendarCallback(CallbackData, prefix="simple_calendar"):
    act: str
    year: int
    month: int
    day: int


def _strike_through(day: int) -> str:
    return " ̶" + "".join(f"{c}̶" for c in str(day)) + " ̶"


def _button(text: str, act: str, year: int, month: int, day: int = 0) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text, callback_data=CalendarCallback(act=act, year=year, month=month, day=day).pack()
    )


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def calendar_keyboard(year: int, month: int, today: date) -> InlineKeyboardMarkup:
    ignore = CalendarAction.IGNORE
    rows: list[list[InlineKeyboardButton]] = [
        [
            _button("⏪", CalendarAction.PREV_YEAR, year, month),
            _button(f"{calendar.month_name[month][:3]}. {year}", ignore, year, month),
            _button("⏩", CalendarAction.NEXT_YEAR, year, month),
        ],
        [_button(day, ignore, year, month) for day in WEEK_DAYS],
    ]

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(_button(" ", ignore, year, month))
            elif date(year, month, day) < today:
                # Past dates can't be chosen.
                row.append(_button(_strike_through(day), ignore, year, month))
            else:
                row.append(_button(str(day), CalendarAction.DAY, year, month, day))
        rows.append(row)

    rows.append(
        [
            _button("◀️", CalendarAction.PREV_MONTH, year, month),
            _button(" ", ignore, year, month),
            _button("▶️", CalendarAction.NEXT_MONTH, year, month),
        ]
    )
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def navigate(data: CalendarCallback) -> tuple[int, int] | None:
    """Year and month to show after a navigation button, None for other buttons."""
    shifts = {
        CalendarAction.PREV_YEAR: -12,
        CalendarAction.NEXT_YEAR: 12,
        CalendarAction.PREV_MONTH: -1,
        CalendarAction.NEXT_MONTH: 1,
    }
    if data.act not in shifts:
        return None
    year, month = shift_month(data.year, data.month, shifts[data.act])
    if not date.min.year <= year <= date.max.year:
        return None
    return year, month
