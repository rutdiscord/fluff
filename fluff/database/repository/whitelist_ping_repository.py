from database.database import Database

"""Repository class responsible for handling any reads and writes to the whitelist_ping table"""
class WhitelistPingRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_whitelisted_users(self, user_id: int) -> list[int]:
        """Gets a list of user ID's that are in this users whitelist"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT whitelisted_user_id FROM whitelist_ping WHERE user_id = ?",
                (str(user_id),)
            )
            rows = await cursor.fetchall()

            return [int(row[0]) for row in rows]


    async def is_user_in_whitelist(self, pinged_user_id: int, pinged_by_id: int) -> bool:
        """Determines if the pinged_by user is in the pinged user's whitelist.

        Returns:
        true if the pinged_by user is in the pinged user's whitelist, false otherwise.
        """
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT EXISTS(SELECT * FROM whitelist_ping WHERE user_id = ? AND whitelisted_user_id = ?)",
                (str(pinged_user_id), str(pinged_by_id))
            )
            row = await cursor.fetchone()
            return bool(row[0])

    async def add_whitelisted_users(self, user_id: int, users_to_whitelist: list[int]) -> None:
        """Adds the list of user ID's to the users whitelist"""
        async with self.db.get_write_connection() as conn:
            for user_id_to_whitelist in users_to_whitelist:
                await conn.execute(
                    "INSERT INTO whitelist_ping (user_id, whitelisted_user_id) "
                    "VALUES (?,?)",
                    (str(user_id), str(user_id_to_whitelist))
                )
            await conn.commit()

    async def remove_whitelisted_users(self, user_id: int, users_to_remove: list[int]) -> int:
        """removes the list of user ID's from the users whitelist

        Returns: the number of users removed from the whitelist table for this user"""
        async with self.db.get_write_connection() as conn:
            placeholders = ",".join("?" * len(users_to_remove))
            cursor = await conn.execute(
                f"DELETE FROM whitelist_ping WHERE user_id = ? AND whitelisted_user_id IN ({placeholders})",
                (str(user_id), *[str(uid) for uid in users_to_remove])
            )
            await conn.commit()
            return cursor.rowcount