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
TOSS_CHANNEL_NAME_PATTERN = re.compile(r"^muted(\d+)$")

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

    async def roleban_users(self, ctx: commands.Context, members: list[discord.Member], roleban_type: RolebanType, remove_roles: bool = True, session_to_use: RolebanSession = None) -> RolebanSession | None:
        """Rolebans a user by creating a new roleban channel, removing the users roles (if remove_roles = true), and adding the roleban role
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

        channel: TextChannel | None = None
        if session_to_use:
            channel = await self.get_channel(session_to_use.channel_id)
        else:
            channel = await self.create_roleban_channel(ctx.guild, roleban_type)

        if channel is None:
            channel_action_type: str = "lookup" if session_to_use else "create"
            await ctx.reply(f"Failed to {channel_action_type} the roleban channel.", mention_author=False)
            return None

        roleban_role = self.bot.pull_role(ctx.guild, self.config_service.get_server_config(ctx.guild.id, "toss", "tossrole"))
        user_ids_to_all_roles: dict[int, list[Role]] = {}
        user_ids_to_unassignable_roles: dict[int, list[Role]] = {}
        if remove_roles:
            for member in members:
                all_roles, unassignable_roles = await self.get_non_rolebanned_user_roles(ctx.guild, member, roleban_role)
                user_ids_to_all_roles[member.id] = all_roles
                user_ids_to_unassignable_roles[member.id] = unassignable_roles
        else:
            for member in members:
                user_ids_to_all_roles[member.id] = list()
                user_ids_to_unassignable_roles[member.id] = list()

        try:
            session = await self.roleban_repo.create_or_add_to_session(
                server_id=ctx.guild.id,
                user_ids_to_roles=user_ids_to_all_roles,
                channel_id=channel.id,
                rolebanned_by=ctx.author.id,
                roleban_type=roleban_type,
                session_id_to_add=session_to_use.id if session_to_use else None
            )
        except sqlite3.Error as err:
            self.bot.log.error(f"Error creating roleban session in server {ctx.guild.id}: {err}")
            if not session_to_use: #if an existing roleban channel already exists with users, and we failed to add a new user to it, then dont delete the existing session
                await self.delete_roleban_channel(channel=channel, reason="roleban setup failed", session_id=None, delete_session=False)
            await ctx.reply("Error while creating the roleban session.", mention_author=False)
            return None

        all_successful = True
        for member in members:
            try:
                if remove_roles:
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

        #some portion of the users either could not be assigned the correct role, or could not view the channel, so we need to unroleban everyone
        if not all_successful:
            for member in members:
                await self.unroleban_user(ctx, session, member.id, channel)

            if not session_to_use:  # if an existing roleban channel already exists with users, and we failed to add a new user to it, then dont delete the existing session
                await self.delete_roleban_channel(channel=channel, reason="roleban setup failed", session_id=session.id, delete_session=True)
            await ctx.reply("Error attempting to set roleban permissions for user. Roleban cancelled.", mention_author=False)
            return None

        return session

    async def unroleban_user(self, ctx: commands.Context, session: RolebanSession, user_id: int, channel: discord.TextChannel | None = None) -> bool:
        """Releases a user from their roleban, restores roles (if the member is present), and sends a message in the notification channel
        Returns: True if this codepath successfully unrolebanned the user, false if we were unable to unroleban the user"""
        if user_id not in {u.user_id for u in session.users}:
            return False

        member = ctx.guild.get_member(user_id)
        try:
            role_ids = await self.roleban_repo.get_role_ids(session.id, user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching rolebanned user roles for user ID {user_id} and session ID {session.id}: {err}")
            return False

        restored_roles, failed_roles = [], []
        if member is not None:
            if role_ids:
                roles = [ctx.guild.get_role(role_id) for role_id in role_ids]
                roles = [role for role in roles if role is not None]
                assignable = [role for role in roles if role.is_assignable()]
                unassignable = [role for role in roles if not role.is_assignable()]
                try:
                    restored_roles, failed_roles = await self.replace_roles(member, assignable, unassignable, f"User unrolebanned by {ctx.author} ({ctx.author.id})")
                except Exception as err:
                    self.bot.log.error(f"Error re-assigning roles to rolebanned user: {err}")
                    return False
            else:
                removed_roleban_role: bool = await self.remove_roleban_role(member)
                if not removed_roleban_role:
                    self.bot.log.error(f"Could not remove roleban role from user: {member.id}")
                    return False
            if channel is not None:
                try:
                    await channel.set_permissions(member, read_messages=False)
                except Exception as err:
                    pass

        try:
            await self.roleban_repo.remove_user_from_session(session.id, user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error deleting roleban session for user ID {user_id} and session ID {session.id}: {err}")
            return False

        embed = stock_embed(self.bot)
        embed.color = discord.Color.green()
        if session.type == RolebanType.RULEPUSH:
            embed.title = "📗 Rulepush removed"
        elif session.type == RolebanType.TOSS:
            embed.title = "🚶 Toss removed"


        if member is not None and member.id == ctx.author.id:
            embed.description = f"{member.mention} was un{session.type.value}ed automatically [`#{ctx.channel.name}`]"
        elif member is not None:
            embed.description = f"{member.mention} was un{session.type.value}ed by {ctx.author.mention} [`#{ctx.channel.name}`]"
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

    async def delete_roleban_channel(self, channel: discord.TextChannel, reason: str, session_id: int | None = None, delete_session: bool = False) -> bool:
        """Deletes a roleban channel if no active users are still rolebanned in that channel
           Args:
                  channel: discord.TextChannel to delete
                  reason: reason for deleting this channel
                  session_id: optional ID. If passed, validates that no active users are still rolebanned in that session
                  delete_session: boolean whether to delete this session. skipped if session_id is None
           Returns: a boolean representing whether the channel was deleted or not"""
        if not RULEPUSH_CHANNEL_NAME_PATTERN.match(channel.name) and not TOSS_CHANNEL_NAME_PATTERN.match(channel.name):
            return False

        try:
            if session_id is not None:
                active_session_users: list[int] = await self.roleban_repo.get_active_users_in_session(session_id)
                if len(active_session_users) > 0:
                    return False

                if delete_session:
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

    async def update_session_start_time(self, session_id: int, start_time: int):
        """Updates the session start time, to accurately reflect when all rules have been posted in
        a rulepush session"""
        try:
            await self.roleban_repo.update_roleban_start_time(session_id, start_time)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error updating session start time for session ID {session_id}: {err}")

    async def reactivate_user_session(self, guild: discord.Guild, member: discord.Member, roleban_type: RolebanType) -> tuple[discord.TextChannel, int, bool] | None:
        """Reactivates a users session by re-creating the roleban channel (if necessary), and re-assigning the roleban role
        Returns: a tuple of [discord.TextChannel, session ID, bool] where the channel represents the actual channel this roleban is taking place,
        an int, representing the session ID in the database for this roleban, and a Boolean representing whether this channel was created
        from this method call, in which case the Boolean is true, or the channel already existed, in which case this Boolean is false. If this
        method fails, None is returned, indicating we did not successfully re-activate/roleban the user."""

        try:
            session: RolebanSession | None = await self.get_roleban_session_by_user(guild.id, member.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching session info when attempting to re-activate user session for user: {member.id}: {err}")
            return None

        if session is None or session.type is not roleban_type or session.users is None or len(session.users) <= 0:
            return None

        # reuse the old channel if it still exists, otherwise recreate it
        channel: discord.TextChannel = self.bot.get_channel(session.channel_id) if session.channel_id else None
        channel_recreated = False
        if channel is None:
            channel = await self.create_roleban_channel(guild, roleban_type)
            channel_recreated = True

            # channel creation failed
            if channel is None:
                await self.send_roleban_resume_failure_notification(member,roleban_type, "I could not create a new channel")
                return None

        try:
            await channel.set_permissions(member, read_messages=True)
        except (discord.Forbidden, discord.HTTPException) as err:
            self.bot.log.error(f"Error restoring channel permissions on rejoin in server {guild.id}: {err}")
            await self.send_roleban_resume_failure_notification(member, roleban_type,"I could not assign the correct channel permissions for the user")
            return None

        successful = await self.assign_roleban_role(member, "User was automatically rolebanned on server join.")
        if not successful:
            await self.send_roleban_resume_failure_notification(member,roleban_type, "I could not assign the roleban role to the user")
            return None

        try:
            await self.roleban_repo.reactivate_user_session(session.id, member.id, channel.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error reactivating session for session ID {session.id} and user ID {member.id}: {err}")
            await self.send_roleban_resume_failure_notification(member,roleban_type, f"a database error prevented the session from being reactivated. The channel is {channel.mention}")
            return None

        embed = stock_embed(self.bot)
        embed.title = f"🔁 {roleban_type.value.capitalize()} Resumed"
        embed.color = discord.Color.orange()
        embed.description = (
            f"{member.mention} ({member.id}) rejoined while {roleban_type.value.lower()}ed. Continuing in {channel.mention}..."
        )
        await self.notification_service.send_notification(member.guild, embed)

        return channel, session.id, channel_recreated

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

    async def remove_roleban_role(self, member: discord.Member) -> bool:
        """removes the roleban role from the user, if it exists"""
        try:
            roleban_role = self.bot.pull_role(member.guild, self.config_service.get_server_config(member.guild.id, "toss", "tossrole"))
            if roleban_role is None:
                return False
            await member.remove_roles(roleban_role)
        except Exception as e:
            self.bot.log.error(f"Failed to remove roleban role to user: {member.id}")
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
        """Picks the lowest rolebanN name not currently in use in this guild"""
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

        if roleban_type == RolebanType.TOSS:
            return f"muted{number}"

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

    async def send_roleban_resume_failure_notification(self, member: discord.Member, roleban_type: RolebanType, reason: str):
        """Sends a notification to the modlog channel, detailing why we were unable to resume a previous roleban"""
        embed = stock_embed(self.bot)
        embed.title = f"⚠️ {roleban_type.value.capitalize()} Resume Failed"
        embed.color = discord.Color.red()
        embed.description = f"{member.mention} rejoined with a pending {roleban_type.value.lower()} roleban, but {reason}."
        return await self.notification_service.send_notification(member.guild, embed)

    def format_role_list(self, roles: list[discord.Role]) -> str:
        if not roles:
            return "None"
        formatted = ", ".join(role.mention for role in reversed(roles))
        if len(formatted) > 1024:  # embed field value limit
            formatted = formatted[:1021] + "..."
        return formatted

    async def get_channel(self, channel_id: int) -> TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException as e:
                self.bot.log.error(f"Failed to fetch channel {channel_id}: {e}")
                return None

        return channel