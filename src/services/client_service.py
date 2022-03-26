# Copyright 2021 aaaaaaaalesha
import asyncio
from typing import Tuple

import aiogram
from aiogram import types, exceptions

from src.keyboards.client_kb import queue_inl_kb

STATUS_OK = 0
STATUS_ALREADY_IN = 1
STATUS_NO_QUEUERS = 2
STATUS_ONE_QUEUER = 3
STATUS_NOT_QUEUER = 4
STATUS_NO_AFTER = 5


async def add_queuers_text(queue_):
    callback: types.CallbackQuery = await queue_.pop()
    msg_lines = callback.message.text.split('\n')

    await add_queuer(msg_lines, callback)

    lock = asyncio.Lock()
    await asyncio.sleep(1.)

    while queue_:
        callback = await queue_.pop()

        async with lock:
            await add_queuer(msg_lines, callback)

    new_text = '\n'.join(msg_lines)
    try:
        with lock:
            await callback.message.edit_text(text=new_text, reply_markup=queue_inl_kb)
    except exceptions.BadRequest:
        pass


async def add_queuer(msg_lines_: list, callback: types.CallbackQuery) -> None:
    user = callback.from_user
    match_str = f"{user.first_name} (@{user.username})"

    for i in range(2, len(msg_lines_)):
        if msg_lines_[i].rfind(match_str) != -1:
            await callback.answer("❕ Вы уже в очереди.")
            return

    msg_lines_.append(f"{len(msg_lines_) - 1}. {match_str}")


# async def add_queuer_text(old_text: str, first_name: str, queuer_username: str) -> Tuple[str, int]:
#     """
#     Changes old_text, adding here a new queuer name.
#     @param old_text: str repr of old message;
#     @param first_name: new queuer first name;
#     @param queuer_username: new queuer username;
#     @return: tuple with new message text and code status.
#     """
#     lines = old_text.split('\n')
#
#     match_str = f"{first_name} (@{queuer_username})"
#     for i in range(2, len(lines)):
#         if lines[i].rfind(match_str) != -1:
#             return str(), STATUS_ALREADY_IN
#
#     lines.append(
#         f"{len(lines) - 1}. {match_str})"
#     )
#
#     return '\n'.join(lines), STATUS_OK


async def delete_queuer_text(old_text: str, first_name: str, queuer_username: str) -> Tuple[str, int]:
    lines = old_text.split('\n')
    if len(lines) == 2:
        return str(), STATUS_NO_QUEUERS
    else:
        index_changer = -1
        match_str = f"{first_name} (@{queuer_username})"
        for i in range(2, len(lines)):
            if lines[i].rfind(match_str) != -1:
                lines.pop(i)
                index_changer = i
                break

        if index_changer == -1:
            return str(), STATUS_NOT_QUEUER

        # If queuer is last in queue.
        if index_changer == len(lines):
            return '\n'.join(lines), STATUS_OK

        for i in range(index_changer, len(lines)):
            lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    return '\n'.join(lines), STATUS_OK


async def skip_ahead(old_text: str, first_name: str, queuer_username: str) -> Tuple[str, int]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), STATUS_NO_QUEUERS

    if len(lines) == 3:
        return str(), STATUS_ONE_QUEUER

    index_changer = -1
    match_str = f"{first_name} (@{queuer_username})"
    for i in range(2, len(lines)):
        if lines[i].rfind(match_str) != -1:
            if i == len(lines) - 1:
                return str(), STATUS_NO_AFTER
            index_changer = i
            break

    if index_changer == -1:
        return str(), STATUS_NOT_QUEUER

    lines[index_changer] = lines[index_changer].replace(f"{index_changer - 1}. ", f"{index_changer}. ", 1)
    lines[index_changer + 1] = lines[index_changer + 1].replace(f"{index_changer}. ", f"{index_changer - 1}. ", 1)

    # Swap.
    lines[index_changer], lines[index_changer + 1] = lines[index_changer + 1], lines[index_changer]

    return '\n'.join(lines), STATUS_OK


async def push_tail(old_text: str, first_name: str, username: str) -> Tuple[str, int]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), STATUS_NO_QUEUERS

    if len(lines) == 3:
        return str(), STATUS_ONE_QUEUER

    index_changer = -1
    del_queuer = str()

    match_str = f"{first_name} (@{username})"
    for i in range(2, len(lines)):
        if lines[i].rfind(match_str) != -1:
            if i + 1 == len(lines):
                return str(), STATUS_NO_AFTER
            del_queuer = lines.pop(i)
            index_changer = i
            break

    if index_changer == -1:
        return str(), STATUS_NOT_QUEUER

    for i in range(index_changer, len(lines)):
        lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    lines.append(del_queuer.replace(f"{index_changer - 1}. ", f"{len(lines) - 1}. ", 1))

    return '\n'.join(lines), STATUS_OK
