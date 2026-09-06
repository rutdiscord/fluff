from database.database import Database
from database.model.StarboardQueue import StarboardQueue
from model.StarboardQueueStatus import StarboardQueueStatus

"""Repository class responsible for handling any reads and writes to the whitelist_ping table"""
class StarboardQueueRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_starboard_queue_entry_by_id(self, message_id: int) -> StarboardQueue | None:
        """Fetches Starboard Queue entry by message_id, if it exists"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT message_id, channel_id, queue_message_id, starboard_message_id, status FROM starboard_queue WHERE message_id = ?",
                (str(message_id),)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            queue_message_id = row["queue_message_id"]
            starboard_message_id = row["starboard_message_id"]
            return StarboardQueue(
                message_id=int(row["message_id"]),
                channel_id=int(row["channel_id"]),
                queue_message_id=int(queue_message_id) if queue_message_id is not None else None,
                starboard_message_id=int(starboard_message_id) if starboard_message_id is not None else None,
                status=StarboardQueueStatus(row["status"])
            )

    async def get_starboard_queue_entry_by_queue_message_id(self, queue_message_id: int) -> StarboardQueue | None:
        """Fetches Starboard Queue entry by queue_message_id, if it exists"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT message_id, channel_id, queue_message_id, starboard_message_id, status FROM starboard_queue WHERE queue_message_id = ?",
                (str(queue_message_id),)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            queue_message_id = row["queue_message_id"]
            starboard_message_id = row["starboard_message_id"]
            return StarboardQueue(
                message_id=int(row["message_id"]),
                channel_id=int(row["channel_id"]),
                queue_message_id=int(queue_message_id) if queue_message_id is not None else None,
                starboard_message_id=int(starboard_message_id) if starboard_message_id is not None else None,
                status=StarboardQueueStatus(row["status"])
            )

    async def add_starboard_queue_entry(self, message_id: int, channel_id: int) -> StarboardQueue | None:
        """Creates a starboard queue entry, if an entry doesn't already exist for this message.
        Returns: StarboardQueue entity if we successfully created a new entry, None otherwise"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO starboard_queue (message_id, channel_id, status) "
                "VALUES (?,?,?)",
                (str(message_id), str(channel_id), StarboardQueueStatus.CREATED.value)
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return None

            return StarboardQueue(
                message_id=int(message_id),
                channel_id=int(channel_id),
                queue_message_id=None,
                starboard_message_id=None,
                status=StarboardQueueStatus.CREATED
            )

    async def update_queue_message_id(self, message_id: int, queue_message_id: int) -> None:
        """Updates an existing starboard queue entry with the ID of the message in the queue channel"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "UPDATE starboard_queue SET queue_message_id = ? WHERE message_id = ?",
                (str(queue_message_id), str(message_id))
            )
            await conn.commit()

    async def update_starboard_message_id(self, message_id: int, starboard_message_id: int) -> None:
        """Updates an existing starboard entry with the ID of the message in the public starboard channel"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "UPDATE starboard_queue SET starboard_message_id = ? WHERE message_id = ?",
                (str(starboard_message_id), str(message_id))
            )
            await conn.commit()

    async def update_status(self, message_id: int, status: StarboardQueueStatus) -> bool:
        """Updates the status of an existing starboard queue entry, if it exists
        Returns: boolean representing whether the entry was successfully updated"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "UPDATE starboard_queue SET status = ? WHERE message_id = ? AND status NOT IN ('ACCEPTED', 'REJECTED')",
                (status.value, str(message_id))
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return False

            return True