# Copyright 2021 aaaaaaaalesha

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ReplyKeyboardRemovekb_cancel = ReplyKeyboardMarkup(resize_keyboard=True).add(
#     KeyboardButton('🚫Отмена')
# )

inl_cancel = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='🚫Отмена', callback_data='cancel_call'))
