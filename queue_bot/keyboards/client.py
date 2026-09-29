from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

PLAN_QUEUE_TEXT = "📌 Запланировать очередь"
DELETE_QUEUE_TEXT = "🗑 Удалить очередь"
PLANNED_QUEUES_TEXT = "🗒 Список запланированных очередей"
MAIN_MENU_TEXTS = (PLAN_QUEUE_TEXT, DELETE_QUEUE_TEXT, PLANNED_QUEUES_TEXT)

SIGN_IN = "sign_in"
SIGN_OUT = "sign_out"
SKIP_AHEAD = "skip_ahead"
IN_TAIL = "in_tail"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=PLAN_QUEUE_TEXT), KeyboardButton(text=DELETE_QUEUE_TEXT)],
            [KeyboardButton(text=PLANNED_QUEUES_TEXT)],
        ],
        resize_keyboard=True,
    )


def queue_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⤴️ Встать в очередь", callback_data=SIGN_IN),
                InlineKeyboardButton(text="↩️ Покинуть очередь", callback_data=SIGN_OUT),
            ],
            [
                InlineKeyboardButton(text="🔃 Пропустить вперёд", callback_data=SKIP_AHEAD),
                InlineKeyboardButton(text="↪️ В хвост очереди", callback_data=IN_TAIL),
            ],
        ]
    )
