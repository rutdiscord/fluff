import json
import discord
from discord.ext import commands
from discord.utils import snowflake_time
from helpers.datafiles import get_guildfile, set_guildfile
from helpers.sv_config import get_config
from helpers.checks import ismod, ismanager


class StickyMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stickied_cache = {
            # 'channelid': 'messageid'
        }

    def enabled(self, guild: discord.Guild) -> bool:
        stickied_channels = get_guildfile(guild.id, "stickied_messages")
        if not stickied_channels or stickied_channels == "{}":
            return False

        for channel_id in stickied_channels.keys():
            if guild.get_channel(int(channel_id)) is None:
                return False

        return True

    def snowflake_difference_in_minutes(self, snowflake1: int, snowflake2: int) -> int:
        time1 = snowflake_time(snowflake1)
        time2 = snowflake_time(snowflake2)
        difference = abs((time1 - time2).total_seconds())
        return int(difference // 60)

    # async def check_channel(
    #         self, guild: discord.Guild, channel: discord.abc.GuildChannel
    # ):
    #     stickied_channels = get_guildfile(guild.id, "stickied_messages")
    #     if

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["sticky"])
    async def stickies(self, ctx):
        """Run a report on the server's channels, and come back with any that have a stickied message.

        Anywhere in the guild.

        No arguments.
        """
        stickied_channels = get_guildfile(ctx.guild.id, "stickied_messages")
        if not stickied_channels:
            await ctx.send("There are no stickied messages in this server.")
            return

        response = "Stickied messages:\n\n"

        for channel_id, message in stickied_channels.items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                response += f"<#{channel.id}>: ```\n{message}\n```"
            else:
                response += f"Channel not found: {channel_id}\n"

        await ctx.send(response)

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @stickies.command()
    async def create(
        self, ctx: discord.abc.GuildChannel, channel: discord.abc.GuildChannel, msg: str
    ):
        """Create a stickied message in the specified channel.

        Anywhere in the guild.

        Channel mention, then the intended sticky message."""
        stickied_channels = get_guildfile(ctx.guild.id, "stickied_messages")
        if str(channel.id) not in stickied_channels:
            stickied_channels[str(channel.id)] = msg
            set_guildfile(
                ctx.guild.id, "stickied_messages", json.dumps(stickied_channels)
            )

            new_message = await channel.send(msg)
            self.stickied_cache[str(channel.id)] = new_message.id

            return await ctx.reply(
                f"Stickied message created in <#{channel.id}>:\n```\n{msg}\n```"
            )

        else:
            prev_msg = stickied_channels[str(channel.id)]
            stickied_channels[str(channel.id)] = msg
            set_guildfile(
                ctx.guild.id, "stickied_messages", json.dumps(stickied_channels)
            )
            return await ctx.reply(
                f"Stickied message updated in <#{channel.id}>:\nBefore:\n```\n{prev_msg}\n```\nAfter:\n```\n{msg}\n```"
            )

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @stickies.command()
    async def delete(
        self, ctx: discord.abc.GuildChannel, channel: discord.abc.GuildChannel
    ):
        stickied_channels = get_guildfile(ctx.guild.id, "stickied_messages")
        if str(channel.id) in stickied_channels:
            if str(channel.id) in self.stickied_cache:
                try:
                    cached_message_id = self.stickied_cache[str(channel.id)]
                    cached_message = await channel.fetch_message(cached_message_id)
                    await cached_message.delete()
                except discord.NotFound:
                    pass
                del self.stickied_cache[str(channel.id)]
            old_message = stickied_channels[str(channel.id)]
            del stickied_channels[str(channel.id)]
            set_guildfile(
                ctx.guild.id, "stickied_messages", json.dumps(stickied_channels)
            )
            await ctx.reply(
                f"Stickied message in <#{channel.id}> has been deleted. The previous message was:\n```\n{old_message}\n```"
            )
        else:
            await ctx.reply(f"No stickied message found in <#{channel.id}>.")

    @commands.bot_has_permissions(send_messages=True)
    @commands.check(ismanager)
    @commands.guild_only()
    @stickies.command()
    async def debug(self, ctx):
        if not self.stickied_cache:
            await ctx.send("The stickied message cache is currently empty.")
        else:
            response = "Stickied Message Cache:\n\n"
            for channel_id, message_id in self.stickied_cache.items():
                response += f"Channel ID: {channel_id}, Message ID: {message_id}\n"
            await ctx.send(f"```\n{response}\n```")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if not self.enabled(message.guild):
            return

        guild_stickied_threshold = (
            get_config(message.guild.id, "sticky", "fresh_stickied_threshold") or 10
        )  # Default to 0 if None

        stickied_channels = get_guildfile(message.guild.id, "stickied_messages")
        if str(message.channel.id) in stickied_channels:
            stickied_message = stickied_channels[str(message.channel.id)]
            print(
                f"Stickied message enabled for channel {message.channel.name} (ID: {message.channel.id})."
            )
            async for msg in message.channel.history(limit=100):
                if msg.content == stickied_message:
                    previous_sticky = msg
                    if (
                        self.snowflake_difference_in_minutes(
                            previous_sticky.id, message.id
                        )
                        > guild_stickied_threshold
                    ):
                        print(
                            f"Stickied message in channel {message.channel.name} (ID: {message.channel.id}) is older than the configured threshold. Operating on message."
                        )
                        await previous_sticky.delete()
                        new_message = await message.channel.send(stickied_message)
                        self.stickied_cache[str(message.channel.id)] = new_message.id
                        return True
            if str(message.channel.id) in self.stickied_cache:
                cached_message_id = self.stickied_cache[str(message.channel.id)]
                try:
                    cached_message = await message.channel.fetch_message(
                        cached_message_id
                    )
                except discord.NotFound:
                    print(
                        f"Cached stickied message for channel {message.channel.name} (ID: {message.channel.id}) not found. Creating new stickied message."
                    )
                    new_message = await message.channel.send(stickied_message)
                    self.stickied_cache[str(message.channel.id)] = new_message.id
            else:
                print(
                    f"Stickied message for channel {message.channel.name} (ID: {message.channel.id}) not found in cache. Creating new stickied message."
                )
                new_message = await message.channel.send(stickied_message)
                self.stickied_cache[str(message.channel.id)] = new_message.id


async def setup(bot):
    await bot.add_cog(StickyMessages(bot))
