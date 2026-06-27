from database.database import Database
from database.model.Rule import Rule

"""Repository class responsible for handling any reads and writes to the rule table"""
class RuleRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_rules(self, server_id: int) -> list[Rule]:
        """Fetches all rules for this server
        Returns: a list of Rules, containing the rule number, title, and content of each rule"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rule_number, title, content "
                "FROM rule "
                "WHERE server_id = ?",
                (str(server_id),)
            )
            rows = await cursor.fetchall()

            server_rules: list[Rule] = []
            for row in rows:
                rule_number, title, content = row
                rule_number = int(rule_number)
                server_rules.append(Rule(rule_number, title, content))

            return server_rules

    async def get_rule_by_number(self, server_id: int, rule_num_to_fetch: int) -> Rule | None:
        """Fetches a rule for this server by its rule number
        Returns: a Rule, containing the rule number, title, and content of each rule"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rule_number, title, content "
                "FROM rule "
                "WHERE server_id = ? AND rule_number = ?",
                (str(server_id), int(rule_num_to_fetch))
            )
            row = await cursor.fetchone()
            if row is None:
                return None

            rule_number, title, content = row
            rule_number = int(rule_number)
            return Rule(rule_number, title, content)

    async def add_rule(self, server_id: int, title: str, content: str) -> None:
        """Adds a rule to the rule table"""
        async with self.db.get_write_connection() as conn:
            #get the next rule number for this server
            cursor = await conn.execute(
                "SELECT COALESCE(MAX(rule_number), 0) + 1 "
                "FROM rule "
                "WHERE server_id = ?",
                (str(server_id),)
            )
            row = await cursor.fetchone()
            next_rule_number = int(row[0])

            await conn.execute(
                "INSERT INTO rule (server_id, rule_number, title, content) "
                "VALUES (?, ?, ?, ?)",
                (str(server_id), next_rule_number, title, content)
            )
            await conn.commit()

    async def update_rule(self, server_id: int, rule_number_to_update: int, title: str, content: str) -> int:
        """Updates an existing rule for this server
        Returns: the number of updated rows"""
        async with self.db.get_write_connection() as conn:

            cursor = await conn.execute(
                "UPDATE rule SET title = ?, content = ? "
                "WHERE server_id = ? AND rule_number = ? ",
                (title, content, str(server_id), int(rule_number_to_update))
            )
            await conn.commit()

            return cursor.rowcount

    async def delete_rule(self, server_id: int, rule_num_to_delete: int) -> int:
        """deletes a rule from the rule table for this server and rule number, if it exists
        Returns: the number of deleted rule rows"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM rule WHERE server_id = ? AND rule_number = ? ",
                (str(server_id), rule_num_to_delete)
            )
            await conn.commit()

            return cursor.rowcount