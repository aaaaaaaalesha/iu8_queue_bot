# Copyright 2021 aaaaaaaalesha


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
    if len(lines) == 2:
        return old_text
    else:
        index_changer = -1
        for i in range(len(lines)):
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
            lines[i].replace(f"{i}. ", f"{i - 1}. ", 1)

    return '\n'.join(lines)
