# Copyright 2021 aaaaaaaalesha

import calendar
from datetime import datetime, timedelta

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from aiogram.types import CallbackQuery

# Setting callback_data prefix and parts.
calendar_callback = CallbackData('simple_calendar', 'act', 'year', 'month', 'day')


class Calendar:
    """Calendar inline keyboard."""

    async def start_calendar(self, year: int = datetime.now().year,
                             month: int = datetime.now().month) -> InlineKeyboardMarkup:
        """
        Creates an inline keyboard with the provided year and month
        :param int year: Year to use in the calendar, if None the current year is used.
        :param int month: Month to use in the calendar, if None the current month is used.
        :return: Returns InlineKeyboardMarkup object with the calendar.
        """
        inline_kb = InlineKeyboardMarkup(row_width=7)
        # For buttons with no answer.
        ignore_callback = calendar_callback.new("IGNORE", year, month, 0)
        # First row - Month and Year
        inline_kb.row()
        inline_kb.insert(InlineKeyboardButton(
            "⏪",
            callback_data=calendar_callback.new("PREV-YEAR", year, month, 1)
        ))
        inline_kb.insert(InlineKeyboardButton(
            f'{calendar.month_name[month][0:3]}. {str(year)}',
            callback_data=ignore_callback
        ))
        inline_kb.insert(InlineKeyboardButton(
            "⏩",
            callback_data=calendar_callback.new("NEXT-YEAR", year, month, 1)
        ))
        # Second row - Week Days
        inline_kb.row()
        for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
            inline_kb.insert(InlineKeyboardButton(day, callback_data=ignore_callback))

        # Calendar rows - days of month.
        month_calendar = calendar.monthcalendar(year, month)
        for week in month_calendar:
            inline_kb.row()
            for day in week:
                if day == 0:
                    inline_kb.insert(InlineKeyboardButton(" ", callback_data=ignore_callback))
                    continue
                # Cross out the irrelevant dates.
                dt_now = datetime.now()
                if dt_now > datetime(year, month, day) and day != dt_now.day:
                    inline_kb.insert(InlineKeyboardButton(
                        self.__strike_through(day), callback_data=ignore_callback
                    ))
                    continue

                inline_kb.insert(InlineKeyboardButton(
                    str(day), callback_data=calendar_callback.new("DAY", year, month, day)
                ))

        # Last row - Buttons.
        inline_kb.row()
        inline_kb.insert(InlineKeyboardButton(
            "◀️", callback_data=calendar_callback.new("PREV-MONTH", year, month, day)
        ))
        inline_kb.insert(InlineKeyboardButton(" ", callback_data=ignore_callback))
        inline_kb.insert(InlineKeyboardButton(
            "▶️", callback_data=calendar_callback.new("NEXT-MONTH", year, month, day)
        ))
        # For cancelling plan queue.
        inline_kb.add(InlineKeyboardButton(text='🚫 Отмена', callback_data='cancel_call'))

        return inline_kb

    @staticmethod
    def __strike_through(day: int) -> str:
        result = f" \u0336"
        for c in str(day):
            result += f'{c}\u0336'
        return result + f" \u0336"

    async def process_selection(self, query: CallbackQuery, data: dict) -> tuple:
        """
        Process the callback_query. This method generates a new calendar if forward or
        backward is pressed. This method should be called inside a CallbackQueryHandler.
        :param query: callback_query, as provided by the CallbackQueryHandler
        :param data: callback_data, dictionary, set by calendar_callback
        :return: Returns a tuple (Boolean,datetime), indicating if a date is selected
                    and returning the date if so.
        """
        return_data = (False, None)
        temp_date = datetime(int(data['year']), int(data['month']), 1)

        # Processing empty buttons, answering with no action.
        if data['act'] == "IGNORE":
            await query.answer(cache_time=60)
        # User picked a day button, return date.
        if data['act'] == "DAY":
            await query.message.delete_reply_markup()  # removing inline keyboard
            return_data = True, datetime(int(data['year']), int(data['month']), int(data['day']))
        # User navigates to previous year, editing message with new calendar.
        if data['act'] == "PREV-YEAR":
            prev_date = temp_date - timedelta(days=365)
            await query.message.edit_reply_markup(await self.start_calendar(int(prev_date.year), int(prev_date.month)))
        # User navigates to next year, editing message with new calendar.
        if data['act'] == "NEXT-YEAR":
            next_date = temp_date + timedelta(days=365)
            await query.message.edit_reply_markup(await self.start_calendar(int(next_date.year), int(next_date.month)))
        # User navigates to previous month, editing message with new calendar.
        if data['act'] == "PREV-MONTH":
            prev_date = temp_date - timedelta(days=1)
            await query.message.edit_reply_markup(await self.start_calendar(int(prev_date.year), int(prev_date.month)))
        # User navigates to next month, editing message with new calendar.
        if data['act'] == "NEXT-MONTH":
            next_date = temp_date + timedelta(days=31)
            await query.message.edit_reply_markup(await self.start_calendar(int(next_date.year), int(next_date.month)))
        # At some point user clicks DAY button, returning date.
        return return_data
