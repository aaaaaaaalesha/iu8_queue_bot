# Copyright 2021 aaaaaaaalesha

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

inl_cancel_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='🚫 Отмена', callback_data='cancel_call')
)
inl_plan_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='🗓 Запланировать очередь', callback_data='plan_queue')
)
