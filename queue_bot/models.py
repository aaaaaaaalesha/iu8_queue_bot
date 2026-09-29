from __future__ import annotations

import enum
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chat:
    chat_id: int
    title: str
    admin_id: int


@dataclass(frozen=True, slots=True)
class Queue:
    id: int
    admin_id: int
    chat_id: int
    chat_title: str
    name: str
    start_at: int  # Unix timestamp, UTC.
    message_id: int | None
    legacy_pending: bool

    @property
    def is_launched(self) -> bool:
        return self.message_id is not None


@dataclass(frozen=True, slots=True)
class Member:
    user_id: int | None
    first_name: str
    username: str | None

    @property
    def label(self) -> str:
        if self.username:
            return f"{self.first_name} (@{self.username})"
        return self.first_name


class OpStatus(enum.Enum):
    OK = enum.auto()
    ALREADY_IN = enum.auto()
    NO_QUEUERS = enum.auto()
    ONE_QUEUER = enum.auto()
    NOT_QUEUER = enum.auto()
    NO_AFTER = enum.auto()
    QUEUE_NOT_FOUND = enum.auto()
