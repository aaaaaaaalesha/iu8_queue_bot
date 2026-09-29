from collections.abc import Iterable

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from queue_bot.models import Chat, Queue

CANCEL = "cancel_call"
PLAN_QUEUE = "plan_queue"


class ChooseChatCallback(CallbackData, prefix="choose_chat"):
    chat_id: int


class DeleteQueueCallback(CallbackData, prefix="delete_queue"):
    queue_id: int


def cancel_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🚫 Отмена", callback_data=CANCEL)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[cancel_button()]])


def plan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🗓 Запланировать очередь", callback_data=PLAN_QUEUE)]]
    )


def chats_keyboard(chats: Iterable[Chat]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=chat.title or str(chat.chat_id), callback_data=ChooseChatCallback(chat_id=chat.chat_id).pack()
            )
        ]
        for chat in chats
    ]
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_queues_keyboard(queues: Iterable[Queue]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=queue.name, callback_data=DeleteQueueCallback(queue_id=queue.id).pack())]
        for queue in queues
    ]
    rows.append([cancel_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)
