import asyncio

from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.utils import exceptions

from src.loader import dp, db, bot
from src.keyboards.client_kb import main_kb, queue_inl_kb
from src.services import client_service
from src.services.client_service import QueueStatus


@dp.message_handler(commands='start')
async def start_handler(message: types.Message):
    """Функция-handler для команды `/start`."""
    await bot.send_message(
        message.from_user.id,
        f'Привет, {message.from_user.first_name} (@{message.from_user.username})!\n'
        f'Я IU8-QueueBot - бот для создания очередей.\n'
        'Давайте начнём: можете использовать команды (/help) '
        f'или кнопки клавиатуры для работы со мной. В случае возникновения проблем, пишите '
        f'@aaaaaaaalesha',
        reply_markup=main_kb,
    )


@dp.message_handler(commands='help')
async def help_handler(message: types.Message):
    """Функция-handler для команды `/help`."""
    await bot.send_message(
        message.from_user.id,
        '/start - Начало работы с ботом \n'
        '/help - Вывести доступные команды\n'
        '/plan_queue - Запланировать очередь\n'
        '/queues_list - Вывести список запланированных очередей\n'
        '/delete_queue - Удалить запланированную очередь',
        reply_markup=main_kb
    )


@dp.errors_handler(exception=exceptions.RetryAfter)
async def flood_handler(update: types.Update, exception: exceptions.RetryAfter):
    pass
    # answer_msg = f'Не так быстро! Подождите {exception.timeout} секунд'
    # if update.message is not None:
    #    await update.message.answer(answer_msg)
    # elif update.callback_query is not None:
    #    await update.message.answer(answer_msg)


@dp.callback_query_handler(Text(startswith='sign_in'), state='*')
async def sign_in_queue_handler(callback: types.CallbackQuery):
    user = callback.from_user

    async with asyncio.Lock():
        old_text, = await db.get_queue_text(callback.message.message_id)
        new_text, status_code = await client_service.add_queuer_text(
            old_text,
            user.first_name,
            user.username,
        )
        match status_code:
            case QueueStatus.OK:
                await db.update_queue_text(
                    callback.message.message_id,
                    new_text,
                )
                await callback.message.edit_text(
                    text=new_text,
                    reply_markup=queue_inl_kb,
                )
            case QueueStatus.EXISTS:
                await callback.answer('❕ Вы уже в очереди.')


@dp.callback_query_handler(Text(startswith='sign_out'), state='*')
async def sign_out_queue_handler(callback: types.CallbackQuery):
    user = callback.from_user
    async with asyncio.Lock():
        old_text, = await db.get_queue_text(callback.message.message_id)
        new_text, status_code = await client_service.delete_queuer_text(
            old_text,
            user.first_name,
            user.username,
        )

        match status_code:
            case QueueStatus.OK:
                await db.update_queue_text(
                    callback.message.message_id,
                    new_text,
                )
                await callback.message.edit_text(
                    text=new_text,
                    reply_markup=queue_inl_kb,
                )
            case QueueStatus.EMPTY | QueueStatus.NOT_QUEUER as answer:
                await callback.answer(answer)


@dp.callback_query_handler(Text(startswith='skip_ahead'), state='*')
async def skip_ahead_handler(callback: types.CallbackQuery):
    user = callback.from_user
    async with asyncio.Lock():
        old_text, = await db.get_queue_text(callback.message.message_id)
        new_text, status_code = await client_service.skip_ahead(
            old_text,
            user.first_name,
            user.username,
        )
        match status_code:
            case QueueStatus.OK:
                await db.update_queue_text(
                    callback.message.message_id,
                    new_text,
                )
                await callback.message.edit_text(
                    text=new_text,
                    reply_markup=queue_inl_kb,
                )
            case (QueueStatus.EMPTY
                  | QueueStatus.ONE_QUEUER
                  | QueueStatus.NOT_QUEUER
                  | QueueStatus.NO_AFTER) as answer:
                await callback.answer(answer)
            case _:
                await callback.answer('❕ Что-то пошло не так')


@dp.callback_query_handler(Text(startswith='in_tail'), state='*')
async def push_tail_handler(callback: types.CallbackQuery):
    user = callback.from_user
    async with asyncio.Lock():
        old_text, = await db.get_queue_text(callback.message.message_id)
        new_text, status_code = await client_service.push_tail(
            old_text,
            user.first_name,
            user.username,
        )

        match status_code:
            case QueueStatus.OK:
                await db.update_queue_text(
                    callback.message.message_id,
                    new_text,
                )
                await callback.message.edit_text(
                    text=new_text,
                    reply_markup=queue_inl_kb,
                )
            case (QueueStatus.EMPTY
                  | QueueStatus.ONE_QUEUER
                  | QueueStatus.NOT_QUEUER
                  | QueueStatus.NO_AFTER) as answer:
                await callback.answer(answer)
            case _:
                await callback.answer('❕ Что-то пошло не так')
