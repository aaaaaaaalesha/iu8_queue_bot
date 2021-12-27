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
        f"SELECT queue_name, start FROM queues_list WHERE assignee_id = {admin_id_}"
    )

    return cursor.fetchall()


async def sql_add_admin(admin_id_: int, user_name_: str) -> None:
    cursor.execute(
        "INSERT INTO admin VALUES (?, ?)",
        (admin_id_, user_name_)
    )
    conn.commit()


async def sql_add_queue(assignee_id_: int, queue_name_: str, start_dt: datetime):
    cursor.execute(
        "INSERT INTO queues_list ('assignee_id', 'queue_name', 'start') VALUES (?, ?, ?)",
        (assignee_id_, queue_name_, start_dt)
    )
    conn.commit()
