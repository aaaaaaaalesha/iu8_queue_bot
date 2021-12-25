# Copyright 2021 aaaaaaaalesha

from aiogram import types, Dispatcher

from src.create_bot import dp, bot


async def echo(message: types.Message):
    await message.answer(message.text)


def register_shared_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for everyone.
    """
    dp.register_message_handler(echo)
