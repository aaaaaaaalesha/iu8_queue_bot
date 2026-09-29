"""Texts of queue messages."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from queue_bot.models import Member

QUEUE_HEADER = "🆕 🅠🅤🅔🅤🅔 🆕"
# Telegram limit for a message text.
MAX_MESSAGE_LENGTH = 4096

_MEMBER_LINE = re.compile(r"^\d+\.\s(.+)$")


def render_queue(name: str, members: Sequence[Member]) -> str:
    lines = [QUEUE_HEADER, f"Очередь «{name}» запущена!"]
    lines.extend(f"{number}. {member.label}" for number, member in enumerate(members, start=1))
    text = "\n".join(lines)
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 1] + "…"
    return text


def parse_legacy_members(text: str) -> list[str]:
    """Extract member labels from a message rendered by the pre-v1 bot."""
    labels = []
    for line in text.split("\n")[2:]:
        match = _MEMBER_LINE.match(line.strip())
        if match:
            labels.append(match.group(1))
    return labels


def format_start(timestamp: int, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp, tz).strftime("%d.%m.%Y в %H:%M")
