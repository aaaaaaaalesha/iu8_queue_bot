# Copyright 2021 aaaaaaaalesha
import asyncio

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import RetryAfter

from src.create_bot import dp, bot
from src.keyboards.client_kb import main_kb, queue_inl_kb
from src.services import client_service


async def start_handler(message: types.Message):
    """
    Handler for `/start` command.
    """
    await bot.send_message(message.from_user.id,
                           f"Привет, {message.from_user.first_name} (@{message.from_user.username})!\n"
                           f"Я IU8-QueueBot - бот для создания очередей.\n"
                           f"Давайте начнём: можете использовать команды (/help ) "
                           f"или кнопки клавиатуры для работы со мной. В случае возникновения проблем, пишите "
                           f"@aaaaaaaalesha",
                           reply_markup=main_kb
                           )


async def help_handler(message: types.Message):
    """
    Handler for `/help` command.
    """
    await bot.send_message(
        message.from_user.id,
        "/start - Начало работы с ботом \n"
        "/help - Вывести доступные команды\n"
        "/plan_queue - Запланировать очередь\n"
        "/queues_list - Вывести список запланированных очередей\n"
        "/delete_queue - Удалить запланированную очередь",
        reply_markup=main_kb
    )


async def flood_handler(update: types.Update, exception: RetryAfter):
    await update.message.answer(f"Не так быстро! Подождите {exception.timeout} секунд")


async def sign_in_queue_handler(callback: types.CallbackQuery):
    queuer_name = callback.from_user.first_name
    queuer_username = callback.from_user.username

    done, _ = await asyncio.wait((client_service.add_queuer_text(callback.message.text, queuer_name, queuer_username),))
    for future in done:
        new_text, status_code = future.result()
        if status_code != client_service.STATUS_OK:
            if status_code == client_service.STATUS_ALREADY_IN:
                await callback.answer(f"❕ Вы уже в очереди.")
                return
        await asyncio.wait((callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb),))


async def sign_out_queue_handler(callback: types.CallbackQuery):
    done, _ = await asyncio.wait(
        (client_service.delete_queuer_text(callback.message.text, callback.from_user.username),))

    for future in done:
        new_text, status_code = future.result()
        if status_code != client_service.STATUS_OK:
            if status_code == client_service.STATUS_NO_QUEUERS:
                await callback.answer("❕ В очереди ещё нет участников.")
                return
            if status_code == client_service.STATUS_NOT_QUEUER:
                await callback.answer(f"❕ @{callback.from_user.username} ещё не участник очереди.")
                return

        await asyncio.wait((callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb),))


async def skip_ahead_handler(callback: types.CallbackQuery):
    new_text, status_code = str(), -1
    done, _ = await asyncio.wait((client_service.skip_ahead(callback.message.text, callback.from_user.username),))

    for future in done:
        new_text, status_code = future.result()

    if status_code != client_service.STATUS_OK:
        if status_code == client_service.STATUS_NO_QUEUERS:
            await callback.answer("❕ В очереди ещё нет участников.")
            return
        if status_code == client_service.STATUS_ONE_QUEUER:
            await callback.answer("❕ В очереди только один участник.")
            return
        if status_code == client_service.STATUS_NOT_QUEUER:
            await callback.answer(f"❕ Вы ещё не участник очереди.")
            return
        if status_code == client_service.STATUS_NO_AFTER:
            await callback.answer("❕ Вы крайний в очереди.")
            return
        await callback.answer("❕ Что-то пошло не так.")
        return

    await callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb)


async def push_tail_handler(callback: types.CallbackQuery):
    new_text, status_code = str(), -1
    done, _ = await asyncio.wait((client_service.push_tail(callback.message.text, callback.from_user.username),))

    for future in done:
        new_text, status_code = future.result()

    if status_code != client_service.STATUS_OK:
        if status_code == client_service.STATUS_NO_QUEUERS:
            await callback.answer("❕ В очереди ещё нет участников.")
            return
        if status_code == client_service.STATUS_ONE_QUEUER:
            await callback.answer("❕ В очереди только один участник.")
            return
        if status_code == client_service.STATUS_NOT_QUEUER:
            await callback.answer(f"❕ Вы ещё не участник очереди.")
            return
        if status_code == client_service.STATUS_NO_AFTER:
            await callback.answer("❕ Вы крайний в очереди.")
            return
        await callback.answer("❕ Что-то пошло не так.")
        return

    await callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb)


def register_client_handlers(dp_: Dispatcher) -> None:
    """
    Function registers all handlers for client.
    """
    dp_.register_message_handler(start_handler, commands='start', state=None)
    dp_.register_message_handler(help_handler, commands="help", state=None)
    dp_.register_errors_handler(flood_handler, exception=RetryAfter)
    dp_.register_callback_query_handler(sign_in_queue_handler, Text(startswith='sign_in'), state="*")
    dp_.register_callback_query_handler(sign_out_queue_handler, Text(startswith='sign_out'), state="*")
    dp_.register_callback_query_handler(skip_ahead_handler, Text(startswith='skip_ahead'), state="*")
    dp_.register_callback_query_handler(push_tail_handler, Text(startswith='in_tail'), state="*")
