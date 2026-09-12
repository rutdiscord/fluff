import time

from database.database import Database
from database.model.StickiedPin import StickiedPin
from database.model.StickyMessage import StickyEntry

"""Repository class responsible for handling any reads and writes to the stickied_pins table"""
class StickiedPinsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_all_stickied_pins(self) -> list[StickiedPin]:
        """Gets every stickied pin from the stickied_pins table.

        Returns:
        list of stickied pins for this server
        """
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT channel_id, message_id, date_added FROM stickied_pins ORDER BY date_added DESC"
            )
            rows = await cursor.fetchall()

        stickied_pins: list[StickiedPin] = []
        for row in rows:
            channel_id, message_id, date_added = row
            stickied_pins.append(StickiedPin(channel_id=int(channel_id), message_id=int(message_id), date_added=int(date_added)))

        return stickied_pins

    async def create_stickied_pin(self, channel_id: int, message_id: int) -> bool:
        """Creates a stickied pin in the stickied pin table.
        Returns: true if the item was added, false otherwise"""
        async with self.db.get_write_connection() as conn:
            created_at = int(time.time())
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO stickied_pins (channel_id, message_id, date_added) "
                "VALUES (?,?,?)",
                (str(channel_id), str(message_id), created_at)
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return False

            return True

    async def delete_stickied_pin(self, channel_id: int, message_id: int) -> bool:
        """Deletes a stickied pin from the stickied pin table.
        Returns: true if the item was deleted, false otherwise"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM stickied_pins WHERE channel_id = ? and message_id = ? ",
                (str(channel_id), str(message_id))
            )
            await conn.commit()

            if cursor.rowcount == 0:
                return False

            return True
