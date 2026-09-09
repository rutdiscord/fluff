import sqlite3

import discord
from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Cog

from database.model.StarboardQueue import StarboardQueue
from database.repository.starboard_channel_blacklist_repository import StarboardChannelBlacklistRepository
from database.repository.starboard_queue_repository import StarboardQueueRepository
from helpers.checks import ismod
from helpers.embeds import stock_embed
from helpers.message_link_embed import build_message_embed
from view.StarboardApprovalView import StarboardApprovalView

STAR_EMOJI = "⭐"
STAR_EMOJI_COUNT_THRESHOLD = 5
class Starboard(Cog):
    """Handles publishing starboard messages.

    When a message receives 5 star emoji reactions, the message is sent to the starboard queue channel.
    This channel allows staff members to either deny the starboard request, or accept the starboard request,
    in which case the message is automatically sent to the configured public starboard channel."""
    def __init__(self, bot):
        self.bot = bot
        self.starboard_queue_repo: StarboardQueueRepository = StarboardQueueRepository(self.bot.db)
        self.starboard_channel_blacklist_repo: StarboardChannelBlacklistRepository = StarboardChannelBlacklistRepository(self.bot.db)

    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def starboard(self, ctx: commands.Context):
        """This handles the starboard blacklist.

        Available commands:
        pls starboard - lists available commands
        pls starboard blacklist - lists channels that are blacklisted
        pls starboard blacklist add channel - adds a channel to the starboard blacklist
        pls starboard blacklist remove channel - removes a channel from the starboard blacklist

        - `channel`
        The channel to add/remove from the blacklist. Required."""
        return await ctx.reply(f"Use `pls starboard blacklist` to view blacklisted channels, and `pls starboard blacklist add/remove` to add or remove channels from the blacklist", mention_author=False)

    @starboard.group(name="blacklist", invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    async def blacklist(self, ctx: commands.Context):
        """This shows the blacklisted starboard channels.

        No arguments."""
        blacklisted_channel_ids: list[int] = await self.starboard_channel_blacklist_repo.get_blacklisted_channels()

        if not blacklisted_channel_ids:
            return await ctx.reply("No channels are blacklisted.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = "Blacklisted Starboard Channels"
        embed.color = ctx.author.color

        for channel_id in blacklisted_channel_ids:
            embed.add_field(
                name=f"<#{channel_id}>",
                value="",
                inline=False
            )

        return await ctx.reply(embed=embed, mention_author=False)

    @blacklist.command(name="add")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    async def blacklist_add(self, ctx: commands.Context, channel: discord.TextChannel):
        """Adds a channel to the starboard blacklist."""
        try:
            channel_added: bool = await self.starboard_channel_blacklist_repo.add_channel_to_blacklist(channel.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to add starboard channel to blacklist: {err}")
            return await ctx.reply("Error adding channel to blacklist table")

        if not channel_added:
            return await ctx.reply(f"{channel.mention} is already in the blacklist.", mention_author=False)

        return await ctx.reply(f"{channel.mention} was added to the starboard blacklist.", mention_author=False)

    @blacklist.command(name="remove")
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.check(ismod)
    async def blacklist_remove(self, ctx: commands.Context, channel: discord.TextChannel):
        """Removes a channel from the starboard blacklist."""
        try:
            channel_removed: bool = await self.starboard_channel_blacklist_repo.remove_channel_from_blacklist(channel.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to remove starboard channel from blacklist: {err}")
            return await ctx.reply("Error removing channel from blacklist table")

        if not channel_removed:
            return await ctx.reply(f"{channel.mention} is not in the blacklist.", mention_author=False)

        return await ctx.reply(f"{channel.mention} was removed from the starboard blacklist.", mention_author=False)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload is None or payload.guild_id is None or payload.channel_id is None or payload.message_id is None or payload.emoji is None or payload.member is None or payload.member.bot:
            return

        if str(payload.emoji) != STAR_EMOJI:
            return

        queue_channel_id: int = self.bot.config_service.get_server_config(payload.guild_id, "starboard", "queue_channel")
        starboard_channel_id: int = self.bot.config_service.get_server_config(payload.guild_id, "starboard", "starboard_channel")
        if queue_channel_id is None or starboard_channel_id is None:
            return

        queue_channel_id = int(queue_channel_id)
        starboard_channel_id = int(starboard_channel_id)

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.get_starboard_queue_entry_by_id(payload.message_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get starboard queue entry for message ID {payload.message_id}: {err}")
            return

        channel = await self.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            channel_id = payload.channel_id
            if isinstance(channel, discord.Thread):
                channel_id = channel.parent_id
            if await self.starboard_channel_blacklist_repo.is_channel_blacklisted(channel_id):
                return
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to check if channel is in starboard blacklist: {err}")
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException as e:
            self.bot.log.error(f"Failed to fetch message {payload.message_id}: {e}")
            return

        if not message or not message.reactions:
            return

        star_emoji_count = self.count_emojis(message)

        if starboard_queue_entry is not None:
            if starboard_queue_entry.starboard_message_id is None:
                return
            starboard_message_id = starboard_queue_entry.starboard_message_id
            starboard_channel = await self.get_channel(starboard_channel_id)
            if starboard_channel is None:
                return
            try:
                starboard_message = await starboard_channel.fetch_message(starboard_message_id)
                embeds = starboard_message.embeds
                embeds[0].set_footer(text=f"{STAR_EMOJI} {star_emoji_count}")
                await starboard_message.edit(embeds=embeds)
            except discord.HTTPException as e:
                self.bot.log.error(f"Failed to fetch message {starboard_message_id}: {e}")
                return

            return

        if star_emoji_count < STAR_EMOJI_COUNT_THRESHOLD:
            return

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.add_starboard_queue_entry(payload.message_id, channel.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to create starboard queue entry for message ID {payload.message_id}: {err}")
            return

        if starboard_queue_entry is None:
            return

        queue_channel: TextChannel = await self.get_channel(queue_channel_id)
        if queue_channel is None:
            return

        view = StarboardApprovalView(self.bot)
        embeds: list[discord.Embed] = await build_message_embed(message)
        queue_message = await queue_channel.send(embeds=embeds, view=view)

        try:
            await self.starboard_queue_repo.update_queue_message_id(payload.message_id, queue_message.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to update starboard queue entry for message ID {payload.message_id}: {err}")

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload is None or payload.guild_id is None or payload.channel_id is None or payload.message_id is None or payload.emoji is None:
            return

        if str(payload.emoji) != STAR_EMOJI:
            return

        starboard_channel_id: int = self.bot.config_service.get_server_config(payload.guild_id, "starboard", "starboard_channel")
        if starboard_channel_id is None:
            return

        starboard_channel_id = int(starboard_channel_id)

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.get_starboard_queue_entry_by_id(payload.message_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get starboard queue entry for message ID {payload.message_id}: {err}")
            return

        if starboard_queue_entry is None:
            return

        channel = await self.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException as e:
            self.bot.log.error(f"Failed to fetch message {payload.message_id}: {e}")
            return

        if not message:
            return

        star_emoji_count = self.count_emojis(message)

        if starboard_queue_entry.starboard_message_id is None:
            return

        starboard_message_id = starboard_queue_entry.starboard_message_id

        starboard_channel = await self.get_channel(starboard_channel_id)
        if starboard_channel is None:
            return
        try:
            starboard_message = await starboard_channel.fetch_message(starboard_message_id)
            embeds = starboard_message.embeds
            embeds[0].set_footer(text=f"{STAR_EMOJI} {star_emoji_count}")
            await starboard_message.edit(embeds=embeds)
        except discord.HTTPException as e:
            self.bot.log.error(f"Failed to fetch message {starboard_message_id}: {e}")
            return

    async def get_channel(self, channel_id: int) -> TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException as e:
                self.bot.log.error(f"Failed to fetch channel {channel_id}: {e}")
                return None

        return channel

    def count_emojis(self, message: discord.Message) -> int:
        for reaction in message.reactions:
            if reaction.emoji == STAR_EMOJI:
                return reaction.count

        return 0


async def setup(bot):
    await bot.add_cog(Starboard(bot))
    bot.add_view(StarboardApprovalView(bot))
