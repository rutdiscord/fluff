import asyncio
import logging
import os
import re
import sqlite3

import aiosqlite
from contextlib import asynccontextmanager

DB_NAME = "fluff_database.db"
READ_CONNECTION_POOL_SIZE = 3

# ^V     -> Starts with a capital V
# (\d+)  -> Capture group 1: The digits
# _+     -> One or more underscores
# (.+)   -> Capture group 2: The description
# \.sql$ -> Ends exactly with .sql
migration_file_pattern = re.compile(r"^V(\d+)_+(.+)\.sql$")

logger = logging.getLogger('discord')

"""Database class responsible for initializing the db schema and managing connection pools"""
class Database:
    def __init__(self):
        self.db_path: str = f"data/{DB_NAME}"
        self.read_conn_pool: asyncio.Queue[aiosqlite.Connection] | None = None
        self.write_conn: aiosqlite.Connection | None = None
        self.write_lock: asyncio.Lock | None = None

    async def init(self):
        self.read_conn_pool = asyncio.Queue(maxsize=READ_CONNECTION_POOL_SIZE)
        self.write_lock = asyncio.Lock()

        self.write_conn = await aiosqlite.connect(self.db_path)
        self.write_conn.row_factory = aiosqlite.Row
        await self._setup_wal(self.write_conn)
        await self._handle_schema_migrations(self.write_conn)

        for _ in range(READ_CONNECTION_POOL_SIZE):
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            await self._setup_wal(conn)
            await self.read_conn_pool.put(conn)

    async def close(self):
        """Close all database connections"""
        while not self.read_conn_pool.empty():
            conn = await self.read_conn_pool.get()
            await conn.close()

        if self.write_conn:
            await self.write_conn.close()

    @asynccontextmanager
    async def get_read_connection(self):
        """Context manager for borrowing a read connection"""
        conn = await self.read_conn_pool.get()
        try:
            yield conn
        finally:
            await self.read_conn_pool.put(conn)

    @asynccontextmanager
    async def get_write_connection(self):
        """Context manager for preventing multiple write connections"""
        async with self.write_lock:
            yield self.write_conn

    async def _setup_wal(self, conn: aiosqlite.Connection):
        """Helper method to apply standard pragmas for each connection"""
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.commit()

    async def _handle_schema_migrations(self, conn: aiosqlite.Connection):
        """Applies all valid schema migrations to the database. This is a useful feature as it will selectively
        apply each new sql file, in order, by its version number. Note that new sql files created that have a version
        number less than the max version in the migration schema history table will not be applied."""
        max_schema_version: int = await self._get_migration_schema_table_latest_version(conn)

        count_of_versions_applied = 0
        sorted_files = sorted(os.listdir("database/migration"), key=self._get_version_number)
        for filename in sorted_files:
            match = migration_file_pattern.match(filename)
            if match:
                if int(match.group(1)) > max_schema_version:
                    logger.info(f"applying version {match.group(1)}: {match.group(2).replace("_", " ")}")
                    with open(f"database/migration/{filename}", "r") as f:
                        try:
                            await conn.executescript(f.read())
                            await conn.execute("INSERT INTO migration_schema_history(version) VALUES(?)",
                                                          (int(match.group(1)),))
                            await conn.execute("PRAGMA optimize") #always run after any schema changes
                            await conn.commit()
                            count_of_versions_applied += 1
                        except sqlite3.Error as e:
                            await self.write_conn.rollback()
                            logger.error(f"Error applying version {match.group(1)}. Skipping all additional migrations")
                            raise e
        if count_of_versions_applied == 0:
            logger.info("No migrations applied")
        else:
            logger.info(f"Successfully applied {count_of_versions_applied} migrations")



    async def _get_migration_schema_table_latest_version(self, conn: aiosqlite.Connection) -> int:
        """Fetches and returns the latest schema version that has been applied to this database.
        If the migration schema table does not exist, then it is created first.

        Returns: the latest schema version applied"""
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migration_schema_history'"
        )
        row = await cursor.fetchone()

        if row:
            await cursor.execute("SELECT MAX(version) FROM migration_schema_history")
            version_row = await cursor.fetchone()

            current_version = version_row[0] if version_row and version_row[0] is not None else -1
            return current_version
        else:
            logger.info("Creating migration schema history table")
            await self._create_migration_schema_table(conn)
            return -1

    async def _create_migration_schema_table(self, conn: aiosqlite.Connection) -> None:
        """Creates the migration schema table"""
        with open(f"database/migration/migration_schema_history.sql", "r") as f:
            await conn.executescript(f.read())
            await conn.commit()

    def _get_version_number(self, filename):
        match = re.search(r"V(\d+)", filename)
        return int(match.group(1)) if match else 0