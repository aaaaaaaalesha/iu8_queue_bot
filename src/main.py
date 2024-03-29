from aiogram import executor

from create_bot import dp
from handlers import admin, client, shared
from db import sqlite_db


async def on_startup(_) -> None:
    print("Bot is online!")
    sqlite_db.start_db()


def main():
    admin.register_admin_handlers(dp)
    client.register_client_handlers(dp)
    shared.register_shared_handlers(dp)
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


if __name__ == '__main__':
    main()
