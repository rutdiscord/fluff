from database.database import Database

"""Repository class responsible for handling any reads and writes to the starboard_channel_blacklist table"""
class StarboardChannelBlacklistRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_blacklisted_channels(self) -> list[int]:
        """Returns a list of channel IDs blacklisted for starboard."""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT channel_id FROM starboard_channel_blacklist"
            )
            rows = await cursor.fetchall()

            return [int(row[0]) for row in rows]

    async def is_channel_blacklisted(self, channel_id: int) -> bool:
        """Returns whether this channel is blacklisted from sending messages to starboard queue."""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM starboard_channel_blacklist WHERE channel_id = ?"
                ")",
                (str(channel_id),)
            )
            row = await cursor.fetchone()

            return bool(row[0])

    async def add_channel_to_blacklist(self, channel_id: int) -> bool:
        """Adds a channel ID to the starboard queue blacklist.
        Returns: true if entry was created, false if not (meaning it was already blacklisted)."""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO starboard_channel_blacklist (channel_id) "
                "VALUES (?)",
                (str(channel_id),)
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return False

            return True

    async def remove_channel_from_blacklist(self, channel_id: int) -> bool:
        """Removes a channel ID from the starboard queue blacklist.
        Returns: true if entry was removed, false if not (meaning it was already not in the blacklist)."""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM starboard_channel_blacklist WHERE channel_id = ?",
                (str(channel_id),)
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return False

            return True