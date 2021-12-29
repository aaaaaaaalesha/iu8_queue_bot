# Copyright 2021 aaaaaaaalesha

import sqlite3
from datetime import datetime

conn = sqlite3.connect('queue_bot.db')
cursor = conn.cursor()


def start_db() -> None:
    sql_script: str
    with open('db/init_db.sql', 'r') as sql_file:
        sql_script = sql_file.read()

    cursor.executescript(sql_script)
    conn.commit()

    if conn:
        print("Data base has been connected!")


def sql_get_queue_list(admin_id_: int) -> list:
    cursor.execute(
        "SELECT id, queue_name, start, chat_id, chat_title  FROM queues_list WHERE assignee_id = ?",
        (admin_id_,)
    )

    return cursor.fetchall()


def sql_get_chat_title(chat_id_: int) -> list:
    cursor.execute(
        "SELECT chat_title FROM chat WHERE chat_id = ?", (chat_id_,)
    )

    return cursor.fetchall()


def sql_get_managed_chats(admin_id_: int) -> list:
    cursor.execute(
        f"SELECT chat_id, chat_title FROM chat WHERE assignee_id = ?", (admin_id_,)
    )

    return cursor.fetchall()


async def sql_add_admin(admin_id_: int, user_name_: str) -> None:
    cursor.execute(
        "INSERT OR IGNORE INTO admin VALUES (?, ?)",
        (admin_id_, user_name_)
    )
    conn.commit()


async def sql_add_managed_chat(admin_id_: int, chat_id_: int, chat_title_: str) -> None:
    cursor.execute(
        "INSERT INTO chat ('assignee_id', 'chat_id', 'chat_title') VALUES (?, ?, ?)",
        (admin_id_, chat_id_, chat_title_)
    )
    conn.commit()


async def sql_delete_managed_chat(chat_id_: int) -> None:
    cursor.execute(
        "DELETE FROM chat WHERE chat_id = ?", (chat_id_,)
    )
    conn.commit()
    cursor.execute(
        "DELETE FROM queues_list WHERE chat_id = ?", (chat_id_,)
    )
    conn.commit()


async def sql_add_queue(admin_id_: int, queue_name_: str, start_dt: datetime, chat_id_: int, chat_title_: str) -> None:
    cursor.execute(
        "INSERT INTO queues_list ('assignee_id', 'queue_name', 'start', 'chat_id', 'chat_title') "
        "VALUES (?, ?, ?, ?, ?)", (admin_id_, queue_name_, start_dt, chat_id_, chat_title_)
    )
    conn.commit()


async def sql_delete_queue(id_: int) -> None:
    cursor.execute(
        "DELETE FROM queues_list WHERE id = ?", (id_,)
    )
    conn.commit()
