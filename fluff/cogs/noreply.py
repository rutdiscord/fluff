import sqlite3
import textwrap
from collections import deque
from datetime import datetime, timezone

import discord, asyncio
from discord.ext.commands import Cog
from discord.ext import commands, tasks

from database.repository.ping_violation_acknowledgement_repository import PingViolationAcknowledgementRepository
from database.repository.whitelist_ping_repository import WhitelistPingRepository
from model.ReplyPing import ReplyPing

REPLY_PING = "pleasereplyping"
NO_REPLY_PING = "noreplyping"
PING_AFTER_DELAY = "waitbeforereplyping"
WHITELIST_PING = "whitelistping"
GHOST_PING_WINDOW_SECONDS = 180

class Reply(Cog):
    """
    Handles reply ping preferences and violations
    """

    def __init__(self, bot):
        self.bot = bot
        self.whitelist_ping_repo: WhitelistPingRepository = WhitelistPingRepository(self.bot.db)
        self.ping_violation_ack_repo: PingViolationAcknowledgementRepository = PingViolationAcknowledgementRepository(self.bot.db)
        self.violations: dict[int, dict[int, deque[int]]] = {} #server ID -> dict[user ID -> double ended queue of timestamps when the user violated a ping preference]
        self.recent_reply_pings: dict[int, ReplyPing] = {} #message ID -> ReplyPing
        self.timers = {}
        self.mode_enabled = False

    async def cog_load(self):
        self.cleanup_violations.start()

    async def cog_unload(self):
        self.cleanup_violations.cancel()

    def get_ping_preference(self, message: discord.Message) -> str | None:
        """Fetches the users ping preference, if it exists"""
        if not message.guild:
            return None
        setting_roles = [
            (self.bot.pull_role(message.guild, "Please Ping"), REPLY_PING),
            (
                self.bot.pull_role(message.guild, "Ping after Delay"),
                PING_AFTER_DELAY,
            ),
            (
                self.bot.pull_role(message.guild, "Whitelist Ping"),
                WHITELIST_PING
            ),
            (self.bot.pull_role(message.guild, "No Ping"), NO_REPLY_PING),
        ]
        for role, identifier in setting_roles:
            if role is None:
                continue
            elif role in message.author.roles:
                return identifier
        return None

    # marr is pissed off mode
    @commands.command(name='pissedmode')
    async def pissedmode(self, ctx):
        if ctx.author.id != 212719295124209664:
            await ctx.send ("You cannot use this command. Only Marr can use this command.")
            return 
        self.mode_enabled = not self.mode_enabled
        status = "enabled" if self.mode_enabled else "disabled"
        await ctx.send(f"Pissed off mode is now {status}.")

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()

        if (
            message.author.bot
            or message.is_system()
            or not message.guild
            or not message.reference
            or message.type != discord.MessageType.reply
        ):
            return

        try:
            refmessage = await message.channel.fetch_message(
                message.reference.message_id
            )
            if (
                refmessage.author.id == message.author.id
                or not message.guild.get_member(refmessage.author.id)
            ):
                return
        except:
            return

        ref_author_mentioned: bool = refmessage.author in message.mentions
        if ref_author_mentioned:
            # we want to keep track of reply pings from the last 3 minutes in order to warn users who
            # delete the reply ping, causing a ghost ping
            self.recent_reply_pings[message.id] = ReplyPing(message.author.id, refmessage.author.id, int(message.created_at.timestamp()))

        preference = self.get_ping_preference(refmessage)
        if not preference:
            return

        # If not reply pinged...
        if preference == REPLY_PING and not ref_author_mentioned:
            return await self.handle_please_ping(message, refmessage)
        # If reply pinged with no_reply_ping role,
        # or reply pinged with whitelist_ping role, and user is not in the pinged users whitelist
        elif (
                (preference == NO_REPLY_PING and ref_author_mentioned) or
                (preference == WHITELIST_PING and ref_author_mentioned and
                 not await self.is_user_whitelisted(refmessage.author.id, message.author.id)
                )
        ):
            return await self.handle_do_not_ping(message, preference)
        # If reply pinged in a window of time...
        elif (
            preference == PING_AFTER_DELAY
            and ref_author_mentioned
        ):
            return await self.handle_wait_before_ping(message, refmessage)

    @Cog.listener()
    async def on_message_delete(self, message: discord.PartialMessage):
        reply_ping_msg: ReplyPing | None = self.recent_reply_pings.pop(message.id, None)
        if reply_ping_msg is None:
            return

        current_timestamp: int = int(datetime.now(tz=timezone.utc).timestamp())
        if (current_timestamp - reply_ping_msg.reply_ping_timestamp) <= GHOST_PING_WINDOW_SECONDS:
            message_str: str = f"<@{reply_ping_msg.message_author_id}> DO NOT quick delete a reply ping message. This leaves a ghost ping that the pinged user cannot find.\n"
            sent_message = await message.channel.send(content=message_str)
            await asyncio.sleep(0.5)
            await sent_message.edit(content=message_str + f"<@{reply_ping_msg.message_author_id}> mentioned <@{reply_ping_msg.ref_message_author_id}> but deleted the message.")


    async def is_user_whitelisted(self, pinged_user_id: int, pinged_by_id: int) -> bool:
        """Returns whether the pinged_by user is in the pinged users whitelist"""
        try:
            return await self.whitelist_ping_repo.is_user_in_whitelist(pinged_user_id, pinged_by_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error checking if {pinged_by_id} is in {pinged_user_id}'s whitelist")
            return True #fail open

    async def handle_please_ping(self, message: discord.Message, refmessage: discord.Message):
        """Handler for user with please ping role and they were not pinged

        Args:
            message: the message that is replying to the reference message
            refmessage: the reference message
        """
        try:
            please_ping_emoji: str = self.bot.config_service.get_server_config(message.guild.id, "reaction", "please_ping_emoji")
            if please_ping_emoji is not None:
                await message.add_reaction(f"<{please_ping_emoji}>")
        except discord.errors.NotFound:
            pass
        except discord.errors.Forbidden as err:
            if err.code == 90001:
                pass
        pokemsg = await message.reply(
            content=refmessage.author.mention, mention_author=False
        )
        await self.bot.await_message(message.channel, refmessage.author, 86400)
        return await pokemsg.delete()

    async def handle_do_not_ping(self, message: discord.Message, preference: str):
        """Handler for user with do not ping role, or user with whitelist ping role, and the pinged
         by user is not in the pinged users whitelist

        Args:
            message: the message that is replying to the reference message
            preference: the ping preference of the pinged by user
        """
        try:
            if preference == NO_REPLY_PING:
                no_ping_emoji: str = self.bot.config_service.get_server_config(message.guild.id, "reaction", "no_ping_emoji")
                if no_ping_emoji is not None:
                    await message.add_reaction(f"<{no_ping_emoji}>")
            elif preference == WHITELIST_PING:
                whitelist_ping_emoji: str = self.bot.config_service.get_server_config(message.guild.id, "reaction", "whitelist_ping_emoji")
                if whitelist_ping_emoji is not None:
                    await message.add_reaction(f"<{whitelist_ping_emoji}>")
        except discord.errors.NotFound:
            await message.channel.send(
                f"*thump thump* {message.author.mention} Quickdeleting a message that violates ping preferences is not cool!",
                delete_after=5.0,
            )
        except discord.errors.Forbidden as err:
            if err.code == 90001:
                return self.bot.dispatch(
                    "autotoss_blocked", message, message.author
                )
        return await self.handle_violation(message)

    async def handle_wait_before_ping(self, message: discord.Message, refmessage: discord.Message):
        """Handler for user with wait before reply ping role

        Args:
            message: the message that is replying to the reference message
            refmessage: the reference message
        """
        if message.guild.id not in self.timers:
            self.timers[message.guild.id] = {}
        self.timers[message.guild.id][refmessage.author.id] = int(
            refmessage.created_at.timestamp()
        )
        if (
                int(message.created_at.timestamp()) - 30
                <= self.timers[message.guild.id][refmessage.author.id]
        ):
            try:
                wait_ping_emoji: str = self.bot.config_service.get_server_config(message.guild.id, "reaction", "wait_ping_emoji")
                if wait_ping_emoji is not None:
                    await message.add_reaction(f"<{wait_ping_emoji}>")
            except discord.errors.NotFound:
                await message.channel.send(
                    f"*thump thump* {message.author.mention} Quickdeleting a message that violates ping preferences is not cool!",
                    delete_after=5.0,
                )
            except discord.errors.Forbidden as err:
                if err.code == 90001:
                    return self.bot.dispatch(
                        "autotoss_blocked", message, message.author
                    )
            return await self.handle_violation(message)

    async def handle_violation_acknowledgement(self, message: discord.Message):
        """Sends the user a temporary discord DM explaining the violation rules, and stores
        the resulting acknowledgement in the ping acknowledgement table"""
        temp_reminder_msg = await message.author.send(
            content="**Please do not reply ping users who do not wish to be pinged.**\n"
                    + "This incident will be excused, but further incidents will be counted as **violations**. (Reply to this message or wait sixty seconds to acknowledge)",
            file=discord.File("assets/noreply.png"),
            mention_author=False,
        )

        def wait_check(new_msg):
            return new_msg.author == message.author and isinstance(
                new_msg.channel, discord.DMChannel
            )

        try:
            await self.bot.wait_for("message", timeout=60, check=wait_check)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            await temp_reminder_msg.delete()

        try:
            await self.ping_violation_ack_repo.add_user_acknowledgement(message.guild.id, message.author.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error adding ping violation acknowledgement for user ID: {message.author.id}: {err}")

    async def handle_violation(self, message: discord.Message):
        """Handles the process of giving the user a violation and reminding them of their current violation count

        Args:
            message: the message that is violating a users ping preference
        """
        remind_frequency: int | None = self.bot.config_service.get_server_config(message.guild.id, "reaction", "noreply_remind_every")
        if remind_frequency is None:
            return
        remind_frequency = min(remind_frequency, 3)

        violation_threshold: int | None = self.bot.config_service.get_server_config(message.guild.id, "reaction", "noreply_threshold")
        if violation_threshold is None:
            return
        violation_threshold = min(violation_threshold, 10)

        try:
            await self.add_violation(message, remind_frequency, violation_threshold)
        except discord.errors.Forbidden:
            if not (
                message.channel.permissions_for(message.guild.me).add_reactions
                and message.channel.permissions_for(message.guild.me).manage_messages
                and message.channel.permissions_for(message.guild.me).moderate_members
            ):
                return

            cur_violation_count: int = self.increment_and_get_user_violation_count(message)
            if (
                cur_violation_count > 1
                and cur_violation_count % remind_frequency == 0
            ):
                try:
                    await message.reply(content=textwrap.dedent(f"""**{message.author.mention}, You have me blocked, or you have DMs disabled!**
                                        **Do not reply ping users who do not wish to be pinged.**
                                        You have currently received {cur_violation_count} violation(s).
                                        {violation_threshold} violations will result in a penalty.""").strip(),
                                        file=discord.File("assets/noreply.png"))
                except discord.errors.NotFound:
                    return await message.channel.send(
                        content=f"{message.author.mention} immediately deleted their own message.\n{message.author.display_name} now has `{cur_violation_count}` violation(s)."
                    )

    async def add_violation(self, message: discord.Message, remind_frequency: int, violation_threshold: int):
        """Adds the violation to the user, in addition to checking if the user needs to be tossed

        Args:
            message: the message that is violating a users ping preference
            remind_frequency: the frequency at which the user should be reminded about their ping violations
            violation_threshold: the number of violations at which the user will be tossed
        """
        staff_roles = [
            self.bot.pull_role(
                message.guild, self.bot.config_service.get_server_config(message.guild.id, "staff", "modrole")
            ),
            self.bot.pull_role(
                message.guild, self.bot.config_service.get_server_config(message.guild.id, "staff", "adminrole")
            ),
        ]
        if (
            not any(staff_roles)
            or any([staff_role in message.author.roles for staff_role in staff_roles])
            or await self.bot.is_owner(message.author)
        ):
            return

        message_author = message.author
        message_guild = message.guild

        has_user_acknowledged: bool = await self.has_user_acknowledged(message_guild.id, message_author.id)
        if not has_user_acknowledged:
            return await self.handle_violation_acknowledgement(message)

        violation_count: int = self.increment_and_get_user_violation_count(message)

        modlog_channel = self.bot.pull_channel(
            message.guild, self.bot.config_service.get_server_config(message_guild.id, "logging", "modlog")
        )

        async def notify_modlog(additional=None):
            return await modlog_channel.send(
                f":infinity: **{message_author.global_name}** (**{message_author.id}**) has received a reply ping preference violation. Their current violation count is {violation_count}. ({additional})"
            )

        try:
            if violation_count == (violation_threshold - 1):
                await notify_modlog(additional="Next violation will result in penalty.")

                await message.reply(
                    content=textwrap.dedent(f"""# {message.author.mention}, your next violation will result in penalty.
                    You have currently received {str(violation_count)} violations.
                    As a reminder, **please respect ping preferences, and do not reply ping users who do not wish to be pinged**.""").strip(),
                    file=discord.File("assets/noreply.png"))

            elif (violation_count % remind_frequency) == 0:
                await notify_modlog("Reminder sent.")
                return await message.author.send(
                    content="**Do not reply ping users who do not wish to be pinged.**\n"
                    + f"You have currently received {str(violation_count)} violations.\n"
                    + f"{violation_threshold} violations will result in a penalty.",
                    file=discord.File("assets/noreply.png"),
                )
            elif violation_count >= violation_threshold:
                return self.bot.dispatch(
                    "violation_threshold_reached", message, message.author
                )
        except ZeroDivisionError:
            return

    async def has_user_acknowledged(self, server_id: int, user_id: int) -> bool:
        """Checks the ping violation acknowledgement table to determine if the user has already acknowledged the ping violation rules"""
        try:
            return await self.ping_violation_ack_repo.has_user_acknowledged(server_id, user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error attempting to check ping violation acknowledgement for user ID {user_id}: {err}")
        return True

    def increment_and_get_user_violation_count(self, message: discord.Message) -> int:
        """Adds a violation to the internal user violation dict, and returns the users updated violation count"""
        if message.guild.id not in self.violations:
            self.violations[message.guild.id] = {}

        if message.author.id not in self.violations[message.guild.id]:
            self.violations[message.guild.id][message.author.id] = deque()

        message_created_timestamp: int = int(message.created_at.timestamp())
        one_hour_ago_timestamp: int = message_created_timestamp - 3600

        violations_deque: deque[int] = self.violations[message.guild.id][message.author.id]
        violations_deque.append(message_created_timestamp)

        # remove any old timestamps. there can be a minute delay before the
        # cron job task cleans up the old timestamps, and we want to be accurate
        while violations_deque and violations_deque[0] <= one_hour_ago_timestamp:
            violations_deque.popleft()

        return len(violations_deque)

    @tasks.loop(minutes=1)
    async def cleanup_violations(self):
        try:
            current_timestamp: int = int(datetime.now(tz=timezone.utc).timestamp())
            one_hour_ago_timestamp: int = current_timestamp - 3600

            for guild_id, users in self.violations.items():
                user_ids_to_remove: list[int] = []
                for user_id, timestamps in users.items():
                    while timestamps and timestamps[0] < one_hour_ago_timestamp:
                        timestamps.popleft()
                    if len(timestamps) == 0:
                        user_ids_to_remove.append(user_id)

                for user_id in user_ids_to_remove:
                    del users[user_id]

            message_ids_to_remove: list[int] = []
            for message_id, reply_ping in self.recent_reply_pings.items():
                if (current_timestamp - reply_ping.reply_ping_timestamp) > GHOST_PING_WINDOW_SECONDS:
                    message_ids_to_remove.append(message_id)

            for message_id in message_ids_to_remove:
                del self.recent_reply_pings[message_id]

        except Exception as e:
            #should not happen but safeguarding so task doesnt stop
            self.bot.log.error(f"Error cleaning up violations: {str(e)}")

    @cleanup_violations.before_loop
    async def before_cleanup_violations(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Reply(bot))
