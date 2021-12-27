# Copyright 2021 aaaaaaaalesha

from aiogram import types, Dispatcher

from src.create_bot import dp, bot
from src.keyboards.client_kb import main_kb


async def welcome_msg(message: types.Message):
    """
    Handler for `/start` or `/help` command.
    """
    await bot.send_message(message.from_user.id,
                           f"Hello, {message.from_user.username}! My name is IU8-QueueBot.\nLet's start our work!",
                           reply_markup=main_kb
                           )


def register_client_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for client.
    """
    dp.register_message_handler(welcome_msg, commands=['start', 'help'])
