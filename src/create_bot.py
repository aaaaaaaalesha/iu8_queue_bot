# Copyright 2021 aaaaaaaalesha

import os
import logging

from aiogram import Bot, Dispatcher

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(os.getenv("TELE_API_TOKEN"))
dp = Dispatcher(bot)
