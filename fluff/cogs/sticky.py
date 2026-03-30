import sqlite3

import discord
from discord import Embed
from discord.ext import commands, tasks
from discord.ext.commands import Cog
import time
import io

from database.model.StickyMessage import StickyEntry
from database.repository.sticky_message_repository import StickyMessageRepository
from helpers.checks import ismod
from helpers.embeds import stock_embed

class StickyMessage(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_message_repo: StickyMessageRepository = StickyMessageRepository(self.bot.db)
        self.sticky_messages_by_server: dict[int, dict[int, StickyEntry]] = {} #server id -> {channel id -> Sticky message data}

    async def cog_load(self):
        self.sticky_messages_by_server = await self.sticky_message_repo.get_all_sticky_messages()
        self.sticky_task.start()

    async def cog_unload(self):
        self.sticky_task.cancel()

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    @commands.group(invoke_without_command=True)
    async def sticky(self, ctx: commands.Context, channel: discord.TextChannel | None = None):
        """Display sticky message information.

        If no channel is provided, lists all sticky messages in the server with a short preview.
        If a channel is provided, and the channel exists, displays the full sticky message for that channel.
        Available commands:
        pls sticky\npls sticky add/create #channel my sticky message\npls sticky update/modify #channel new message here
        pls sticky delete/remove #channel

        - `channel`
        The name of the channel that contains the sticky message to display. Optional.
        """
        embed = stock_embed(self.bot)
        embed.title = "Available Sticky Messages"
        embed.color = discord.Color.red()
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

        server_entries = self.sticky_messages_by_server.get(ctx.guild.id)
        if not server_entries:
            embed.add_field(
                name="No sticky messages",
                value="There are no sticky messages available in this server.",
                inline=True
            )
            return await self.send_sticky_server_embed(ctx, embed, server_entries)
        if not channel:
            self.insert_sticky_server_embed_data(ctx, embed, server_entries)
            return await self.send_sticky_server_embed(ctx, embed, server_entries)

        message_data = server_entries.get(channel.id)
        if message_data:
            return await ctx.reply(
                message_data.message,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )
        else:
            return await ctx.reply(
                f"no sticky messages available for {channel.name}",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none()
            )

    @sticky.command(aliases=["add"])
    @commands.guild_only()
    @commands.check(ismod)
    async def create(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        """Create a sticky message for a channel."""
        if ctx.guild.id not in self.sticky_messages_by_server:
            self.sticky_messages_by_server[ctx.guild.id] = {}
        if channel.id in self.sticky_messages_by_server[ctx.guild.id]:
            return await ctx.send("There is already a sticky message in that channel. Use `update` to overwrite the sticky message")

        try:
            await self.sticky_message_repo.create_sticky_message(ctx.guild.id, channel.id, message)
        except sqlite3.Error as e:
            self.bot.log.error(f"error inserting sticky message into the sticky_message table: {e}")
            return await ctx.send(f"Unable to create sticky message for {channel.mention}")

        self.sticky_messages_by_server[ctx.guild.id][channel.id] = StickyEntry(message, None)
        return await ctx.send(f"Sticky message set in {channel.mention}")

    @sticky.command(aliases=["modify"])
    @commands.guild_only()
    @commands.check(ismod)
    async def update(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        """Update an existing sticky message for a channel."""
        if ctx.guild.id not in self.sticky_messages_by_server:
            return await ctx.send(
                "There is no sticky message for this server")
        if channel.id not in self.sticky_messages_by_server[ctx.guild.id]:
            return await ctx.send(
                "There is no sticky message for that channel. Use `create` to create a new sticky message")

        try:
            await self.sticky_message_repo.update_sticky_message_content(ctx.guild.id, channel.id, message)
        except sqlite3.Error as e:
            self.bot.log.error(f"error updating sticky message field in the sticky_message table: {e}")
            return await ctx.send(f"Unable to update sticky message for {channel.mention}")

        message_id_to_update = self.sticky_messages_by_server[ctx.guild.id][channel.id].last_sticky_message_id
        if message_id_to_update is not None:
            try:
                current_message = await channel.fetch_message(self.sticky_messages_by_server[ctx.guild.id][channel.id].last_sticky_message_id)
                await current_message.edit(content=message)
            except (discord.NotFound, discord.HTTPException):
                pass

        self.sticky_messages_by_server[ctx.guild.id][channel.id].message = message
        return await ctx.send(f"Sticky message updated in {channel.mention}")

    @sticky.command(aliases=["remove"])
    @commands.guild_only()
    @commands.check(ismod)
    async def delete(self, ctx: commands.Context, channel: discord.TextChannel):
        """Delete an existing sticky message for a channel."""
        server_entries = self.sticky_messages_by_server.get(ctx.guild.id)
        if not server_entries:
            return await ctx.send("There are no sticky messages for this server")

        if channel.id not in server_entries:
            return await ctx.send("There is no sticky message set for that channel")

        if server_entries[channel.id].last_sticky_message_id is not None:
            try:
                previous_message = await channel.fetch_message(server_entries[channel.id].last_sticky_message_id)
                await previous_message.delete()
            except discord.NotFound:
                pass

        try:
            await self.sticky_message_repo.delete_sticky_message(ctx.guild.id, channel.id)
        except sqlite3.Error as e:
            self.bot.log.error(f"error deleting sticky message in the sticky_message table: {e}")

        del server_entries[channel.id]
        return await ctx.send(f"Sticky message removed in {channel.mention}")


    @tasks.loop(minutes=1)
    async def sticky_task(self):
        """Scheduled cron job task that runs every minute. This job is responsible for
        determining if a channel with a sticky message needs to re-send the message."""
        for server_id, server_sticky_messages in list(self.sticky_messages_by_server.items()):
            for channel_id, message_data in list(server_sticky_messages.items()):
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    continue

                latest_message = None
                try:
                    latest_message = await anext(channel.history(limit=1), None)
                except (discord.Forbidden, discord.HTTPException):
                    continue

                time_since_last_message = (
                    int(time.time()) - int(latest_message.created_at.timestamp())
                    if latest_message is not None
                    else 0
                )

                if latest_message is not None and latest_message.id == message_data.last_sticky_message_id:
                    continue
                if latest_message is None or time_since_last_message >= 300:
                    try:
                        await self.send_sticky_message(server_id, channel_id, channel, message_data)
                    except Exception as e:
                        self.bot.log.error(f"error attempting to send/save sticky message data: {e}")

    @sticky_task.before_loop
    async def before_sticky_task(self):
        await self.bot.wait_until_ready()

    async def send_sticky_message(self, server_id: int, channel_id: int, channel: discord.TextChannel, message_data: StickyEntry):
        """Sends a sticky message to a channel. If a previous sticky message exists, it is deleted before sending the new message."""
        if message_data.last_sticky_message_id is not None:
            try:
                previous_message = await channel.fetch_message(message_data.last_sticky_message_id)
                await previous_message.delete()
            except discord.NotFound:
                pass
        sent_message = await self.bot.get_channel(channel_id).send(message_data.message)
        try:
            await self.sticky_message_repo.update_sticky_message_sent_id(server_id, channel_id, sent_message.id)
        except sqlite3.Error as e:
            self.bot.log.error(f"error attempting to update sticky message entry in the database: {e}")
        self.sticky_messages_by_server[server_id][channel_id].last_sticky_message_id = sent_message.id

    def insert_sticky_server_embed_data(self, ctx: commands.Context, embed: Embed, server_entries: dict[int, StickyEntry]):
        """Inserts the necessary sticky message information into the embed object"""
        for channel_id, message_data in list(server_entries.items()):
            embed.add_field(
                name=f"**{ctx.guild.get_channel(channel_id)}**",
                value=(
                        "> "
                        + discord.utils.remove_markdown(
                    message_data.message[:60].replace("\n", " ")
                )
                ),
                inline=True
            )

    async def send_sticky_server_embed(self, ctx: commands.Context, embed: Embed, server_entries: dict[int, StickyEntry]):
        """Sends the constructed embed as a reply to the user. If there are too many fields inside the embed, then
        the embed is converted and sent as a file."""
        try:
            await ctx.reply(embed=embed, mention_author=False)
        except discord.errors.HTTPException as exception:  # Over 25 embed fields
            if exception.code == 50035:
                file_content = ""
                for channel_id, message_data in list(server_entries.items()):
                    file_content += f"\nChannel: {ctx.guild.get_channel(channel_id).name}\n" + (
                            "> "
                            + message_data.message
                            + "\n"
                    )
                await ctx.send(
                    file=discord.File(
                        io.StringIO(file_content),  # type:ignore
                        filename=f"stickies-{ctx.guild.id}.txt",
                    )
                )

async def setup(bot):
    await bot.add_cog(StickyMessage(bot))