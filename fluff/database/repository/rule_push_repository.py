from database.database import Database

"""Repository class responsible for handling any reads and writes to the various rule push tables"""
class RulePushRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create_rulepush_session_keywords(self, session_id: int, keywords: list[str]) -> int:
        """Adds all keywords for the given session.
        Returns: the session id"""
        async with self.db.get_write_connection() as conn:
            await conn.executemany(
                "INSERT INTO rule_push_session_keyword (session_id, keyword) VALUES (?, ?)",
                [(session_id, keyword) for keyword in keywords]
            )
            await conn.commit()
            return session_id

    async def mark_keyword_found_and_count(self, session_id: int, keyword: str) -> tuple[int, int, int]:
        """Marks a keyword found (if not already) and returns total words found
        Returns: (updated, found, total) where updated is 1 if this call actually performed an update, found
        is the total number of keywords that the user has found, and total is the total number of keywords
        that the user has to find before being released"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "UPDATE rule_push_session_keyword SET found = 1 "
                "WHERE session_id = ? AND keyword = ? AND found = 0",
                (session_id, keyword),
            )
            updated = cursor.rowcount
            cursor = await conn.execute(
                "SELECT COALESCE(SUM(found), 0), COUNT(*) "
                "FROM rule_push_session_keyword WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
            await conn.commit()
            return updated, int(row[0]), int(row[1])

    async def get_keywords(self, server_id: int) -> list[str]:
        """Gets all keywords for a server"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT keyword "
                "FROM rule_push_keyword "
                "WHERE server_id = ? "
                "ORDER BY keyword ASC",
                (str(server_id),)
            )

            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_keywords_for_session(self, session_id: int) -> list[str]:
        """Fetches the keywords for this session
        Returns: a list of keywords"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT keyword "
                "FROM rule_push_session_keyword "
                "WHERE session_id = ? "
                "ORDER BY keyword ASC",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def add_keywords(self, server_id: int, keywords_list: list[str]) -> int:
        """Adds a list of keywords to this server"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.executemany(
                "INSERT OR IGNORE INTO rule_push_keyword (server_id, keyword) "
                "VALUES (?, ?)",
                [(str(server_id), keyword) for keyword in keywords_list]
            )
            await conn.commit()

            return cursor.rowcount

    async def delete_keywords(self, server_id: int, keywords_list: list[str]) -> int:
        """Deletes a list of keywords from this server"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.executemany(
                "DELETE FROM rule_push_keyword WHERE server_id = ? AND keyword = ?",
                [(str(server_id), keyword) for keyword in keywords_list]
            )
            await conn.commit()

            return cursor.rowcount