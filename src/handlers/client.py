# Copyright 2021 aaaaaaaalesha
import sqlite3

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from datetime import datetime

from src.create_bot import dp, bot
from src.keyboards.client_kb import main_kb, queue_inl_kb
from src.db.sqlite_db import sql_add_queuer
from src.services import client_service


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


async def sign_in_queue_handler(callback: types.CallbackQuery):
    msg_id = callback.message.message_id
    dt = datetime.now()
    queuer_id = callback.from_user.id
    queuer_name = callback.from_user.first_name
    queuer_username = callback.from_user.username

    status_code = await sql_add_queuer(msg_id, dt, queuer_id, queuer_name, queuer_username)
    if status_code == sqlite3.SQLITE_DENY:
        await callback.answer(f"❕ {queuer_name} уже состоит в очереди.")
        return
    elif status_code != sqlite3.SQLITE_OK:
        await callback.answer("📛 Данная очередь больше не работает.")
        return

    new_text = await client_service.add_queuer_text(callback.message.text, queuer_name, queuer_username)

    await callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb)


async def sign_out_queue_handler(callback: types.CallbackQuery):
    pass


def register_client_handlers(dp: Dispatcher) -> None:
    """
    Function for registration all handlers for client.
    """
    dp.register_callback_query_handler(sign_in_queue_handler, Text(startswith='sign_in'), state="*")
    dp.register_message_handler(start_handler, commands=['start', 'help'], state=None)
