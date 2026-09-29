"""Tracking the group chats the bot is a member of."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import JOIN_TRANSITION, LEAVE_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated, Message

from queue_bot.db.repository import Repository
from queue_bot.services.scheduler import QueueScheduler
from queue_bot.services.updater import QueueMessageUpdater

logger = logging.getLogger(__name__)

GROUP_CHATS = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})


async def bot_added_handler(event: ChatMemberUpdated, bot: Bot, repo: Repository) -> None:
    user = event.from_user
    await repo.add_chat(event.chat.id, event.chat.title or "", user.id, user.username)
    logger.info("Bot was added to chat %s by %s", event.chat.id, user.id)
    try:
        await bot.send_message(
            event.chat.id,
            f"Привет! Теперь {user.first_name} (@{user.username}) – администратор очередей в этом чате.\n"
            "Запланировать её можно в личном чате со мной. Приятной работы!",
        )
    except TelegramAPIError as e:
        logger.warning("Can't greet chat %s: %s", event.chat.id, e)


async def bot_removed_handler(
    event: ChatMemberUpdated, repo: Repository, scheduler: QueueScheduler, updater: QueueMessageUpdater
) -> None:
    for queue_id in await repo.remove_chat(event.chat.id):
        scheduler.cancel(queue_id)
        updater.forget(queue_id)
    logger.info("Bot was removed from chat %s", event.chat.id)


async def chat_migrated_handler(message: Message, repo: Repository) -> None:
    """A group was converted to a supergroup and got a new id."""
    assert message.migrate_to_chat_id is not None
    await repo.migrate_chat(message.chat.id, message.migrate_to_chat_id)
    logger.info("Chat %s migrated to %s", message.chat.id, message.migrate_to_chat_id)


async def chat_renamed_handler(message: Message, repo: Repository) -> None:
    assert message.new_chat_title is not None
    await repo.rename_chat(message.chat.id, message.new_chat_title)


def build_router() -> Router:
    router = Router(name="chat_events")
    router.my_chat_member.filter(GROUP_CHATS)
    router.my_chat_member.register(bot_added_handler, ChatMemberUpdatedFilter(JOIN_TRANSITION))
    router.my_chat_member.register(bot_removed_handler, ChatMemberUpdatedFilter(LEAVE_TRANSITION))
    router.message.register(chat_migrated_handler, F.migrate_to_chat_id, GROUP_CHATS)
    router.message.register(chat_renamed_handler, F.new_chat_title, GROUP_CHATS)
    return router
