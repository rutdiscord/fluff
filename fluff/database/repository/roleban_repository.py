
"""Repository class responsible for handling reads and writes to the various roleban tables"""
import time

from discord import Role

from database.database import Database
from database.model.RolebanSession import RolebanSession, RolebanSessionUser
from model.RolebanStatus import RolebanStatus
from model.RolebanType import RolebanType


class RolebanRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_sessions(self, server_id: int) -> list[RolebanSession]:
        """Fetches all open sessions for this server, oldest first"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rs.id AS id, rs.server_id AS server_id, rs.channel_id AS channel_id, rs.type AS type, rs.created_at AS created_at, "
                "GROUP_CONCAT(rsu.user_id) AS user_ids, "
                "GROUP_CONCAT(rsu.rolebanned_by) AS rolebanned_bys, "
                "GROUP_CONCAT(rsu.status) AS statuses "
                "FROM roleban_session rs LEFT JOIN roleban_session_user rsu "
                "ON rs.id = rsu.session_id "
                "WHERE rs.server_id = ? "
                "GROUP BY rs.id "
                "ORDER BY rs.id ASC",
                (str(server_id),)
            )
            rows = await cursor.fetchall()
            return [self.row_to_session(row) for row in rows]

    async def create_session(self, server_id: int, user_ids_to_roles: dict[int, list[Role]], channel_id: int, rolebanned_by: int, roleban_type: RolebanType) -> RolebanSession:
        """Creates a roleban session, and stores each users previous roles, if they exist.
        Returns: an instance of RolebanSession"""
        async with self.db.get_write_connection() as conn:
            created_at = int(time.time())
            cursor = await conn.execute(
                "INSERT INTO roleban_session (server_id, channel_id, type, created_at) "
                "VALUES (?, ?, ?, ?)",
                (str(server_id), str(channel_id), roleban_type.value, str(created_at))
            )
            session_id = cursor.lastrowid

            if user_ids_to_roles:
                await conn.executemany(
                    "INSERT INTO roleban_session_user (session_id, user_id, status, rolebanned_by) VALUES (?, ?, ?, ?)",
                    [(session_id, str(user_id), RolebanStatus.ACTIVE.value, str(rolebanned_by)) for user_id in user_ids_to_roles]
                )

                await conn.executemany(
                    "INSERT INTO roleban_session_user_role (session_id, user_id, role_id) VALUES (?, ?, ?)",
                    [
                        (session_id, str(user_id), str(role.id))
                        for user_id, roles in user_ids_to_roles.items()
                        for role in roles
                    ]
                )

            await conn.commit()
            users = [
                RolebanSessionUser(
                    user_id=user_id,
                    rolebanned_by=rolebanned_by,
                    status=RolebanStatus.ACTIVE
                )
                for user_id in user_ids_to_roles
            ]
            return RolebanSession(
                id=int(session_id),
                server_id=server_id,
                channel_id=channel_id,
                type=roleban_type,
                created_at=created_at,
                users=users
            )

    async def get_active_users_in_session(self, session_id: int) -> list[int]:
        """Fetches list of discord user ID's that are still in this session and active"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT user_id FROM roleban_session_user WHERE session_id = ? AND status = 'active'",
                (session_id,)
            )
            rows = await cursor.fetchall()
            return [int(row[0]) for row in rows]

    async def delete_session(self, session_id: int) -> int:
        """Deletes a session and any related information, such as the stored user roles.
        Returns: the number of deleted rows"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM roleban_session WHERE id = ?",
                (session_id,)
            )
            await conn.commit()
            return cursor.rowcount

    async def remove_user_from_session(self, session_id: int, user_id: int) -> int:
        """Removes a user from a session.
        Returns: the number of deleted rows"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM roleban_session_user WHERE session_id = ? AND user_id = ?",
                (session_id, str(user_id))
            )
            result = cursor.rowcount

            await conn.execute(
                "DELETE FROM roleban_session_user_role WHERE session_id = ? AND user_id = ?",
                (session_id, str(user_id))
            )

            await conn.commit()
            return result

    async def update_user_status(self, session_id: int, user_id: int, roleban_status: RolebanStatus) -> int:
        """Updates a user status for a specific session to denote whether the user has rejoined,
        meaning we set the status to active, or the user has left the server , meaning we set the status to left
        Returns: the number of updated rows"""
        async with self.db.get_write_connection() as conn:
            cursor = await conn.execute(
                "UPDATE roleban_session_user SET status = ? WHERE session_id = ? AND user_id = ?",
                (roleban_status.value, session_id, str(user_id))
            )
            await conn.commit()
            return cursor.rowcount

    async def reactivate_user_session(self, session_id: int, user_id: int, channel_id: int) -> int:
        """Reactivates a 'left' session after the user rejoined, pointing the parent session at the (possibly new) channel ID
        Returns: the number of updated rows"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "UPDATE roleban_session SET channel_id = ? WHERE id = ?",
                (str(channel_id), session_id)
            )
            cursor = await conn.execute(
                "UPDATE roleban_session_user SET status = ? WHERE session_id = ? AND user_id = ?",
                (RolebanStatus.ACTIVE.value, session_id, str(user_id))
            )
            await conn.commit()
            return cursor.rowcount

    async def get_session_by_user(self, server_id: int, user_id: int) -> RolebanSession | None:
        """Fetches the session for this user in this server
        Returns: the session, or None if the user has no open session"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rs.id AS id, rs.server_id AS server_id, rs.channel_id AS channel_id, rs.type AS type, rs.created_at AS created_at, "
                "GROUP_CONCAT(rsu.user_id) AS user_ids, "
                "GROUP_CONCAT(rsu.rolebanned_by) AS rolebanned_bys, "
                "GROUP_CONCAT(rsu.status) AS statuses "
                "FROM roleban_session rs JOIN roleban_session_user rsu "
                "ON rs.id = rsu.session_id "
                "WHERE rs.server_id = ? AND rsu.user_id = ? "
                "GROUP BY rsu.user_id",
                (str(server_id), str(user_id))
            )
            row = await cursor.fetchone()
            return self.row_to_session(row) if row else None

    async def get_session_by_channel(self, server_id: int, channel_id: int) -> RolebanSession | None:
        """Fetches the session assigned to this channel
        Returns: the session, or None if no session is using this channel"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rs.id AS id, rs.server_id AS server_Id, rs.channel_id AS channel_id, rs.type AS type, rs.created_at AS created_at, "
                "GROUP_CONCAT(rsu.user_id) AS user_ids, "
                "GROUP_CONCAT(rsu.rolebanned_by) AS rolebanned_bys, "
                "GROUP_CONCAT(rsu.status) AS statuses "
                "FROM roleban_session rs LEFT JOIN roleban_session_user rsu "
                "ON rs.id = rsu.session_id "
                "WHERE rs.server_id = ? AND rs.channel_id = ? "
                "GROUP BY rs.channel_id",
                (str(server_id), str(channel_id))
            )
            row = await cursor.fetchone()
            return self.row_to_session(row) if row else None

    async def get_role_ids(self, session_id: int, user_id: int) -> list[int]:
        """Fetches the stored (pre-roleban) role ids for this session and user"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT role_id FROM roleban_session_user_role WHERE session_id = ? AND user_id = ?",
                (session_id, str(user_id))
            )
            rows = await cursor.fetchall()
            return [int(row[0]) for row in rows]

    def row_to_session(self, row) -> RolebanSession:
        user_ids = row["user_ids"].split(",") if row["user_ids"] else []
        rolebanned_bys = row["rolebanned_bys"].split(",") if row["rolebanned_bys"] else []
        statuses = row["statuses"].split(",") if row["statuses"] else []

        users = [
            RolebanSessionUser(
                user_id=int(uid),
                rolebanned_by=int(rb),
                status=st
            )
            for uid, rb, st in zip(user_ids, rolebanned_bys, statuses)
        ]

        return RolebanSession(
            id=int(row["id"]),
            server_id=int(row["server_id"]),
            channel_id=int(row["channel_id"]) if row["channel_id"] is not None else None,
            type=RolebanType(row["type"]),
            created_at=int(row["created_at"]),
            users=users
        )