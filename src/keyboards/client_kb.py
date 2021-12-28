# Copyright 2021 aaaaaaaalesha

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

main_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
main_kb.row(KeyboardButton("📌 Запланировать очередь"), KeyboardButton("🗑 Удалить очередь"))
main_kb.add(KeyboardButton("🗒 Список запланированных очередей"))
