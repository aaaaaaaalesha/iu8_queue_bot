# Copyright 2021 aaaaaaaalesha

import os
import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage


class UserQueue:
    """Implements a simple queue for users."""

    def __init__(self):
        self.__queue = asyncio.Queue()
        self.__current_msg_text = str()
        self.__size = 0

    def __len__(self):
        return self.__size

    async def push(self, callback: types.CallbackQuery) -> None:
        await self.__queue.put(item=callback)
        self.__size += 1

    async def pop(self):
        return await self.__queue.get()

    async def update_msg_text(self, msg_text: str) -> None:
        self.__current_msg_text = msg_text


# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize storage for FSM.
storage = MemoryStorage()

# Initialize bot and dispatcher
bot = Bot(os.getenv("TELE_API_TOKEN"))
dp = Dispatcher(bot, storage=storage)

# Initialize queue
queue = UserQueue()
