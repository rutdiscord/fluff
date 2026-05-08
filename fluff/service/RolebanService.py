import re
import sqlite3

import discord
from discord import CategoryChannel, TextChannel, Role
from discord.ext import commands

from database.model.RolebanSession import RolebanSession
from database.repository.roleban_repository import RolebanRepository
from helpers.embeds import createdat_embed, joinedat_embed, stock_embed, author_embed
from model.RolebanStatus import RolebanStatus
from model.RolebanType import RolebanType
from service.ConfigService import ConfigService
from service.NotificationService import NotificationService

RULEPUSH_CHANNEL_NAME_PATTERN = re.compile(r"^rulepush(\d+)$")
TOSS_CHANNEL_NAME_PATTERN = re.compile(r"^toss(\d+)$")

class RolebanService:
    """A service that is responsible for handling all things roleban (toss/untoss, rulepush, etc)"""
    def __init__(self, bot):
        self.bot = bot
        self.config_service: ConfigService = self.bot.config_service
        self.notification_service: NotificationService = self.bot.notification_service
        self.roleban_repo: RolebanRepository = RolebanRepository(self.bot.db)

    async def get_open_sessions(self, server_id: int) -> list[RolebanSession] | None:
        """Fetches the open sessions for this server"""
        try:
            return await self.roleban_repo.get_sessions(server_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching open sessions for server {server_id}: {err}")

        return None

    async def roleban_users(self, ctx: commands.Context, members: list[discord.Member], roleban_type: RolebanType) -> RolebanSession | None:
        """Rolebans a user by creating a new roleban channel, removing the users roles, and adding the roleban role
        Returns: an instance of RolebanSession if the user was successfully rolebanned, otherwise None, meaning an error occurred and the user was not rolebanned"""

        for member in members:
            try:
                existing = await self.roleban_repo.get_session_by_user(ctx.guild.id, member.id)
            except sqlite3.Error as err:
                self.bot.log.error(f"Error checking existing roleban session in server {ctx.guild.id}: {err}")
                await ctx.reply("Database error while checking existing sessions. Roleban cancelled.", mention_author=False)
                return None

            if existing is not None:
                location = f"<#{existing.channel_id}>" if existing.channel_id else "a deleted channel"
                await ctx.reply(
                    f"That member is already rolebanned in {location}.",
                    mention_author=False,
                )
                return None

        channel: TextChannel | None = await self.create_roleban_channel(ctx.guild, roleban_type)
        if channel is None:
            await ctx.reply("Failed to create the roleban channel.", mention_author=False)
            return None

        roleban_role = self.bot.pull_role(ctx.guild, self.config_service.get_server_config(ctx.guild.id, "toss", "tossrole"))
        user_ids_to_all_roles: dict[int, list[Role]] = {}
        user_ids_to_unassignable_roles: dict[int, list[Role]] = {}
        for member in members:
            all_roles, unassignable_roles = await self.get_non_rolebanned_user_roles(ctx.guild, member, roleban_role)
            user_ids_to_all_roles[member.id] = all_roles
            user_ids_to_unassignable_roles[member.id] = unassignable_roles

        try:
            session = await self.roleban_repo.create_session(
                ctx.guild.id,
                user_ids_to_all_roles,
                channel.id,
                ctx.author.id,
                roleban_type
            )
        except sqlite3.Error as err:
            self.bot.log.error(f"Error creating roleban session in server {ctx.guild.id}: {err}")
            await self.delete_roleban_channel(channel, "roleban setup failed")
            await ctx.reply("Error while creating the roleban session.", mention_author=False)
            return None

        all_successful = True
        for member in members:
            try:
                await self.replace_roles(member, [roleban_role], user_ids_to_unassignable_roles[member.id],f"User rolebanned by {ctx.author} ({ctx.author.id})")
                await channel.set_permissions(member, read_messages=True)
            except (discord.Forbidden, discord.HTTPException) as err:
                all_successful = False
                self.bot.log.error(f"Error replacing roles or editing channel permissions for roleban in server {ctx.guild.id}: {err}")
                break

            try:
                notification_embed = self.create_notification_embed(ctx, member, user_ids_to_all_roles[member.id], roleban_type, channel)
                await self.notification_service.send_notification(ctx.guild, notification_embed)
            except Exception as err:
                self.bot.log.error(f"Error sending notification embed for roleban: {err}")

        #some portion of the users either couldnt be assigned the correct role, or couldnt view the channel, so we need to unroleban everyone
        if not all_successful:
            for member in members:
                await self.unroleban_user(ctx, session, member.id, channel)

            await self.delete_roleban_channel(channel, "roleban setup failed", session.id)
            await ctx.reply("Error attempting to set roleban permissions for user. Roleban cancelled.", mention_author=False)
            return None

        return session

    async def unroleban_user(self, ctx: commands.Context, session: RolebanSession, user_id: int, channel: discord.TextChannel | None = None) -> bool:
        """Releases a user from their roleban, restores roles (if the member is present), and sends a message in the notification channel
        Returns: True if this codepath successfully unrolebanned the user, false we were unable to unroleban the user"""
        if user_id not in {u.user_id for u in session.users}:
            return False

        member = ctx.guild.get_member(user_id)
        try:
            role_ids = await self.roleban_repo.get_role_ids(session.id, user_id)
            await self.roleban_repo.remove_user_from_session(session.id, user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error releasing roleban session for user ID user_id {user_id} and session ID {session.id}: {err}")
            return False

        restored_roles, failed_roles = [], []
        if member is not None:
            roles = [ctx.guild.get_role(role_id) for role_id in role_ids]
            roles = [role for role in roles if role is not None]
            assignable = [role for role in roles if role.is_assignable()]
            unassignable = [role for role in roles if not role.is_assignable()]
            restored_roles, failed_roles = await self.replace_roles(member, assignable, unassignable, f"User unrolebanned by {ctx.author} ({ctx.author.id})")
            if channel is not None:
                try:
                    await channel.set_permissions(member, read_messages=False)
                except Exception as err:
                    pass


        embed = stock_embed(self.bot)
        embed.color = discord.Color.green()
        if session.type == RolebanType.RULEPUSH:
            embed.title = "📗 Rulepush removed"
        elif session.type == RolebanType.TOSS:
            embed.title = "🚶 Toss removed"


        if member is not None and member.id == ctx.author.id:
            embed.description = f"{member.mention} was un{session.type.value}ed automatically [`#{ctx.channel.name}`]"
        else:
            embed.description = f"user ID {user_id} was un{session.type.value}ed by {ctx.author.mention} [`#{ctx.channel.name}`]"

        embed.add_field(name="🎨 Restored Roles", value=self.format_role_list(restored_roles), inline=False)
        if failed_roles:
            embed.add_field(name="🚫 Failed Roles", value=self.format_role_list(failed_roles), inline=False)

        if member is None:
            embed.add_field(
                name="⚠️ Note",
                value="The user is no longer in the server, so no roles were restored.",
                inline=False,
            )

        await self.notification_service.send_notification(ctx.guild, embed)

        return True

    async def get_roleban_session_by_channel(self, server_id: int, channel_id: int) -> RolebanSession | None:
        try:
            return await self.roleban_repo.get_session_by_channel(server_id, channel_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error getting session by channel {channel_id}: {err}")

        return None

    async def get_roleban_session_by_user(self, server_id: int, user_id: int) -> RolebanSession | None:
        try:
            return await self.roleban_repo.get_session_by_user(server_id, user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error getting session by user id {user_id}: {err}")

        return None

    async def create_roleban_channel(self, guild: discord.Guild, roleban_type: RolebanType) -> discord.TextChannel | None:
        """Creates a new roleban channel, depending on the type of roleban requested."""
        try:
            category = self.bot.pull_category(guild,self.config_service.get_server_config(guild.id, "toss", "tosscategory"))
            return await self.perform_channel_creation_and_add_overrides(guild, category, roleban_type)
        except (discord.Forbidden, discord.HTTPException) as err:
            self.bot.log.error(f"Error creating roleban channel in server {guild.id}: {err}")

        return None

    async def perform_channel_creation_and_add_overrides(self, guild: discord.Guild, category: CategoryChannel, roleban_type: RolebanType) -> TextChannel:
        """Creates the actual channel, and adds necessary overrides for staff."""
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True),
        }

        bot_role = self.bot.pull_role(guild, self.config_service.get_server_config(guild.id, "staff", "botrole"))
        if bot_role:
            overwrites[bot_role] = discord.PermissionOverwrite(read_messages=True)

        staff_roles = [
            self.bot.pull_role(guild, self.config_service.get_server_config(guild.id, "staff", "modrole")),
            self.bot.pull_role(guild, self.config_service.get_server_config(guild.id, "staff", "adminrole")),
        ]
        for staff_role in staff_roles:
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True)

        return await guild.create_text_channel(
            self.get_next_channel_name(guild, roleban_type),
            reason=f"Fluff {roleban_type.value}",
            category=category,
            overwrites=overwrites
        )

    async def delete_roleban_channel(self, channel: discord.TextChannel, reason: str, session_id: int | None = None) -> bool:
        """Deletes a roleban channel if no active users are still rolebanned in that channel
           Args:
                  channel: discord.TextChannel to delete
                  reason: reason for deleting this channel
                  session_id: optional ID. If passed, validates that no active users are still rolebanned in that session
           Returns: a boolean representing whether the channel was deleted or not"""
        if not RULEPUSH_CHANNEL_NAME_PATTERN.match(channel.name) and not TOSS_CHANNEL_NAME_PATTERN.match(channel.name):
            return False

        try:
            if session_id is not None:
                active_session_users: list[int] = await self.roleban_repo.get_active_users_in_session(session_id)
                if len(active_session_users) > 0:
                    return False

                await self.delete_session(session_id)

            await channel.delete(reason=reason)
            return True
        except discord.NotFound:
            pass
        except (discord.Forbidden, discord.HTTPException) as err:
            self.bot.log.error(f"Failed to delete roleban channel #{channel.name}: {err}")
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching session info for session ID {session_id}: {err}")

        return False

    async def delete_session(self, session_id: int):
        try:
            await self.roleban_repo.delete_session(session_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error deleting roleban session in the database for session ID {session_id}: {err}")

    async def update_user_session_status(self, session_id: int, user_id: int, status: RolebanStatus) -> int:
        """Updates a users status for a specific session
        Returns: the number of rows that were updated in the database"""
        try:
            return await self.roleban_repo.update_user_status(session_id, user_id, status)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error updating session status for session ID {session_id} and user ID {user_id}: {err}")

        return 0

    async def reactivate_user_session(self, session_id: int, user_id: int, channel_id: int) -> int:
        """Reactivates a users session by setting the status to ACTIVE and updating the channel ID"""
        try:
            return await self.roleban_repo.reactivate_user_session(session_id, user_id, channel_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error reactivating session for session ID {session_id} and user ID {user_id}: {err}")

        return 0

    async def replace_roles(self, member: discord.Member, assignable_roles: list[discord.Role],
                            unassignable_roles: list[discord.Role], reason: str) -> tuple[list, list]:
        """Replaces the users roles with the list of roles
        Returns: (new roles, failed roles)"""
        try:
            await member.edit(
                roles=assignable_roles + unassignable_roles,
                reason=reason,
            )
            return assignable_roles + unassignable_roles, []
        except discord.Forbidden:
            # e.g. user had a booster role, but the boost expired when trying to restore the roles
            await member.edit(roles=assignable_roles, reason=reason)
            return assignable_roles, unassignable_roles

    async def assign_roleban_role(self, member: discord.Member, reason: str) -> bool:
        """Assigns the roleban role to the user, and logs why this user was assigned that role
        Returns: a boolean representing whether the assignment was successful or not"""
        try:
            roleban_role = self.bot.pull_role(member.guild,self.config_service.get_server_config(member.guild.id, "toss","tossrole"))
            all_roles, unassignable_roles = await self.get_non_rolebanned_user_roles(member.guild, member, roleban_role)
            await self.replace_roles(member, [roleban_role], unassignable_roles, reason)
        except Exception as e:
            self.bot.log.error(f"Failed to assign roleban role to user: {member.id}")
            return False

        return True


    async def get_non_rolebanned_user_roles(self, guild: discord.Guild, member: discord.Member, roleban_role: discord.Role) -> tuple[list[discord.Role], list[discord.Role]]:
        """Fetches all roles (excluding the guild default role and the roleban role) that belong to a user, and unassignable roles,
        which is a subset of the all roles list, but only including roles that we cannot assign the user (like the server
        booster role)"""
        all_roles = [r for r in member.roles if r != guild.default_role and r != roleban_role]
        unassignable_roles = [r for r in all_roles if not r.is_assignable()]
        return all_roles, unassignable_roles

    def get_next_channel_name(self, guild: discord.Guild, roleban_type: RolebanType) -> str:
        """Picks the lowest roleban-N name not currently in use in this guild"""
        used = set()
        for channel in guild.channels:
            match = None
            if roleban_type == RolebanType.RULEPUSH:
                match = RULEPUSH_CHANNEL_NAME_PATTERN.match(channel.name)
            else:
                match = TOSS_CHANNEL_NAME_PATTERN.match(channel.name)

            if match:
                used.add(int(match.group(1)))
        number = 1
        while number in used:
            number += 1
        return f"{roleban_type.value}{number}"

    def create_notification_embed(self, ctx: commands.Context, member: discord.Member,
                                  roles: list[discord.Role], roleban_type: RolebanType, roleban_channel: discord.TextChannel) -> discord.Embed:
        """Creates a notification embed for a rolebanned user"""
        notify_embed = stock_embed(self.bot)
        author_embed(notify_embed, member, True)
        notify_embed.color = ctx.author.color
        if roleban_type == RolebanType.RULEPUSH:
            notify_embed.title = "📖 Rulepush"
        elif roleban_type == RolebanType.TOSS:
            notify_embed.title = "🚷 Toss"
        else:
            notify_embed.title = "placeholder title"

        notify_embed.description = (
            f"{member.mention} was {roleban_type.value}ed by {ctx.author.mention} "
            f"[[Jump]({ctx.message.jump_url})]\n> This {roleban_type.value} takes place in {roleban_channel.mention}..."
        )
        createdat_embed(notify_embed, member)
        joinedat_embed(notify_embed, member)
        assignable = [r for r in roles if r.is_assignable()]
        unassignable = [r for r in roles if not r.is_assignable()]
        notify_embed.add_field(
            name="🎨 Previous Roles",
            value=self.format_role_list(assignable),
            inline=False
        )
        if unassignable:
            notify_embed.add_field(
                name="🚫 Kept Roles (not assignable)",
                value=self.format_role_list(unassignable),
                inline=False
            )

        return notify_embed

    def format_role_list(self, roles: list[discord.Role]) -> str:
        if not roles:
            return "None"
        formatted = ", ".join(role.mention for role in reversed(roles))
        if len(formatted) > 1024:  # embed field value limit
            formatted = formatted[:1021] + "..."
        return formatted