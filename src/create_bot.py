import os
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

load_dotenv('.env')

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize storage for FSM.
storage = MemoryStorage()

# Initialize bot and dispatcher
bot = Bot(os.getenv('TELE_API_TOKEN'))
dp = Dispatcher(bot, storage=storage)
