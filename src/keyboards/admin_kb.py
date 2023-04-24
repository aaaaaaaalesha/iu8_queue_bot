from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

cancel_button = InlineKeyboardButton(
    text='🚫 Отмена',
    callback_data='cancel_call',
)
inl_cancel_kb = InlineKeyboardMarkup().add(cancel_button)
inl_plan_kb = InlineKeyboardMarkup().add(
    InlineKeyboardButton(
        text='🗓 Запланировать очередь',
        callback_data='plan_queue',
    )
)
