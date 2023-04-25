import os
import datetime as dt

import aiosqlite


class Database:
    def __init__(self):
        self.conn: aiosqlite.Connection | None = None
        self.database = os.getenv('DATABASE', default='queue_bot.db')
        self.create_tables()
        self.connect()

    async def connect(self):
        self.conn = await aiosqlite.connect(self.database)

    async def create_tables(self):
        async with aiosqlite.connect(self.database) as conn:
            sql_file_path = (
                'db/init_db.sql'
                if bool(os.getenv('DEBUG', 'True'))
                else '/app/src/db/init_db.sql'
            )
            with open(sql_file_path, 'r') as sql_file:
                sql_script = sql_file.read()

            await conn.executescript(sql_script)
            await conn.commit()

    async def get_queue_list(self, admin_id_: int) -> list:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "SELECT id, queue_name, start, chat_id, chat_title  "
                "FROM queue "
                "WHERE assignee_id = ?",
                (admin_id_,),
        ) as cursor:
            return await cursor.fetchall()

    async def get_queue_from_list(self, id_: int) -> tuple:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "SELECT *  "
                "FROM queue "
                "WHERE id = ?",
                (id_,),
        ) as cursor:
            return await cursor.fetchone()

    async def post_queue(self, queue_id_: int, msg_id_: int, msg_text: str):
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "UPDATE queue "
                "SET msg_id = ?, msg_text = ?"
                "WHERE id = ?",
                (msg_id_, msg_text, queue_id_),
        ):
            await self.conn.commit()

    async def update_queue_text(self, msg_id_: int, msg_text: str):
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "UPDATE queue "
                "SET msg_text = ?"
                "WHERE msg_id = ?",
                (msg_text, msg_id_,),
        ):
            await self.conn.commit()

    async def get_queue_text(self, msg_id_: int) -> str:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "SELECT msg_text "
                "FROM queue "
                "WHERE msg_id = ?",
                (msg_id_,),
        ) as cursor:
            return await cursor.fetchone()

    async def get_chat_title(self, chat_id_: int) -> tuple:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "SELECT chat_title "
                "FROM chat "
                "WHERE chat_id = ?",
                (chat_id_,),
        ) as cursor:
            return await cursor.fetchone()

    async def get_managed_chats(self, admin_id_: int) -> list:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                f"SELECT chat_id, chat_title "
                f"FROM chat "
                f"WHERE assignee_id = ?",
                (admin_id_,),
        ) as cursor:
            return await cursor.fetchall()

    async def add_admin(self, admin_id_: int, user_name_: str) -> None:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "INSERT OR IGNORE INTO admin "
                "VALUES (?, ?)",
                (admin_id_, user_name_),
        ):
            await self.conn.commit()

    async def add_managed_chat(
            self,
            admin_id_: int,
            chat_id_: int,
            chat_title_: str
    ) -> None:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "INSERT INTO chat "
                "('assignee_id', 'chat_id', 'chat_title') "
                "VALUES (?, ?, ?)",
                (admin_id_, chat_id_, chat_title_),
        ):
            await self.conn.commit()

    async def delete_managed_chat(self, chat_id_: int) -> None:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "DELETE FROM chat "
                "WHERE chat_id = ?",
                (chat_id_,),
        ):
            await self.conn.commit()

        async with self.conn.execute(
                "DELETE FROM queue "
                "WHERE chat_id = ?",
                (chat_id_,),
        ):
            await self.conn.commit()

    async def add_queue(
            self,
            admin_id_: int,
            queue_name_: str,
            start_dt: dt.datetime,
            chat_id_: int,
            chat_title_: str,
    ) -> tuple:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "INSERT INTO queue "
                "('assignee_id', 'queue_name', 'start', 'chat_id', 'chat_title') "
                "VALUES (?, ?, ?, ?, ?)",
                (admin_id_, queue_name_, start_dt, chat_id_, chat_title_),
        ):
            await self.conn.commit()

        async with self.conn.execute(
                "SELECT id "
                "FROM queue "
                "WHERE assignee_id = ? AND queue_name = ? AND chat_id = ?",
                (admin_id_, queue_name_, chat_id_),
        ) as cursor:
            return await cursor.fetchone()

    async def delete_queue(self, id_: int) -> tuple[int, int]:
        if self.conn is None:
            await self.connect()

        async with self.conn.execute(
                "SELECT chat_id, msg_id "
                "FROM queue "
                "WHERE id = ?",
                (id_,),
        ) as cursor:
            chat_id, msg_id = await cursor.fetchone()

        async with self.conn.execute(
                "DELETE FROM queue "
                "WHERE id = ?",
                (id_,),
        ):
            await self.conn.commit()

        return chat_id, msg_id
