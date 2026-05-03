from database.database import Database
from database.model.Snippet import Snippet

"""Repository class responsible for handling any reads and writes to the snippets table"""
class SnippetsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_snippets(self, server_id: int) -> list[Snippet]:
        """Gets a list of all the server snippets"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT s.name, s.content, GROUP_CONCAT(sa.alias) AS aliases "
                "FROM snippets s LEFT JOIN snippets_alias sa "
                "ON s.id = sa.snippet_id "
                "WHERE s.server_id = ? "
                "GROUP BY s.id ORDER BY s.name",
                (str(server_id),)
            )
            rows = await cursor.fetchall()

            snippets: list[Snippet] = []
            for row in rows:
                snippet_name, snippet_content, aliases = row
                snippet_name = str(snippet_name)
                snippet_content = str(snippet_content)
                snippet_aliases: list[str] | None = str(aliases).split(",") if aliases else None

                snippet: Snippet = Snippet(snippet_name, snippet_content, snippet_aliases)
                snippets.append(snippet)

            return snippets

    async def get_snippet_content_by_name(self, server_id: int, name: str) -> str | None:
        """Gets a snippets content by its main name or alias. Returns None if no snippet by that name or alias exists"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT s.content "
                "FROM snippets s LEFT JOIN snippets_alias sa "
                "ON s.id = sa.snippet_id "
                "WHERE s.server_id = ? "
                "AND (s.name = ? OR sa.alias = ?) "
                "LIMIT 1",
                (str(server_id), name, name)
            )

            row = await cursor.fetchone()
            return str(row[0]) if row else None

    async def add_snippet_alias(self, server_id: int, snippet_name: str, snippet_alias: str) -> str:
        """Adds a snippet alias to a snippet
        Returns: A string representing the reason the snippet alias was not added (e.g. that name is already in use)
        or a string that describes a successful insert into the alias table"""
        async with self.db.get_write_connection() as conn:
            #check if a snippet name/alias already exists for this server
            cursor = await conn.execute(
                "SELECT EXISTS ("
                "SELECT 1 FROM snippets WHERE server_id = ? AND name = ? "
                "UNION "
                "SELECT 1 FROM snippets_alias sa "
                "JOIN snippets s ON s.id = sa.snippet_id "
                "WHERE s.server_id = ? AND sa.alias = ?"
                ")",
                (str(server_id), snippet_alias, str(server_id), snippet_alias)
            )
            row = await cursor.fetchone()

            if bool(row[0]):
                return "A snippet with this name or alias already exists"

            #get the primary key ID of the snippet with this snippet name
            cursor = await conn.execute(
                "SELECT s.id "
                "FROM snippets s "
                "WHERE s.server_id = ? "
                "AND s.name = ? ",
                (str(server_id), snippet_name)
            )

            snippet_id = await cursor.fetchone()
            if snippet_id is None:
                return "No snippet with this name exists"

            await conn.execute(
                "INSERT INTO snippets_alias (snippet_id, alias) "
                "VALUES (?,?)",
                (int(snippet_id[0]), snippet_alias)
            )
            await conn.commit()

            return f"Alias `{snippet_alias}` added successfully for snippet"

    async def remove_snippet_alias(self, server_id: int, snippet_alias: str) -> int:
        """Removes a snippet alias from a snippet
        Returns: an integer representing the number of snippet aliases removed"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM snippets_alias "
                "WHERE alias = ? "
                "AND snippet_id IN ( "
                "SELECT id FROM snippets WHERE server_id = ?"
                ")",
                (snippet_alias, str(server_id))
            )

            await conn.commit()
            return cursor.rowcount


    async def add_snippet(self, server_id: int, name: str, content: str) -> bool:
        """Adds a snippet for this server. If a snippet with this name or alias already exists for this server, it will do nothing
        Returns: true if the snippet was added, otherwise false"""
        async with self.db.get_write_connection() as conn:
            # check if a snippet name/alias already exists for this server
            cursor = await conn.execute(
                "SELECT EXISTS ("
                    "SELECT 1 FROM snippets WHERE server_id = ? AND name = ? "
                    "UNION "
                    "SELECT 1 FROM snippets_alias sa "
                    "JOIN snippets s ON s.id = sa.snippet_id "
                    "WHERE s.server_id = ? AND sa.alias = ?"
                ")",
                (str(server_id), name, str(server_id), name)
            )
            row = await cursor.fetchone()

            if bool(row[0]):
                return False

            await conn.execute(
                "INSERT INTO snippets (server_id, name, content) "
                "VALUES (?,?,?)",
                (str(server_id), name, content)
            )
            await conn.commit()

            return True

    async def update_snippet(self, server_id: int, name: str, content: str) -> int:
        """Updates a snippets content for this server.
        Returns: the number of snippet rows that were updated"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "UPDATE snippets SET content = ? WHERE server_id = ? AND name = ? ",
                (content, str(server_id), name)
            )
            await conn.commit()

            return cursor.rowcount

    async def delete_snippet(self, server_id: int, name: str) -> int:
        """Deletes a snippets for this server.
        Returns: the number of snippet rows that were deleted"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM snippets WHERE server_id = ? AND name = ? ",
                (str(server_id), name)
            )
            await conn.commit()

            return cursor.rowcount