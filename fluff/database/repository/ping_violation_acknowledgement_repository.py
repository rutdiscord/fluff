from database.database import Database

"""Repository class responsible for handling any reads and writes to the ping_violation_acknowledgement table"""
class PingViolationAcknowledgementRepository:
    def __init__(self, db: Database):
        self.db = db

    async def has_user_acknowledged(self, server_id: int, user_id: int) -> bool:
        """Check if the user has acknowledged the ping violation agreement

        Returns:
            true if user has previously accepted the acknowledgement, false otherwise.
        """
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT EXISTS(SELECT * FROM ping_violation_acknowledgement WHERE server_id = ? AND user_id = ?)",
                (str(server_id), str(user_id))
            )
            row = await cursor.fetchone()
            return bool(row[0])

    async def add_user_acknowledgement(self, server_id: int, user_id: int):
        """Adds the server ID and user ID combination to the ping_violation_acknowledgement table"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO ping_violation_acknowledgement (server_id, user_id) "
                "VALUES (?, ?)",
                (str(server_id), str(user_id))
            )
            await conn.commit()
