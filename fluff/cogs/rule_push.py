import asyncio
import re
import sqlite3
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Cog

from database.model.LeaderboardEntry import LeaderboardEntry
from database.model.RolebanSession import RolebanSession, RolebanSessionUser
from database.model.TempBannedUser import TempBannedUser
from database.repository.rule_push_leaderboard_repository import RulePushLeaderboardRepository
from database.repository.rule_push_repository import RulePushRepository
from database.repository.rule_repository import RuleRepository
from database.repository.tempban_repository import TempBanRepository
from database.repository.user_metadata_repository import UserMetadataRepository
from helpers.checks import ismod, check_if_target_is_staff
from helpers.embeds import (
    stock_embed,
)
from helpers.rulepush_text import (
    KEYWORDS_PER_PUSH,
    render_rules,
    select_push_keywords,
)
from model.RolebanStatus import RolebanStatus
from model.RolebanType import RolebanType

CHANNEL_NAME_PATTERN = re.compile(r"^rulepush(\d+)$")
DISCORD_MESSAGE_LIMIT = 2000
MAX_MILLISECONDS_RULEPUSH_LEADERBOARD = 86400000

class RulePush(Cog):
    """Forces a user to re-read the rules.

    The user's roles are stripped (and stored in the database), they are isolated
    in a private rulepush channel, and the rules are posted with hidden out-of-place
    keywords. Typing all the keywords releases them automatically."""

    def __init__(self, bot):
        self.bot = bot
        self.rule_push_repo: RulePushRepository = RulePushRepository(self.bot.db)
        self.rule_push_leaderboard_repo: RulePushLeaderboardRepository = RulePushLeaderboardRepository(self.bot.db)
        self.user_metadata_repo: UserMetadataRepository = UserMetadataRepository(self.bot.db)
        self.rule_repo: RuleRepository = RuleRepository(self.bot.db)
        self.tempban_repo: TempBanRepository = TempBanRepository(self.bot.db)

    async def cog_load(self):
        self.kick_task.start()

    async def cog_unload(self):
        self.kick_task.cancel()

    async def send_long_message(self, channel: discord.TextChannel, text: str) -> discord.Message:
        """Sends text if its under the message limit, otherwise sends the message in fixed DISCORD_MESSAGE_LIMIT-sized chunks."""
        lines = text.split("\n")
        current_chunk = ""

        final_message: discord.Message = None
        for line in lines:
            # +1 for the newline we'll add
            if len(current_chunk) + len(line) + 1 > DISCORD_MESSAGE_LIMIT:
                if current_chunk:
                    final_message = await channel.send(current_chunk, allowed_mentions=discord.AllowedMentions.none())
                current_chunk = line
            else:
                current_chunk = current_chunk + "\n" + line if current_chunk else line

        if current_chunk:
            final_message = await channel.send(current_chunk, allowed_mentions=discord.AllowedMentions.none())

        return final_message

    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(aliases=["rpush"], invoke_without_command=True)
    async def rulepush(self, ctx: commands.Context, member: discord.Member = None):
        """This pushes a user into a rulepush channel.

        Available commands:
        pls rulepush user - rulepushes a user to a private channel
        pls unrulepush user - unrulepushes a user, restores roles, and deletes the channel
        pls rulepush sessions - SENSITIVE, DO NOT RUN IN PUBLIC CHANNEL. Views rulepush answer keywords and status per user
        pls rulepush keywords - SENSITIVE, DO NOT RUN IN PUBLIC CHANNEL. Lists all keywords that rulepush chooses from
        pls rulepush create/add rulepushkeyword1 rulepushkeyword2 ...
        pls rulepush delete/remove rulepushkeyword1 rulepushkeyword2 ....

        - `member`
        The member to send to a rulepush channel. Required."""
        if member is None:
            return await ctx.reply(
                "Please specify a member to rulepush, e.g. `pls rulepush @user`.",
                mention_author=False,
            )
        if member.id == ctx.author.id:
            return await ctx.reply("You cannot rulepush yourself.", mention_author=False)

        if check_if_target_is_staff(self.bot, member, self.bot.config_service):
            return await ctx.reply("You cannot rulepush other staff members.", mention_author=False)

        return await self.perform_rulepush(ctx, member, False)

    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["unrpush"])
    async def unrulepush(self, ctx: commands.Context, member: discord.Member = None):
        """This releases a user from a rulepush early.
        - `member`
        The member to release. Optional if run inside a rulepush channel."""
        if member is None:
            session = await self.bot.roleban_service.get_roleban_session_by_channel(ctx.guild.id, ctx.channel.id)
            if session is None:
                return await ctx.reply("No session found. Either run this inside a rulepush channel, or specify a member, e.g.: `pls unrulepush @user`.", mention_author=False)
        else:
            session = await self.bot.roleban_service.get_roleban_session_by_user(ctx.guild.id, member.id)
            if session is None:
                return await ctx.reply("That member is not rulepushed.", mention_author=False)

        if session.users is None or len(session.users) <= 0:
            return await ctx.reply("There are no members to unrulepush", mention_author=False)

        if session.type != RolebanType.RULEPUSH:
            return await ctx.reply("This user is not rulepushed.", mention_author=False)

        channel = ctx.guild.get_channel(session.channel_id)
        released = await self.bot.roleban_service.unroleban_user(ctx, session, session.users[0].user_id, channel)
        deleted_channel = False
        if released:
            deleted_channel = await self.bot.roleban_service.delete_roleban_channel(channel=channel, reason="manually removed rulepush", session_id=session.id, delete_session=True)

        if ctx.channel.id != session.channel_id:
            if released and deleted_channel:
                return await ctx.reply("Rulepush removed", mention_author=False)
            else:
                return await ctx.reply("Rulepush was not removed. Either an error occurred, or the rulepush no longer exists.", mention_author=False)

    @rulepush.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    async def sessions(self, ctx: commands.Context):
        """This shows the open rulepush sessions.

        No arguments."""
        sessions: list[RolebanSession] | None = await self.bot.roleban_service.get_open_sessions(ctx.guild.id)

        sessions = [session for session in sessions if session.type == RolebanType.RULEPUSH and session.users[0].status == RolebanStatus.ACTIVE.value]

        if not sessions:
            return await ctx.reply("No sessions found.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = "Rulepush Sessions"
        embed.color = ctx.author.color

        for session in sessions:
            #there is only 1 user per rulepush session
            user: RolebanSessionUser = session.users[0]
            channel = ctx.guild.get_channel(session.channel_id) if session.channel_id else None
            location = channel.mention if channel else "*(channel deleted)*"
            status = "🔴 Active" if user.status == RolebanStatus.ACTIVE.value else "🚪 User left"
            dt = datetime.fromtimestamp(session.created_at, tz=timezone.utc)

            found_keywords: list[str] = []
            not_found_keywords: list[str] = []
            try:
                found_keywords, not_found_keywords = await self.rule_push_repo.get_keywords_for_session(session.id)
            except sqlite3.Error as err:
                self.bot.log.error(f"error fetching keywords for session {session.id}: {err}")

            found_keyword_value = ", ".join(found_keywords) if found_keywords else "None"
            not_found_keyword_value = ", ".join(not_found_keywords) if not_found_keywords else "None"

            embed.add_field(
                name=f"{status} - #{channel.name}" if channel else status,
                value=(
                    f"> User: <@{user.user_id}>\n"
                    f"> Channel: {location}\n"
                    f"> Found keywords: {found_keyword_value}\n"
                    f"> Unfound Keywords: {not_found_keyword_value}\n"
                    f"> Rolebanned by: <@{user.rolebanned_by}>\n"
                    f"> Rolebanned: {discord.utils.format_dt(dt, 'R')}"
                ),
                inline=True
            )

        return await ctx.reply(embed=embed, mention_author=False)

    @rulepush.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    async def keywords(self, ctx: commands.Context):
        """This lists the rulepush keywords for this server.

        No arguments."""
        should_print_keywords: bool = await self.confirm_action(ctx, ctx.channel)
        if not should_print_keywords:
            return

        try:
            server_keywords: list[str] = await self.rule_push_repo.get_keywords(ctx.guild.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error getting rulepush keywords for server {ctx.guild.id}: {err}")
            return await ctx.reply("Error fetching server rulepush keywords", mention_author=False)

        embed = stock_embed(self.bot)
        embed.color = discord.Color.dark_teal()
        embed.title = "Rule Push Keywords"

        if not server_keywords:
            embed.add_field(name="", value="No rule push keywords found", inline=False)
        else:
            # Split keywords across multiple fields if needed
            chunks = []
            current = []
            current_len = 0

            for kw in server_keywords:
                # +2 for ", " separator
                addition = len(kw) + (2 if current else 0)
                if current_len + addition > 1024:
                    chunks.append(", ".join(current))
                    current = [kw]
                    current_len = len(kw)
                else:
                    current.append(kw)
                    current_len += addition

            if current:
                chunks.append(", ".join(current))

            for chunk in chunks:
                embed.add_field(name="", value=chunk, inline=False)

        if len(embed) > 6000:
            file_content = ", ".join(server_keywords).encode("utf-8")
            return await ctx.send(
                file=discord.File(
                    io.StringIO(file_content),  # type:ignore
                    filename=f"keywords.txt",
                )
            )

        return await ctx.reply(embed=embed, mention_author=False)

    @rulepush.command(aliases=["add"])
    @commands.guild_only()
    @commands.check(ismod)
    async def create(self, ctx: commands.Context, *, keywords: str):
        """This adds a list of rulepush keywords.

        - `keyword`
        The keyword to add. Required."""
        if keywords is None or len(keywords) <= 0:
            await ctx.reply("You must pass in at least one keyword to create.", mention_author=False)

        keyword_list = [k.lower().strip() for k in keywords.split()]
        try:
            keyword_added_count: int = await self.rule_push_repo.add_keywords(ctx.guild.id, keyword_list)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error creating rule push keyword for server {ctx.guild.id}: {err}")
            return await ctx.reply("Error creating rule push keywords", mention_author=False)

        if keyword_added_count > 0:
            return await ctx.reply(f"Successfully added {keyword_added_count} keywords.", mention_author=False)

        return await ctx.reply(f"No keywords were added, they already exist.", mention_author=False)

    @rulepush.command(aliases=["remove"])
    @commands.guild_only()
    @commands.check(ismod)
    async def delete(self, ctx: commands.Context, *, keywords: str):
        """This deletes a list of rulepush keywords.

        - `keyword`
        The keyword to delete. Required."""
        if keywords is None or len(keywords) <= 0:
            await ctx.reply("You must pass in at least one keyword to delete.", mention_author=False)

        keyword_list = [k.lower().strip() for k in keywords.split()]

        try:
            keyword_removed_count: int = await self.rule_push_repo.delete_keywords(ctx.guild.id, keyword_list)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error deleting rule push keyword for server {ctx.guild.id}: {err}")
            return await ctx.reply("Error deleting rule push keywords", mention_author=False)

        if keyword_removed_count > 0:
            return await ctx.reply(f"Successfully deleted {keyword_removed_count} keywords.", mention_author=False)

        return await ctx.reply(f"no keywords were deleted, they did not exist.", mention_author=False)


    @rulepush.command(aliases=["leaderboards"])
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context):
        """Returns the top 20 fastest rulepush times"""
        leaderboard_entries: list[LeaderboardEntry] = await self.rule_push_leaderboard_repo.get_rule_push_leaderboard()

        if not leaderboard_entries:
            return await ctx.reply("No rulepush leaderboard entries found.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = "🏆 Rule Push Leaderboard"
        embed.color = discord.Color.gold()

        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        lines = []

        for rank, entry in enumerate(leaderboard_entries):
            position = medals.get(rank, f"**{rank + 1}.**")
            time_str = self.caclulate_completion_time(entry.completion_time)
            date_str = f"<t:{entry.completion_date}:d> at <t:{entry.completion_date}:T>"
            lines.append(f"{position} **{time_str}** by <@{entry.user_id}> ({entry.user_name}) on {date_str}\n")

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Top 20 entries")

        return await ctx.reply(embed=embed, mention_author=False)

    @rulepush.command(aliases=["rank"])
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.guild_only()
    async def position(self, ctx: commands.Context):
        """Returns the users rulepush rank"""
        if ctx.author is None or ctx.guild is None:
            return await ctx.reply("You must be in a server to do this.", mention_author=False)

        position_data : tuple[int, str] | None = await self.rule_push_leaderboard_repo.get_user_position(ctx.author.id)
        if position_data is None:
            return await ctx.reply("No rulepush position data found.", mention_author=False)

        time_str = self.caclulate_completion_time(position_data[0])
        return await ctx.reply(f"You are rank **{position_data[1]}** with a time of **{time_str}**.", mention_author=False)

    @rulepush.command(aliases=["myself"])
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.guild_only()
    async def me(self, ctx: commands.Context):
        """Rolebans the user who invoked the method"""
        if ctx.author is None or ctx.guild is None:
            return await ctx.reply("You must be in a server to do this.", mention_author=False)

        is_target_staff: bool = check_if_target_is_staff(self.bot, ctx.author, self.bot.config_service)

        return await self.perform_rulepush(ctx, ctx.author, is_target_staff)

    @Cog.listener()
    async def on_ping_violation_threshold_reached(self, message: discord.Message):
        ctx: commands.Context = await self.bot.get_context(message)
        if ctx is None or ctx.author is None or ctx.guild is None:
            return

        is_target_staff: bool = check_if_target_is_staff(self.bot, ctx.author, self.bot.config_service)

        await self.perform_rulepush(ctx, ctx.author, is_target_staff, True)
        return await message.reply(
                    f"**{self.bot.pacify_name(message.author.name)}** has been automatically rulepushed for reaching the reply ping preference violation threshold."
                )

    async def perform_rulepush(self, ctx: commands.Context, member: discord.Member, is_target_staff: bool, ping_violation: bool = False):
        """performs the actual rulepush action"""
        if member.bot:
            return await ctx.reply("You cannot rulepush a bot.", mention_author=False)

        try:
            rules = await self.rule_repo.get_rules(ctx.guild.id)
            all_keywords = await self.rule_push_repo.get_keywords(ctx.guild.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error loading rules/keywords for server {ctx.guild.id}: {err}")
            return await ctx.reply("Database error while loading rules and keywords.", mention_author=False)

        if not rules:
            return await ctx.reply("No rules exist yet! Use `pls help rule`.", mention_author=False)

        chosen_keywords = select_push_keywords(all_keywords)
        if chosen_keywords is None:
            return await ctx.reply(
                f"At least {KEYWORDS_PER_PUSH} distinct keywords are required! Use `pls rulepush add`.",
                mention_author=False,
            )

        rendered_rules = render_rules(rules, chosen_keywords)
        if rendered_rules is None:
            return await ctx.reply(
                f"Not enough `{{{{}}}}` slots in the rules! At least {KEYWORDS_PER_PUSH} eligible slots are required.",
                mention_author=False,
            )

        session: RolebanSession = await self.bot.roleban_service.roleban_users(ctx=ctx, members=[member], roleban_type=RolebanType.RULEPUSH, remove_roles=not is_target_staff, session_to_use=None)
        if session is None:
            return

        try:
            await self.rule_push_repo.create_rulepush_session_keywords(session.id, chosen_keywords)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error while adding keyword for rulepush session: {err}")
            await self.bot.roleban_service.unroleban_user(ctx, session, member.id, ctx.guild.get_channel(session.channel_id))
            await self.bot.roleban_service.delete_roleban_channel(channel=self.bot.get_channel(session.channel_id), reason="Keyword DB setup failed, deleting channel", session_id=session.id, delete_session=True)
            return await ctx.reply(f"Error while creating rulepush session: {err}", mention_author=False)

        rulepush_channel: discord.TextChannel = self.bot.get_channel(session.channel_id)
        rules_message = ""
        for rule in rendered_rules:
            if rule.rule_number < 0:
                rules_message += f"**{rule.title}**\n{rule.content}"
            else:
                rules_message += f"**Rule {rule.rule_number}. {rule.title}**\n{rule.content}"

        final_message: discord.Message = await self.send_long_message(rulepush_channel, rules_message)
        epoch_start_time_ms = int(final_message.created_at.timestamp() * 1000)
        await self.bot.roleban_service.update_session_start_time(session.id, epoch_start_time_ms)

        await rulepush_channel.send(
            f"{member.mention}, you've been sent here by staff to re-read the server rules.\n\n"
            f"Hidden in the rules above are **{KEYWORDS_PER_PUSH} words that don't belong**. "
            f"Read carefully and type each out-of-place word in this channel. "
            f"Once you have found all {KEYWORDS_PER_PUSH} words, you will be automatically removed from this channel.",
            allowed_mentions=discord.AllowedMentions(users=True),
        )

        if ping_violation:
            await rulepush_channel.send(
                f"For future reference, please pay attention to a users ping preference.",
                file=discord.File("assets/noreply.png"),
            )

        try:
            await ctx.message.add_reaction("📖")
        except (discord.Forbidden, discord.HTTPException):
            pass

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        """Checks messages in rulepush channels against the sessions remaining keywords"""
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.channel, discord.TextChannel) or not isinstance(message.author, discord.Member):
            return
        if not CHANNEL_NAME_PATTERN.match(message.channel.name):
            return

        session: RolebanSession = await self.bot.roleban_service.get_roleban_session_by_channel(message.guild.id, message.channel.id)
        if session is None or session.type != RolebanType.RULEPUSH or session.users is None or len(session.users) <= 0:
            return

        #only ever one user in rulepush sessions
        session_user_id = session.users[0].user_id
        session_user_status = session.users[0].status

        if session_user_status != RolebanStatus.ACTIVE.value or session_user_id != message.author.id:
            return

        guessed_word: str = message.content.lower().strip()
        if len(guessed_word.split()) > 1:
            return await message.channel.send("I don't recognize that message! Please send each word separately and alone in its own message!", mention_author=False)

        try:
            updated, found_count, total = await self.rule_push_repo.mark_keyword_found_and_count(session.id, guessed_word)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error marking keyword found for rulepush session {session.id}: {err}")
            return await message.reply("Error while recording your answer. Try again.", mention_author=False)

        if updated == 0:
            return  # not a keyword or already found

        if found_count >= total:
            if session.start_time > 0:
                #make sure user metadata is up to date with users name
                try:
                    await self.user_metadata_repo.update_user_metadata(message.author.id, message.author.name)
                except sqlite3.Error as err:
                    self.bot.log.error(f"Error updating user_metadata for {message.author.id}: {err}")

                end_time = int(message.created_at.timestamp() * 1000)
                total_elapsed_millis = end_time - session.start_time
                rule_push_rank: str | None = None
                if total_elapsed_millis < MAX_MILLISECONDS_RULEPUSH_LEADERBOARD:
                    try:
                        rule_push_rank = await self.rule_push_leaderboard_repo.update_rule_push_leaderboard(message.author.id, total_elapsed_millis, int(message.created_at.timestamp()))
                    except sqlite3.Error as err:
                        self.bot.log.error(f"Error updating rulepush leaderboard for {message.author.id}: {err}")

                time_str = self.caclulate_completion_time(total_elapsed_millis)
                if rule_push_rank is None:
                    await message.channel.send(f"You finished with a time of **{time_str}**.")
                else:
                    await message.channel.send(f"You finished with a time of **{time_str}**. Your current rank is **{rule_push_rank}**.")

                await asyncio.sleep(5)

            ctx: commands.Context = await self.bot.get_context(message)
            released = await self.bot.roleban_service.unroleban_user(ctx, session, message.author.id, message.channel)
            if released:
                deleted_channel = await self.bot.roleban_service.delete_roleban_channel(channel=message.channel, reason="user completed rulepush", session_id=session.id, delete_session=True)
                if not deleted_channel:
                    return await message.channel.send("User was unrulepushed, but I was unable to delete the channel.", mention_author=False)
            else:
                return await message.channel.send("User finished rulepush, but I was unable to unrulepush them.", mention_author=False)
        else:
            return await message.reply(f"You've found a word. {found_count} out of {total} words found.", mention_author=False)

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Marks a session as 'left' so the user can't evade a rulepush by leaving"""
        await self.bot.wait_until_ready()
        try:
            session = await self.bot.roleban_service.get_roleban_session_by_user(member.guild.id, member.id)
        except sqlite3.Error as err:
            return self.bot.log.error(f"Error fetching rulepush session on member remove: {err}")

        if session is None or session.type is not RolebanType.RULEPUSH or session.users is None or len(session.users) <= 0:
            return

        # only ever one user in rulepush sessions
        session_user_id = session.users[0].user_id

        try:
            count_updated = await self.bot.roleban_service.update_user_session_status(session.id, session_user_id, RolebanStatus.LEFT)
        except sqlite3.Error as err:
            return self.bot.log.error(f"Error marking rulepush session {session.id} for user {session_user_id} as left: {err}")

        if count_updated <= 0:
            return

        try:
            await member.guild.fetch_ban(member)
            out = f"🔨 **{self.bot.pacify_name(str(member))}** got banned while rulepushed."
        except discord.NotFound:
            out = f"🚪 **{self.bot.pacify_name(str(member))}** left while rulepushed."
        except (discord.Forbidden, discord.HTTPException):
            out = (
                f"❓ **{self.bot.pacify_name(str(member))}** was removed from the server.\n"
                f"I was unable to determine why."
            )

        channel: discord.TextChannel = self.bot.get_channel(session.channel_id) if session.channel_id else None
        if channel:
            await channel.send(out)

        embed = stock_embed(self.bot)
        embed.title = "🚪 Rulepush Evasion?"
        embed.color = discord.Color.orange()
        embed.description = out

        return await self.bot.notification_service.send_notification(channel.guild, embed)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Resumes a rulepush for a user who left during a rulepush and rejoined"""
        await self.bot.wait_until_ready()
        guild = member.guild

        reactivated_session_info: tuple[discord.TextChannel, int, bool] | None = await self.bot.roleban_service.reactivate_user_session(guild, member, RolebanType.RULEPUSH)
        if reactivated_session_info is None:
            return

        channel, session_id, channel_recreated = reactivated_session_info

        if channel_recreated:
            # re-render the rules with the same keywords (but possibly in different positions) so progress carries over
            rules = None
            keywords = None
            try:
                rules = await self.rule_repo.get_rules(member.guild.id)
                found_keywords, not_found_keywords = await self.rule_push_repo.get_keywords_for_session(session_id)
                keywords = found_keywords + not_found_keywords
            except sqlite3.Error as err:
                self.bot.log.error(f"Error loading rules/keywords for user {member.id}: {err}")
                return await channel.send("error loading rules/keywords.")

            rendered_rules = render_rules(rules, keywords)
            if rendered_rules is None:
                return await channel.send("error loading rules/keywords.")

            rules_message = ""
            for rule in rendered_rules:
                if rule.rule_number < 0:
                    rules_message += f"**{rule.title}**\n{rule.content}"
                else:
                    rules_message += f"**Rule {rule.rule_number}. {rule.title}**\n{rule.content}"

            await self.send_long_message(channel, rules_message)

        await channel.send(f"🔁 {member.mention}, you left while a rulepush was in progress, so it has been resumed. Re-read the rules and type each hidden word that you find.", allowed_mentions=discord.AllowedMentions(users=True))

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        if user is None or user.id is None:
            return

        banned_user_info: TempBannedUser | None = await self.tempban_repo.get_banned_user_info(user.id, guild.id)
        if banned_user_info is not None:
            return

        try:
            await self.rule_push_leaderboard_repo.remove_user_from_leaderboard(user.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error removing user {user.id} from rule push leaderboard: {err}")

    async def confirm_action(self, ctx: commands.Context, channel: discord.abc.GuildChannel) -> bool:
        """Waits up to one minute for the invoking user to confirm they actually want to run this command

        Returns: true if this command should actually run, false otherwise"""
        await ctx.reply(
            "**WARNING: sensitive information. Do not invoke command in general chat**. Type `yes` to continue, or `no` to cancel. (I will wait 1 minute for your response before automatically cancelling the command)",
            mention_author=False)
        response: discord.Message = await self.bot.await_message(channel, ctx.author, 60)
        if response is None or response.content.lower() != "yes":
            await ctx.reply("command cancelled", mention_author=False)
            return False

        return True

    def caclulate_completion_time(self, completion_time: int) -> str:
        minutes, remainder_ms = divmod(completion_time, 60000)
        seconds = remainder_ms / 1000
        return f"{minutes}m, {seconds:.3f}s"

    @tasks.loop(minutes=10)
    async def kick_task(self):
        """Scheduled cron job task that runs every ten minutes. This job is responsible for
        informing rulepushed users at the 24 hour mark that they have 24 hours left to finish the rulepush.
        If the rulepush has met or exceeded the 48 hour mark, then the user is automatically kicked,
        and the rulepush channel is deleted."""
        try:
            for guild in self.bot.guilds:
                sessions: list[RolebanSession] | None = await self.bot.roleban_service.get_open_sessions(guild.id)

                if not sessions:
                    continue

                sessions = [session for session in sessions if session.type == RolebanType.RULEPUSH and session.users[0].status == RolebanStatus.ACTIVE.value]

                for session in sessions:
                    channel: discord.TextChannel = self.bot.get_channel(session.channel_id) if session.channel_id else None
                    if not channel:
                        continue

                    member: discord.Member = guild.get_member(session.users[0].user_id)
                    if member is None:
                        try:
                            member = await guild.fetch_member(session.users[0].user_id)
                        except Exception as e:
                            member = None

                    if check_if_target_is_staff(self.bot, member, self.bot.config_service):
                        continue

                    current_time = discord.utils.utcnow()
                    channel_age = current_time - channel.created_at
                    reminder_sent: bool = await self.rule_push_repo.get_rulepush_reminder(session.id)
                    if not reminder_sent and channel_age > timedelta(hours=24):
                        try:
                            limit = int((current_time + timedelta(hours=24)).timestamp())
                            await channel.send(f"<@{session.users[0].user_id}>, you have spent 24 hours without completing the rulepush."
                                               f"You have until <t:{limit}:f> (<t:{limit}:R>) before you will be automatically kicked.")
                            await self.rule_push_repo.update_rulepush_reminder(session.id, 1)
                        except Exception as err:
                            self.bot.log.error(f"Error while sending reminder for session {session.id}: {err}")
                    elif reminder_sent and channel_age > timedelta(hours=48):
                        try:
                            if member is not None:
                                await member.kick(reason=f"[Kick performed by Fluff] Rulepush time limit exceeded")
                            await self.rule_push_repo.update_rulepush_reminder(session.id, 0)
                            await self.bot.roleban_service.update_user_session_status(session.id, session.users[0].user_id, RolebanStatus.LEFT)

                            embed = stock_embed(self.bot)
                            embed.title = "Rulepush Session Closed (Fluff)"
                            embed.color = discord.Color.orange()
                            embed.description = f"`#{channel.name}`'s session was closed due to exceeding the maximum rulepush time limit"
                            await self.bot.notification_service.send_notification(channel.guild, embed)

                            return await channel.delete(reason="Channel closed for exceeding rulepush time limit")
                        except Exception as err:
                            self.bot.log.error(f"Error while kicking user from expired session {session.id}: {err}")
        except Exception as e:
            self.bot.log.error(f"Error performing rulepush kick task: {e}")

    @kick_task.before_loop
    async def before_kick_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(RulePush(bot))