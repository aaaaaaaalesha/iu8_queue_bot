"""Это всё нужно менять нахер..."""

from enum import StrEnum


class QueueStatus(StrEnum):
    OK = '👍'
    EXISTS = '❕ Вы уже в очереди'
    EMPTY = '❕ В очереди ещё нет участников'
    ONE_QUEUER = '❕ В очереди только один участник'
    NOT_QUEUER = '❕ Вы ещё не участник очереди'
    NO_AFTER = '❕ Вы крайний в очереди'


async def add_queuer_text(old_text: str, first_name: str, username: str) -> tuple[str, QueueStatus]:
    lines = old_text.split('\n')
    match_str = f"{first_name} (@{username})"
    for i in range(2, len(lines)):
        if lines[i].rfind(match_str) != -1:
            return str(), QueueStatus.EXISTS

    lines.append(f"{len(lines) - 1}. {match_str}")

    return '\n'.join(lines), QueueStatus.OK


async def delete_queuer_text(old_text: str, first_name: str, username: str) -> tuple[str, QueueStatus]:
    lines = old_text.split('\n')

    match_str = f"{first_name} (@{username})"
    if len(lines) == 2:
        return str(), QueueStatus.EMPTY
    else:
        index_changer = -1
        for i in range(2, len(lines)):
            if lines[i].rfind(match_str) != -1:
                lines.pop(i)
                index_changer = i
                break

        if index_changer == -1:
            return str(), QueueStatus.NOT_QUEUER

        # If queuer is last in queue.
        if index_changer == len(lines):
            return '\n'.join(lines), QueueStatus.OK

        for i in range(index_changer, len(lines)):
            lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    return '\n'.join(lines), QueueStatus.OK


async def skip_ahead(old_text: str, first_name: str, username: str) -> tuple[str, QueueStatus]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), QueueStatus.EMPTY

    if len(lines) == 3:
        return str(), QueueStatus.ONE_QUEUER

    index_changer = -1
    match_str = f"{first_name} (@{username})"
    for i in range(2, len(lines)):
        if lines[i].rfind(match_str) != -1:
            if i == len(lines) - 1:
                return str(), QueueStatus.NO_AFTER
            index_changer = i
            break

    if index_changer == -1:
        return str(), QueueStatus.NOT_QUEUER

    lines[index_changer] = lines[index_changer].replace(f"{index_changer - 1}. ", f"{index_changer}. ", 1)
    lines[index_changer + 1] = lines[index_changer + 1].replace(f"{index_changer}. ", f"{index_changer - 1}. ", 1)

    # Swap.
    lines[index_changer], lines[index_changer + 1] = lines[index_changer + 1], lines[index_changer]

    return '\n'.join(lines), QueueStatus.OK


async def push_tail(old_text: str, first_name: str, username: str) -> tuple[str, QueueStatus]:
    lines = old_text.split('\n')

    if len(lines) == 2:
        return str(), QueueStatus.EMPTY

    if len(lines) == 3:
        return str(), QueueStatus.ONE_QUEUER

    index_changer = -1
    del_queuer = str()

    match_str = f"{first_name} (@{username})"
    for i in range(2, len(lines)):
        if lines[i].rfind(match_str) != -1:
            if i + 1 == len(lines):
                return str(), QueueStatus.NO_AFTER
            del_queuer = lines.pop(i)
            index_changer = i
            break

    if index_changer == -1:
        return str(), QueueStatus.NOT_QUEUER

    for i in range(index_changer, len(lines)):
        lines[i] = lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    lines.append(del_queuer.replace(f"{index_changer - 1}. ", f"{len(lines) - 1}. ", 1))

    return '\n'.join(lines), QueueStatus.OK
