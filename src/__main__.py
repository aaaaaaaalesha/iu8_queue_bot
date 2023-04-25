from aiogram import executor

from src.loader import logger, bot, dp, db


async def on_startup(_) -> None:
    await db.connect()
    await db.create_tables()
    logger.info('Bot now is online!')


async def on_startup_wrapper(dp) -> None:
    await on_startup(dp)


if __name__ == '__main__':
    executor.start_polling(
        dispatcher=dp,
        on_startup=lambda dp: on_startup_wrapper(dp),
        skip_updates=True,
    )
