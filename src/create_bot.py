# Copyright 2021 aaaaaaaalesha

import os
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize storage for FSM.
storage = MemoryStorage()

# Initialize bot and dispatcher
bot = Bot(os.getenv("TELE_API_TOKEN"))
dp = Dispatcher(bot, storage=storage)
