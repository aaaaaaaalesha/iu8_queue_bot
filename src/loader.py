import os
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from db.sqlite_db import Database

load_dotenv('.env')

# Настройка логирования.
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# Инициализация бота, диспетчера, бд.
bot = Bot(token=os.getenv('TELE_API_TOKEN'))
dp = Dispatcher(bot, storage=MemoryStorage())
db = Database()
