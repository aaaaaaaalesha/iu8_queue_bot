"""Application settings loaded from environment variables (and optional `.env`)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    database_path: str
    timezone: ZoneInfo
    # Minimal pause between two consecutive edits of the same queue message.
    # Changes made during the pause are coalesced into a single edit.
    edit_interval: float
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        token = os.getenv("TELE_API_TOKEN") or os.getenv("BOT_TOKEN")
        if not token:
            raise RuntimeError("Environment variable TELE_API_TOKEN is not set")

        return cls(
            bot_token=token,
            database_path=os.getenv("DATABASE_PATH", "queue_bot.db"),
            timezone=ZoneInfo(os.getenv("TIMEZONE", "Europe/Moscow")),
            edit_interval=float(os.getenv("QUEUE_EDIT_INTERVAL", "1.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
