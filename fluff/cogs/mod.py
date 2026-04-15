import sqlite3
from datetime import timezone, datetime
from typing import List

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Cog
import asyncio
import emoji

from database.model.TempBannedUser import TempBannedUser
from database.repository.tempban_repository import TempBanRepository
from helpers.checks import ismod, isadmin
from helpers.datafiles import add_userlog
from helpers.embeds import stock_embed
from helpers.placeholders import random_msg
from helpers.sv_config import get_config
import re

from helpers.time import parse_duration

#for the love of god, this cog really needs to be split out into multiple cogs for better readability
class Mod(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.check_if_target_is_staff = self.check_if_target_is_staff
        self.bot.modqueue = {}
        self.tempban_repo: TempBanRepository = TempBanRepository(self.bot.db)

    async def cog_load(self):
        self.unban_user_task.start()

    async def cog_unload(self):
        self.unban_user_task.cancel()

    def check_if_target_is_staff(self, target):
        return any(
            r
            == self.bot.pull_role(
                target.guild, get_config(target.guild.id, "staff", "modrole")
            )
            or r
            == self.bot.pull_role(
                target.guild, get_config(target.guild.id, "staff", "adminrole")
            )
            for r in target.roles
        )

    @commands.bot_has_permissions(kick_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["boot"])
    async def kick(self, ctx, target: discord.Member, *, reason: str = ""):
        """This kicks a user.

        Giving a `reason` will send the reason to the user.

        - `target`
        The target to kick.
        - `reason`
        The reason for the kick. Optional."""
        if target == ctx.author:
            return await ctx.send(
                random_msg("warn_targetself", authorname=ctx.author.name)
            )
        elif target == self.bot.user:
            return await ctx.send(
                random_msg("warn_targetbot", authorname=ctx.author.name)
            )
        elif self.check_if_target_is_staff(target):
            return await ctx.send("I cannot kick Staff members.")

        add_userlog(ctx.guild.id, target.id, ctx.author, reason, "kicks")

        safe_name = await commands.clean_content(escape_markdown=True).convert(
            ctx, str(target)
        )

        dm_message = f"**You were kicked** from `{ctx.guild.name}`."
        if reason:
            dm_message += f'\n*The given reason is:* "{reason}".'
        dm_message += "\n\nYou are able to rejoin."
        failmsg = ""

        try:
            await target.send(dm_message)
        except discord.errors.Forbidden:
            # Prevents kick issues in cases where user blocked bot
            # or has DMs disabled
            failmsg = "\nI couldn't DM this user to tell them."
            pass
        except discord.HTTPException:
            # Prevents kick issues on bots
            pass

        await target.kick(reason=f"[Kick peformed by {ctx.author}] {reason}")
        await ctx.send(f"**{target.mention}** was KICKED.{failmsg}")

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(isadmin)
    @commands.guild_only()
    @commands.command(aliases=["yeet"])
    async def ban(self, ctx, target: discord.User, *, reason: str = ""):
        """This bans a user.

        Giving a `reason` will send the reason to the user.

        - `target`
        The target to ban.
        - `reason`
        The reason for the ban. Optional."""
        if await self.should_skip_ban(ctx, target):
            return

        #remove the user from the temp ban table, if an entry exists. We dont want them to be unbanned automatically if we are
        #permanently banning them
        await self.remove_user_from_tempban(ctx, target.id)

        if reason:
            add_userlog(ctx.guild.id, target.id, ctx.author, reason, "bans")
        else:
            add_userlog(
                ctx.guild.id,
                target.id,
                ctx.author,
                f"No reason provided. ({ctx.message.jump_url})",
                "bans",
            )

        dm_message = f"**You were banned** from `{ctx.guild.name}`."
        if reason:
            dm_message += f'\n*The given reason is:* "{reason}".'
        dm_message += "\n\nThis ban does not expire"
        dm_message += (
            f", but you may appeal it here (although you must wait 1 week minimum before attempting to appeal):\n{get_config(ctx.guild.id, 'staff', 'appealurl')}"
            if get_config(ctx.guild.id, "staff", "appealurl")
            else "."
        )

        await self.handle_ban(ctx, target, dm_message, reason)

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(isadmin)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def tempban(self, ctx: commands.Context, target: discord.User, duration: str, *, reason: str):
        """This bans a user for a specified amount of time, after which they will be automatically unbanned from the server.

        Available commands:
        pls tempban user duration reason
        pls tempban update user duration
        pls tempban list
        pls tempban info target
        pls tempban remove (note that this only removes the tempban entry but does not unban. Use pls unban instead.)

        - `target`
        The target user to ban. A user ID or @mention.
        - `duration`
        The duration of the ban. You can specify minutes, hours, days, or weeks, e.g. 15m, 3h, 25d, 6w, etc.
        - `reason`
        The reason for the ban."""
        if await self.should_skip_ban(ctx, target):
            return

        date_to_unban: int = 0
        length_of_ban: int = 0
        ban_unit: str = ""
        try:
            date_to_unban, length_of_ban, ban_unit = parse_duration(duration)
            await self.tempban_repo.add_banned_user(target.id, ctx.author.id, ctx.guild.id, reason, date_to_unban)
        except ValueError as err:
            return await ctx.reply(str(err), mention_author=False)
        except sqlite3.Error as err:
            self.bot.log.error(f"Unable to insert into tempban repo for {target.id}: {err}")
            return await ctx.reply("Error trying to ban user. This user may already be banned", mention_author=False)

        dm_message = f"**You were temporarily banned** from `{ctx.guild.name}`."
        dm_message += f'\n*The given reason is:* "{reason}".'
        dm_message += f'\n\nThis ban will expire in {length_of_ban} {ban_unit}.'

        await self.handle_ban(ctx, target, dm_message, reason, str(length_of_ban) + " " + str(ban_unit))

    @commands.bot_has_permissions(embed_links=True)
    @tempban.command(aliases=["info"])
    @commands.check(isadmin)
    @commands.guild_only()
    async def list(self, ctx: commands.Context, target: discord.User = None):
        """Fetch information on users who are currently banned

           Pass a user ID in to see additional detail for a specific user

           - `target`
           The target ID of a user who is banned. Optional.
        """
        if target is None:
            banned_users: list[tuple[int, int]] = list()
            try:
                banned_users = await self.tempban_repo.get_all_banned_users(ctx.guild.id)
            except sqlite3.Error as err:
                self.bot.log.error(f"Unable to fetch banned users from tempban table: {str(err)}")
                return await ctx.reply("Error attempting to fetch temp banned users", mention_author=False)

            if not banned_users:
                return await ctx.reply("No users are temp banned", mention_author=False)

            return await self.create_and_send_tempban_list(ctx, banned_users)

        try:
            banned_user_info: TempBannedUser | None = await self.tempban_repo.get_banned_user_info(target.id, ctx.guild.id)
            if banned_user_info is None:
                return await ctx.reply("Could not find a temp banned user with that ID", mention_author=False)

            return await self.create_and_send_tempban_user_info(ctx, banned_user_info)
        except sqlite3.Error as err:
            self.bot.log.error(f"Unable to fetch banned user info for ID {target.id}: {str(err)}")
            return await ctx.reply("Error attempting to fetch info for that user", mention_author=False)

    @tempban.command()
    @commands.check(isadmin)
    @commands.guild_only()
    async def update(self, ctx: commands.Context, target: discord.User, duration: str):
        """Updates the time range for a specific users tempban"""
        date_to_unban: int = 0
        length_of_ban: int = 0
        ban_unit: str = ""
        rows_updated: int = 0
        try:
            date_to_unban, length_of_ban, ban_unit = parse_duration(duration)
            rows_updated = await self.tempban_repo.update_banned_user_date(target.id, ctx.guild.id, date_to_unban)
        except ValueError as err:
            return await ctx.reply(str(err), mention_author=False)
        except sqlite3.Error as err:
            self.bot.log.error(f"Unable to update the users unban date for {target.id}: {err}")
            return await ctx.reply("Error trying to update the users unban date.", mention_author=False)

        if rows_updated == 0:
            return await ctx.reply("No user tempban found", mention_author=False)

        return await ctx.reply(f"Unban date set to {length_of_ban} {ban_unit} from now", mention_author=False)

    @tempban.command(aliases=["delete"])
    @commands.check(isadmin)
    @commands.guild_only()
    async def remove(self, ctx: commands.Context, target: discord.User):
        """Removes a temp banned user"""
        row_removed_count = await self.remove_user_from_tempban(ctx, target.id, "un")
        if row_removed_count == 0:
            return await ctx.reply("No tempban entry found for that user", mention_author=False)
        else:
            return await ctx.reply("Tempban removed. Use `pls unban` if you want to actually unban the user.", mention_author=False)

    async def create_and_send_tempban_list(self, ctx: commands.Context, banned_users: List[tuple[int, int]]):
        embed = stock_embed(self.bot)
        embed.color = discord.Color.red()
        embed.title = "Temp banned users"

        tempbanned_users_embed_value = ""
        for banned_user in banned_users:
            dt = datetime.fromtimestamp(banned_user[1], tz=timezone.utc)
            tempbanned_users_embed_value += f"<@{banned_user[0]}>: Unbanned {discord.utils.format_dt(dt, 'R')}\n"

        embed.add_field(
            name="",
            value=tempbanned_users_embed_value,
            inline=False,
        )

        embed.add_field(
            name="Additional commands",
            value="Use `pls tempban info/list user_id_here` to view additional tempban information on a particular user",
            inline=False,
        )

        return await ctx.reply(embed=embed, mention_author=False)

    async def create_and_send_tempban_user_info(self, ctx: commands.Context, banned_user_info: TempBannedUser):
        embed = stock_embed(self.bot)
        embed.color = discord.Color.red()
        embed.title = "Info for temp banned user"

        embed.add_field(
            name="Banned User",
            value=f"<@{banned_user_info.banned_user_id}>",
            inline=False,
        )

        embed.add_field(
            name="Banned By",
            value=f"<@{banned_user_info.banned_by_id}>",
            inline=False,
        )

        embed.add_field(
            name="Ban Reason",
            value=banned_user_info.reason,
            inline=False,
        )

        dt = datetime.fromtimestamp(banned_user_info.date_to_unban, tz=timezone.utc)
        embed.add_field(
            name="Unban Time",
            value=f"{discord.utils.format_dt(dt, 'R')}",
            inline=False,
        )

        return await ctx.reply(embed=embed, mention_author=False)


    async def should_skip_ban(self, ctx, target: discord.User) -> bool:
        """Performs pre-checks that determine whether we should skip the ban process for this user"""
        if target == ctx.author:
            await ctx.send(
                random_msg("warn_targetself", authorname=ctx.author.name)
            )
            return True
        elif target == self.bot.user:
            await ctx.send(
                random_msg("warn_targetbot", authorname=ctx.author.name)
            )
            return True
        if ctx.guild.get_member(target.id):
            if self.check_if_target_is_staff(ctx.guild.get_member(target.id)):
                await ctx.send("I cannot ban Staff members.")
                return True

        # Check if already banned
        user = await self.bot.fetch_user(target.id)
        attempt_fetch_ban = None

        try:
            attempt_fetch_ban = await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            pass
        if isinstance(attempt_fetch_ban, discord.BanEntry):
            await ctx.reply(
                f"This user appears to be banned! `{attempt_fetch_ban.reason}`"
            )
            return True

        return False

    async def handle_ban(self, ctx: commands.Context, target: discord.User, dm_message: str, reason: str, length_of_ban: str = ""):
        """Handles banning the user and sending them a message"""
        failmsg = ""
        if ctx.guild.get_member(target.id) is not None:
            try:
                await target.send(dm_message)
            except discord.errors.Forbidden:
                # Prevents ban issues in cases where user blocked bot
                # or has DMs disabled
                failmsg = "\nI couldn't DM this user to tell them."
                pass
            except discord.HTTPException:
                # Prevents ban issues on bots
                pass

        await ctx.guild.ban(
            target,
            reason=f"[Ban performed by {ctx.author}] {reason}",
            delete_message_days=0,
        )
        duration_part = f" for {length_of_ban}" if length_of_ban else ""
        await ctx.send(f"**{target.mention}** is now BANNED{duration_part}.\n{failmsg}")

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["bandel"])
    async def dban(
        self, ctx, day_count: int, target: discord.User, *, reason: str = ""
    ):
        """This bans a user with X days worth of messages deleted.

        Giving a `reason` will send the reason to the user.

        - `day_count`
        The days worth of messages to delete.
        - `target`
        The target to kick.
        - `reason`
        The reason for the kick. Optional."""
        if await self.should_skip_ban(ctx, target):
            return

        if day_count < 0 or day_count > 7:
            return await ctx.send(
                "Message delete day count must be between 0 and 7 days."
            )

        # remove the user from the temp ban table, if an entry exists. We dont want them to be unbanned automatically if we are
        # permanently banning them
        await self.remove_user_from_tempban(ctx, target.id, "d")

        if reason:
            add_userlog(ctx.guild.id, target.id, ctx.author, reason, "bans")
        else:
            add_userlog(
                ctx.guild.id,
                target.id,
                ctx.author,
                f"No reason provided. ({ctx.message.jump_url})",
                "bans",
            )

        failmsg = ""
        if ctx.guild.get_member(target.id) is not None:
            dm_message = f"**You were banned** from `{ctx.guild.name}`."
            if reason:
                dm_message += f'\n*The given reason is:* "{reason}".'
            appealmsg = (
                f", but you may appeal it here (although you must wait 1 week minimum before attempting to appeal):\n{get_config(ctx.guild.id, 'staff', 'appealurl')}"
                if get_config(ctx.guild.id, "staff", "appealurl")
                else "."
            )
            dm_message += f"\n\nThis ban does not expire{appealmsg}"
            try:
                await target.send(dm_message)
            except discord.errors.Forbidden:
                # Prevents ban issues in cases where user blocked bot
                # or has DMs disabled
                failmsg = "\nI couldn't DM this user to tell them."
                pass
            except discord.HTTPException:
                # Prevents ban issues on bots
                pass

        await target.ban(
            reason=f"[Ban performed by {ctx.author}] {reason}",
            delete_message_days=day_count,
        )
        await ctx.send(
            f"**{target.mention}** is now BANNED.\n{day_count} days of messages were deleted.\n{failmsg}"
        )

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def massban(self, ctx, *, targets: str):
        """This mass bans user IDs.

        You can get IDs with `pls dump` if they're banned from
        a different server with the bot. Otherwise, good luck.
        This won't DM them.

        - `targets`
        The target to ban."""
        msg = await ctx.send(f"**MASSBAN IN PROGRESS**")
        targets_int = [int(target) for target in targets.strip().split(" ")]

        for target in targets_int:
            target_user = await self.bot.fetch_user(target)
            if await self.should_skip_ban(ctx, target_user):
                continue

            # remove the user from the temp ban table, if an entry exists. We dont want them to be unbanned automatically if we are
            # permanently banning them
            await self.remove_user_from_tempban(ctx, target, "mass")

            add_userlog(
                ctx.guild.id,
                target,
                ctx.author,
                f"Part of a massban. [[Jump]({ctx.message.jump_url})]",
                "bans",
            )

            await ctx.guild.ban(
                target_user,
                reason=f"[Ban performed by {ctx.author}] Massban",
                delete_message_days=0,
            )

        await msg.edit(content=f"All {len(targets_int)} users are now BANNED.")

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def unban(self, ctx, target: discord.User, *, reason: str = ""):
        """This unbans a user.

        The `reason` won't be sent to the user.

        - `target`
        The target to unban.
        - `reason`
        The reason for the unban. Optional."""

        await self.remove_user_from_tempban(ctx, target.id, "un")

        safe_name = await commands.clean_content(escape_markdown=True).convert(
            ctx, str(target)
        )

        await ctx.guild.unban(
            target, reason=f"[Unban performed by {ctx.author}] {reason}"
        )
        await ctx.send(f"{safe_name} is now UNBANNED.")

    @commands.bot_has_permissions(ban_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["silentban"])
    async def sban(self, ctx, target: discord.User, *, reason: str = ""):
        """This bans a user silently.

        In this case, the `reason` will only be sent to the logs and not DMed to them.

        - `target`
        The target to ban.
        - `reason`
        The reason for the ban. Optional."""
        if await self.should_skip_ban(ctx, target):
            return

        # remove the user from the temp ban table, if an entry exists. We dont want them to be unbanned automatically if we are
        # permanently banning them
        await self.remove_user_from_tempban(ctx, target.id, "s")

        if reason:
            add_userlog(ctx.guild.id, target.id, ctx.author, reason, "bans")
        else:
            add_userlog(
                ctx.guild.id,
                target.id,
                ctx.author,
                f"No reason provided. ({ctx.message.jump_url})",
                "bans",
            )

        safe_name = await commands.clean_content(escape_markdown=True).convert(
            ctx, str(target)
        )

        await ctx.guild.ban(
            target,
            reason=f"[Ban performed by {ctx.author}] {reason}",
            delete_message_days=0,
        )
        await ctx.send(f"{safe_name} is now silently BANNED.")

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["clear"])
    async def purge(
        self, ctx, limit: int | None, channel: discord.abc.GuildChannel | None
    ):
        """This clears a given number of messages.

        Please see the sister subcommands as well, in the [documentation](https://3gou.0ccu.lt/as-a-moderator/basic-functionality/#purging).
        Defaults to 50 messages in the current channel. Max of one million.

        - `limit`
        The limit of messages to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not limit:
            limit = 50

        if not channel:
            channel = ctx.channel
        if limit >= 1000000:
            return await ctx.reply(
                content=f"Your purge limit of `{limit}` is too high. Are you trying to `purge from {limit}`?",
                mention_author=False,
            )
        deleted = len(await channel.purge(limit=limit))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` messages purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command()
    async def bots(self, ctx, limit: int, channel: discord.abc.GuildChannel | None):
        """This clears a given number of bot messages.

        Defaults to 50 messages in the current channel. Max of one million.

        - `limit`
        The limit of messages to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not limit:
            limit = 50
        if not channel:
            channel = ctx.channel

        def is_bot(m):
            return any((m.author.bot, m.author.discriminator == "0000"))

        deleted = len(await channel.purge(limit=limit, check=is_bot))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` bot messages purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command(name="from")
    async def _from(
        self,
        ctx,
        target: discord.User,
        limit=50,
        channel: discord.abc.GuildChannel = None,
    ):
        """This clears a given number of user messages.

        Defaults to 50 messages in the current channel. Max of one million.

        - `target`
        The user to purge messages from.
        - `limit`
        The limit of messages to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not channel:
            channel = ctx.channel

        def is_mentioned(m):
            return target.id == m.author.id

        deleted = len(await channel.purge(limit=limit, check=is_mentioned))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` messages from {target} purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command(name="with")
    async def _with(
        self,
        ctx,
        string: str,
        limit=50,
        channel: discord.abc.GuildChannel = None,
    ):
        """This clears a given number of specific messages.

        Defaults to 50 messages in the current channel. Max of one million.

        - `string`
        Messages containing this will be deleted.
        - `limit`
        The limit of messages to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not channel:
            channel = ctx.channel

        def contains(m):
            return string in m.content

        deleted = len(await channel.purge(limit=limit, check=contains))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` messages containing `{string}` purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command(aliases=["emoji"])
    async def emotes(self, ctx, limit: int, channel: discord.abc.GuildChannel | None):
        """This clears a given number of emotes.

        Defaults to 50 messages in the current channel. Max of one million.

        - `limit`
        The limit of emotes to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not channel:
            channel = ctx.channel

        if not limit:
            limit = 50
        emote_re = re.compile(r":[A-Za-z0-9_]+:", re.IGNORECASE)

        def has_emote(m):
            return any(
                (
                    emoji.emoji_count(m.content),
                    emote_re.findall(m.content),
                )
            )

        deleted = len(await channel.purge(limit=limit, check=has_emote))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` emotes purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command()
    async def embeds(self, ctx, limit: int, channel: discord.abc.GuildChannel | None):
        """This clears a given number of messages with embeds.

        This includes stickers, by the way, but not emoji.
        Defaults to 50 messages in the current channel. Max of one million.

        - `limit`
        The limit of messages to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not channel:
            channel = ctx.channel

        if not limit:
            limit = 50

        def has_embed(m):
            return any((m.embeds, m.attachments, m.stickers))

        deleted = len(await channel.purge(limit=limit, check=has_embed))
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` embeds purged.",
            delete_after=5,
        )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @purge.command(aliases=["reactions"])
    async def reacts(self, ctx, limit: int, channel: discord.abc.GuildChannel | None):
        """This clears a given number of reactions.

        This does NOT delete their messages! Just the reactions!
        Defaults to 50 messages in the current channel. Max of one million.

        - `limit`
        The limit of reactions to delete. Optional.
        - `channel`
        The channel to purge from. Optional."""
        if not channel:
            channel = ctx.channel

        deleted = 0
        async for msg in channel.history(limit=limit):
            if msg.reactions:
                deleted += 1
                await msg.clear_reactions()
        await ctx.send(
            f"<a:bunnytrashjump:1256812177768185878> `{deleted}` reactions purged.",
            delete_after=5,
        )

    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["slow"])
    async def slowmode(
        self, ctx, channel: discord.abc.GuildChannel = None, seconds: int = 5
    ):
        """This makes the bot set a channel's slowmode.

        Slowmode will be set in a `channel` to a specified amount of `seconds`. Running this command by itself will enable a 5 second slowmode for the invoker's current channel.

        - `channel`
        The channel to manage slowmode for. Optional, will target to the current channel by default.
        - `seconds`
        The time (in seconds) to set slowmode for. Optional, will be five seconds by default.
        """
        if not channel:
            channel = ctx.channel

        if channel.slowmode_delay == seconds:
            return await ctx.reply(
                f"Slowmode is already `{seconds}` second(s) in {channel.mention}!",
                mention_author=False,
            )

        new_channel_data = await channel.edit(slowmode_delay=seconds)

        if new_channel_data.slowmode_delay > 0:
            return await ctx.reply(
                f"Slowmode set to `{seconds}` second(s) in {channel.mention}.",
                mention_author=False,
            )
        else:
            return await ctx.reply(
                f"Slowmode disabled in {channel.mention}.", mention_author=False
            )

    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["unslow"])
    async def unslowmode(self, ctx, channel: discord.abc.GuildChannel | None):
        """This makes the bot disable a channel's slowmode.

        Slowmode will be disabled in a `channel` if it is supplied, otherwise Fluff will disable slowmode for the invoker's current channel.

        - `channel`
        The channel to disable slowmode for. Optional, will target to the current channel by default.
        """
        if not channel:
            channel = ctx.channel

        if channel.slowmode_delay == 0:
            return await ctx.reply(
                f"Slowmode is already disabled in {channel.mention}!",
                mention_author=False,
            )

        if channel.slowmode_delay > 0:
            new_channel_data = await channel.edit(slowmode_delay=0)
            if new_channel_data.slowmode_delay == 0:
                return await ctx.reply(
                    f"Slowmode disabled in {channel.mention}.", mention_author=False
                )

    @commands.check(isadmin)
    @commands.guild_only()
    @commands.command(aliases=["send"])
    async def speak(
        self,
        ctx,
        channel: discord.abc.GuildChannel,
        *,
        text: str,
    ):
        """This makes the bot repeat some text in a specific channel.

        If you manage the bot, it can even run commands.

        - `channel`
        The channel to post the text in.
        - `text`
        The text to repeat."""
        output = await channel.send(text)
        if ctx.author.id in self.bot.config.managers:
            output.author = ctx.author
            newctx = await self.bot.get_context(output)
            newctx.message.author = ctx.guild.me
            await self.bot.invoke(newctx)
        await ctx.reply("👍", mention_author=False)

    @commands.check(isadmin)
    @commands.guild_only()
    @commands.command()
    async def reply(
        self,
        ctx,
        message: discord.Message,
        *,
        text: str,
    ):
        """This makes the bot reply to a message.

        If you manage the bot, it can even run commands.

        - `message`
        The message to reply to. Message link preferred.
        - `text`
        The text to repeat."""
        output = await message.reply(content=f"{text}", mention_author=False)
        if ctx.author.id in self.bot.config.managers:
            output.author = ctx.author
            newctx = await self.bot.get_context(output)
            newctx.message.author = ctx.guild.me
            await self.bot.invoke(newctx)
        await ctx.reply("👍", mention_author=False)

    @commands.check(isadmin)
    @commands.guild_only()
    @commands.command()
    async def react(
        self,
        ctx,
        message: discord.Message,
        emoji: str,
    ):
        """This makes the bot react to a message with an emoji.

        It can't react with emojis it doesn't have access to.

        - `message`
        The message to reply to. Message link preferred.
        - `emoji`
        The emoji to react with."""
        emoji = discord.PartialEmoji.from_str(emoji)
        await message.add_reaction(emoji)
        await ctx.reply("👍", mention_author=False)

    @commands.check(isadmin)
    @commands.guild_only()
    @commands.command()
    async def typing(
        self,
        ctx,
        channel: discord.abc.GuildChannel,
        duration: int,
    ):
        """This makes the bot type in a channel for some time.

        There's not much else to it.

        - `channel`
        The channel or thread to type in.
        - `duration`
        The length of time to type for."""
        await ctx.reply("👍", mention_author=False)
        async with channel.typing():
            await asyncio.sleep(duration)

    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["msg"])
    async def message(self, ctx: commands.Context, target: discord.User, *, message: str = ""):
        try:
            await target.send(message)
        except Exception as e:
            return await ctx.reply("Unable to send a DM to this user", mention_author=False)

        return await ctx.reply(f"Message sent to {target.display_name}.", mention_author=False)

    @commands.bot_has_permissions(moderate_members=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def timeout(self, ctx: commands.Context, target: discord.Member, duration: str, *, reason: str):
        """This times out a user for a specified amount of time, and DM's the user with the reason for the timeout.

           Available commands:
           pls timeout user duration reason
           pls timeout remove user

           - `target`
           The target user to timeout. A user ID or @mention.
           - `duration`
           The duration of the timeout. You can specify minutes, hours, days, or weeks, e.g. 15m, 3h, 25d, 6w, etc.
           - `reason`
           The reason for the timeout."""
        if target == ctx.author:
            return await ctx.send(
                random_msg("warn_targetself", authorname=ctx.author.name)
            )
        elif target == self.bot.user:
            return await ctx.send(
                random_msg("warn_targetbot", authorname=ctx.author.name)
            )
        if ctx.guild.get_member(target.id):
            if self.check_if_target_is_staff(ctx.guild.get_member(target.id)):
                return await ctx.send("I cannot timeout Staff members.")

        length_of_timeout: int = 0
        timeout_unit: str = ""
        try:
            date_timeout_ends, length_of_timeout, timeout_unit = parse_duration(duration)
            timeout_datetime = datetime.fromtimestamp(date_timeout_ends, tz=timezone.utc)
            await target.timeout(timeout_datetime, reason=reason)
        except ValueError as err:
            return await ctx.reply(str(err), mention_author=False)
        except Exception as e:
            self.bot.log.error(f"error trying to timeout member {target.id}: {str(e)}")
            return await ctx.reply("Unable to timeout user. Make sure the timeout is no longer than 28 days", mention_author=False)

        try:
            await target.send(reason)
        except Exception as e:
            return await ctx.reply("The user was timed out, but I was unable to send the user a DM", mention_author=False)

        return await ctx.reply(f"User was timed out for {length_of_timeout} {timeout_unit}", mention_author=False)

    @commands.bot_has_permissions(moderate_members=True)
    @timeout.command()
    @commands.check(ismod)
    @commands.guild_only()
    async def remove(self, ctx: commands.Context, target: discord.Member):
        """Removes a timeout for a user"""
        try:
            await target.timeout(None)
        except Exception as e:
            self.bot.log.error(f"error trying to remove timeout for user {target.id}: {str(e)}")
            return await ctx.reply("Unable to remove timeout. Maybe the user is not timed out?", mention_author=False)

        return await ctx.reply("Timeout removed", mention_author=False)

    async def remove_user_from_tempban(self, ctx: commands.Context, user_id: int, ban_version: str = "") -> int:
        """Removes a user from the temp ban table, if such an entry for that user and server exists"""
        try:
            return await self.tempban_repo.remove_banned_user(user_id, ctx.guild.id)
        except sqlite3.Error as err:
            self.bot.log.error(
                f"Error trying to remove {user_id} from the tempban table before fully {ban_version}banning the user: {str(err)}")
            await ctx.send(f"Please double check that the user is currently temp banned")

        return 0

    @tasks.loop(minutes=1)
    async def unban_user_task(self):
        """Scheduled cron job task that runs every minute. This job is responsible for
        unbanning any temp banned users whose date_to_unban is less than or equal to the current UTC time"""
        current_epoch_timestamp = int(datetime.now(timezone.utc).timestamp())
        user_ids_by_server_to_unban: list[tuple[int, int]] = list()
        try:
            user_ids_by_server_to_unban = await self.tempban_repo.get_expired_ban_users(current_epoch_timestamp)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error querying expired ban users: {str(err)}")
            return

        if user_ids_by_server_to_unban:
            self.bot.log.info(f"unbanning {len(user_ids_by_server_to_unban)} tempbanned users")
            for user_id, server_id in user_ids_by_server_to_unban:
                try:
                    user = await self.bot.fetch_user(user_id)
                    guild = self.bot.get_guild(int(server_id))
                    if guild is None:
                        continue
                    await guild.unban(user, reason="[Unban performed by Fluff] automated tempban removal")
                    await self.tempban_repo.remove_banned_user(user_id, server_id)
                except discord.NotFound as err:
                    self.bot.log.error(f"error looking up/unbanning user {user_id}. removing from tempban table: {str(err)}")
                    try:
                        await self.tempban_repo.remove_banned_user(user_id, server_id)
                    except sqlite3.Error as err:
                        self.bot.log.error(f"Error trying to remove invalid ban for {user_id} from tempban table: {str(err)}")
                except (discord.HTTPException, discord.Forbidden) as err:
                    self.bot.log.error(f"failed to unban {user_id}: {err}")
                except sqlite3.Error as err:
                    self.bot.log.error(f"Error trying to remove {user_id} from tempban table in scheduled unban task: {str(err)}")


    @unban_user_task.before_loop
    async def before_unban_user_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Mod(bot))
