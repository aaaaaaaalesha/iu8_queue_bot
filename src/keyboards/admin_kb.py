# Copyright 2021 aaaaaaaalesha

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

cancel_button = InlineKeyboardButton(text='🚫 Отмена', callback_data='cancel_call', )
inl_cancel_kb = InlineKeyboardMarkup().add(cancel_button)

inl_plan_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(text='🗓 Запланировать очередь', callback_data='plan_queue')
)

queue_inl_kb = InlineKeyboardMarkup(row_width=2)
queue_inl_kb.row(
    InlineKeyboardButton(text='⤴️ Встать в очередь', callback_data='sign_in'),
    InlineKeyboardButton(text='↩️ Покинуть очередь', callback_data='sign_out')
)
queue_inl_kb.add(
    InlineKeyboardButton(text='🔃 Пропустить вперёд себя', callback_data='skip_ahead'),
    InlineKeyboardButton(text='↪️ В хвост очереди', callback_data='in_tail')
)
