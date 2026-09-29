"""Wiring of the bot: storage, services, dispatcher."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import BotCommand

from queue_bot.config import Settings
from queue_bot.db.database import Database
from queue_bot.db.repository import Repository
from queue_bot.handlers import build_router
from queue_bot.services.scheduler import QueueScheduler
from queue_bot.services.updater import QueueMessageUpdater

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description="Начало работы с ботом"),
    BotCommand(command="help", description="Вывести доступные команды"),
    BotCommand(command="plan_queue", description="Запланировать очередь"),
    BotCommand(command="queues_list", description="Вывести список запланированных очередей"),
    BotCommand(command="delete_queue", description="Удалить запланированную очередь"),
]


def build_dispatcher(settings: Settings, bot: Bot) -> Dispatcher:
    db = Database(settings.database_path)
    repo = Repository(db)
    updater = QueueMessageUpdater(bot, repo, interval=settings.edit_interval)
    scheduler = QueueScheduler(bot, repo, updater)

    # SimpleEventIsolation processes updates of the same user in the same chat
    # one by one (e.g. a double click on a button), updates of different users
    # are still handled concurrently.
    dp = Dispatcher(
        storage=MemoryStorage(),
        events_isolation=SimpleEventIsolation(),
        settings=settings,
        repo=repo,
        updater=updater,
        scheduler=scheduler,
    )
    dp.include_router(build_router())

    @dp.startup()
    async def on_startup() -> None:
        await db.connect()
        await scheduler.restore()
        try:
            await bot.set_my_commands(BOT_COMMANDS)
        except Exception:
            logger.warning("Can't set bot commands", exc_info=True)
        logger.info("Bot is online!")

    @dp.shutdown()
    async def on_shutdown() -> None:
        await scheduler.close()
        await updater.close()
        await db.close()
        logger.info("Bot is stopped")

    return dp


async def run() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = Bot(settings.bot_token)
    dp = build_dispatcher(settings, bot)
    # Updates received while the bot was offline are processed, not dropped:
    # button presses made during a restart must not be lost.
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
