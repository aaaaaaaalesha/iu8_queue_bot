# Copyright 2021 aaaaaaaalesha

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PLAN_QUEUE_TEXT = "📌 Запланировать очередь"
DELETE_QUEUE_TEXT = "🗑 Удалить очередь"
PLANNED_QUEUES_TEXT = "🗒 Список запланированных очередей"

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.row(KeyboardButton(PLAN_QUEUE_TEXT), KeyboardButton(DELETE_QUEUE_TEXT))
main_kb.add(KeyboardButton(PLANNED_QUEUES_TEXT))


queue_inl_kb = InlineKeyboardMarkup(row_width=2)
queue_inl_kb.row(
    InlineKeyboardButton(text='⤴️ Встать в очередь', callback_data='sign_in'),
    InlineKeyboardButton(text='↩️ Покинуть очередь', callback_data='sign_out')
)
queue_inl_kb.add(
    InlineKeyboardButton(text='🔃 Пропустить вперёд', callback_data='skip_ahead'),
    InlineKeyboardButton(text='↪️ В хвост очереди', callback_data='in_tail')
)
