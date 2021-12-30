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
