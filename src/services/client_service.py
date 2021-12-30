# Copyright 2021 aaaaaaaalesha

from typing import Tuple

STATUS_OK = 0
STATUS_NO_QUEUERS = 1
STATUS_ONE_QUEUER = 2
STATUS_NOT_QUEUER = 3
STATUS_NO_AFTER = 4


async def add_queuer_text(old_text: str, queuer_name: str, queuer_username: str) -> str:
    lines = old_text.split('\n')
    number: int
    if len(lines) == 2:
        number = 1
    else:
        last_line = lines[-1]
        number = int(last_line[:last_line.find('. ')]) + 1

    lines.append(
        f"{number}. {queuer_name} (@{queuer_username})"
    )

    return '\n'.join(lines)


async def delete_queuer_text(old_text: str, queuer_username: str) -> str:
    lines = old_text.split('\n')
    if len(lines) <= 2:
        return old_text
    else:
        index_changer = -1
        for i in range(2, len(lines)):
            if lines[i].find(f"@{queuer_username}") != -1:
                lines.pop(i)
                index_changer = i
                break

        if index_changer == -1:
            return old_text

        # If queuer is last in queue.
        if index_changer == len(lines):
            return '\n'.join(lines)

        for i in range(index_changer, len(lines)):
            lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    return '\n'.join(lines)


async def skip_ahead(old_text: str, username: str) -> Tuple[str, int]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), STATUS_NO_QUEUERS

    if len(lines) == 3:
        return str(), STATUS_ONE_QUEUER

    index_changer = -1
    for i in range(2, len(lines)):
        if lines[i].find(f"@{username}") != -1:
            if i + 1 == len(lines):
                return str(), STATUS_NO_AFTER
            index_changer = i
            break

    if index_changer == -1:
        return str(), STATUS_NOT_QUEUER

    lines[index_changer] = lines[index_changer].replace(f"{index_changer - 1}. ", f"{index_changer}. ", 1)
    lines[index_changer + 1] = lines[index_changer + 1].replace(f"{index_changer}. ", f"{index_changer + 1}. ", 1)

    # Swap.
    lines[index_changer], lines[index_changer + 1] = lines[index_changer + 1], lines[index_changer]

    return '\n'.join(lines), STATUS_OK


async def push_tail(old_text: str, username: str) -> Tuple[str, int]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), STATUS_NO_QUEUERS

    if len(lines) == 3:
        return str(), STATUS_ONE_QUEUER

    index_changer = -1
    del_queuer = str()
    for i in range(3, len(lines)):
        if lines[i].find(f"@{username}") != -1:
            if i + 1 == len(lines):
                return str(), STATUS_NO_AFTER
            del_queuer = lines.pop(i)
            index_changer = i
            break

    if index_changer == -1:
        return str(), STATUS_NOT_QUEUER

    for i in range(index_changer, len(lines)):
        lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    lines.append(del_queuer.replace(f"{index_changer - 1}. ", f"{len(lines)}. ", 1))

    return '\n'.join(lines), STATUS_OK
