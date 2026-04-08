
from database.database import Database
from database.model.StickyMessage import StickyEntry

"""Repository class responsible for handling any reads and writes to the sticky_message table"""
class StickyMessageRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_all_sticky_messages(self) -> dict[int, dict[int, StickyEntry]]:
        """Gets every sticky message from the sticky message table.

        Returns:
        dict[int, dict[int, StickyEntry]]: A nested dictionary where the outer key is the
        server (guild) ID, the inner key is the channel ID, and the value is the
        StickyEntry containing the message content and last message metadata.
        """
        sticky_messages = {}
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT server_id, channel_id, message, last_message_id FROM sticky_message"
            )
            rows = await cursor.fetchall()

        for row in rows:
            server_id, channel_id, message, last_message_id = row
            server_id = int(server_id)
            channel_id = int(channel_id)
            if last_message_id is not None:
                last_message_id = int(last_message_id)

            if server_id not in sticky_messages:
                sticky_messages[int(server_id)] = {}

            sticky_messages[server_id][channel_id] = StickyEntry(message, last_message_id)

        return sticky_messages

    async def create_sticky_message(self, server_id: int, channel_id: int, message: str) -> tuple[int, int]:
        """Creates a sticky message in the sticky message table.
        Returns: the server_id + channel_id of the newly created sticky message row"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "INSERT INTO sticky_message (server_id, channel_id, message, last_message_id) "
                "VALUES (?,?,?,?)",
                (str(server_id), str(channel_id), message, None)
            )
            await conn.commit()

            return server_id, channel_id

    async def update_sticky_message_content(self, server_id: int, channel_id: int, message: str) -> None:
        """Updates an existing sticky message's message column."""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "UPDATE sticky_message SET message = ? WHERE server_id = ? AND channel_id = ?",
                (message, str(server_id), str(channel_id))
            )
            await conn.commit()

    async def update_sticky_message_sent_id(self, server_id: int, channel_id: int, last_message_id: int) -> None:
        """Updates an existing sticky message's last_message_id column."""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "UPDATE sticky_message SET last_message_id = ? WHERE server_id = ? AND channel_id = ?",
                (str(last_message_id), str(server_id), str(channel_id))
            )
            await conn.commit()

    async def delete_sticky_message(self, server_id: int, channel_id: int) -> None:
        """Deletes an existing sticky message in the sticky message table."""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "DELETE FROM sticky_message WHERE server_id = ? AND channel_id = ?",
                (str(server_id), str(channel_id))
            )
            await conn.commit()
