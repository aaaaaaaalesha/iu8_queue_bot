from aiogram import executor

from create_bot import dp, logger
from handlers import admin, client, shared
from db import sqlite_db


async def on_startup(_) -> None:
    logger.info("Bot now is online!")
    sqlite_db.start_db()


async def on_shutdown(_) -> None:
    logger.info("Bot now is offline!")
    sqlite_db.stop_db()


def main():
    admin.register_admin_handlers(dp)
    client.register_client_handlers(dp)
    shared.register_shared_handlers(dp)
    executor.start_polling(
        dispatcher=dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )


if __name__ == '__main__':
    main()
