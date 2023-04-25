from aiogram import types

from src.__main__ import dp, bot, db


@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_handler(message: types.Message) -> None:
    """
    Функция-handler обработки добавления бота в групповой чат.
    """
    # Проверяем, что бот был добавлен в чат.
    if any(bot.id == member.id for member in message.new_chat_members):
        user = message.from_user
        await db.add_admin(user.id, user.username)
        await db.add_managed_chat(user.id, message.chat.id, message.chat.title)
        await message.reply(
            f'Привет! Теперь {user.first_name} (@{user.username}) – '
            'администратор очередей в этом чате.\n'
            'Запланировать её можно в личном чате со мной. Приятной работы!'
        )


@dp.message_handler(content_types=types.ContentTypes.LEFT_CHAT_MEMBER)
async def left_chat_handler(message: types.Message) -> None:
    """
    Функция-handler обработки удаления бота из группового чата.
    """
    if bot.id == message.left_chat_member.id:
        await db.delete_managed_chat(message.chat.id)
