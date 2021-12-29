# Copyright 2021 aaaaaaaalesha

from aiogram import types, Dispatcher

from src.create_bot import dp, bot
from src.keyboards.client_kb import main_kb


async def start_handler(message: types.Message):
    """
    Handler for `/start` or `/help` command.
    """
    await bot.send_message(message.from_user.id,
                           f"Привет, {message.from_user.first_name} (@{message.from_user.username})!\n"
                           f"Я IU8-QueueBot - бот для создания очередей.\n"
                           f"Давайте начнём: можете использовать команды "
                           f"или кнопки клавиатуры для работы со мной. В случае возникновения проблем, пишите "
                           f"@aaaaaaaalesha",
                           reply_markup=main_kb
                           )

# TODO: handle queue requests here


def register_client_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for client.
    """
    dp.register_message_handler(start_handler, commands=['start', 'help'], state=None)
