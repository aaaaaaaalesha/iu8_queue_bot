# Copyright 2021 aaaaaaaalesha

import sqlite3


def start_db() -> None:
    global conn, cur
    conn = sqlite3.connect('queue_bot.db')
    cur = conn.cursor()

    sql_script: str
    with open('db/init_db.sql', 'r') as sql_file:
        sql_script = sql_file.read()

    cur.executescript(sql_script)
    conn.commit()

    if conn:
        print("Data base has been connected!")
