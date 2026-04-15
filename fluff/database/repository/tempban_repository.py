from database.database import Database
from database.model.TempBannedUser import TempBannedUser

"""Repository class responsible for handling any reads and writes to the tempban table"""
class TempBanRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_all_banned_users(self, server_id: int) -> list[tuple[int, int]]:
        """Fetches all banned users for this server from the tempban table, and returns their user ID and unban date, in epoch timestamp format"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT banned_user_id, date_to_unban FROM tempban WHERE server_id = ? ORDER BY date_to_unban ASC",
                (str(server_id),)
            )
            rows = await cursor.fetchall()

            return [(int(banned_user_id), int(date_to_unban)) for banned_user_id, date_to_unban in rows]

    async def get_banned_user_info(self, banned_user_id: int, server_id: int) -> TempBannedUser | None:
        """Fetches all info about a temp banned user for this server"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT banned_user_id, banned_by_id, reason, date_to_unban FROM tempban WHERE banned_user_id = ? AND server_id = ?",
                (str(banned_user_id), str(server_id))
            )
            row = await cursor.fetchone()

            if row is None:
                return None

            return TempBannedUser(int(row[0]), int(row[1]), str(row[2]), int(row[3]))

    async def get_expired_ban_users(self, current_timestamp: int) -> list[tuple[int, int]]:
        """Fetches all users and their associated server whose date_to_unban timestamp comes before or is equal to current_timestamp"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT banned_user_id, server_id FROM tempban WHERE date_to_unban <= ?",
                (current_timestamp,)
            )
            rows = await cursor.fetchall()

            return [(int(row[0]), int(row[1])) for row in rows]

    async def add_banned_user(self, banned_user_id: int, banned_by_id: int, server_id: int, reason: str, date_to_unban: int) -> None:
        """Adds the banned user and other important information to the tempban table"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "INSERT INTO tempban (banned_user_id, banned_by_id, server_id, reason, date_to_unban) VALUES (?, ?, ?, ?, ?)",
                (str(banned_user_id), str(banned_by_id), str(server_id), reason, date_to_unban)
            )
            await conn.commit()

    async def update_banned_user_date(self, banned_user_id: int, server_id: int, date_to_unban: int) -> int:
        """Updates the datetime for when the users tempban should be removed"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "UPDATE tempban SET date_to_unban = ? WHERE banned_user_id = ? AND server_id = ?",
                (date_to_unban, str(banned_user_id), str(server_id))
            )
            await conn.commit()
            return cursor.rowcount

    async def remove_banned_user(self, banned_user_id: int, server_id: int) -> int:
        """Removes the tempban for this user in this server, if an entry exists"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM tempban WHERE banned_user_id = ? AND server_id = ?",
                (str(banned_user_id), str(server_id))
            )
            await conn.commit()
            return cursor.rowcount