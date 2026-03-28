import asyncio

import aiosqlite
from contextlib import asynccontextmanager

DB_NAME = "fluff_database.db"
SCHEMA_NAME = "fluff_schema.sql"
READ_CONNECTION_POOL_SIZE = 3

"""Database class responsible for initializing the db schema and managing connection pools"""
class Database:
    def __init__(self):
        self.db_path: str = f"data/{DB_NAME}"
        self.schema_path: str = f"database/{SCHEMA_NAME}"
        self.read_conn_pool: asyncio.Queue[aiosqlite.Connection] | None = None
        self.write_conn: aiosqlite.Connection | None = None
        self.write_lock: asyncio.Lock | None = None

    async def init(self):
        self.read_conn_pool = asyncio.Queue(maxsize=READ_CONNECTION_POOL_SIZE)
        self.write_lock = asyncio.Lock()

        self.write_conn = await aiosqlite.connect(self.db_path)
        self.write_conn.row_factory = aiosqlite.Row
        await self._setup_wal(self.write_conn)
        with open(self.schema_path, "r") as f:
            await self.write_conn.executescript(f.read())
            await self.write_conn.commit()

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
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.commit()
