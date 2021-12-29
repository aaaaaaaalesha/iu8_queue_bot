# Copyright 2021 aaaaaaaalesha

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

PLAN_QUEUE_TEXT = "📌 Запланировать очередь"
DELETE_QUEUE_TEXT = "🗑 Удалить очередь"
PLANNED_QUEUES_TEXT = "🗒 Список запланированных очередей"

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.row(KeyboardButton(PLAN_QUEUE_TEXT), KeyboardButton(DELETE_QUEUE_TEXT))
main_kb.add(KeyboardButton(PLANNED_QUEUES_TEXT))
