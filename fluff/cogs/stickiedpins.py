import sqlite3

import discord
from discord.ext import commands

from database.model.StickiedPin import StickiedPin
from database.repository.stickied_pins_repository import StickiedPinsRepository
from helpers.checks import ismod
from helpers.embeds import stock_embed


class StickiedPins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stickied_pins_repo: StickiedPinsRepository = StickiedPinsRepository(self.bot.db)

    async def update_pins(
        self, channel: discord.abc.GuildChannel
    ):
        stickied_pins: list[StickiedPin] = []
        try:
            stickied_pins = await self.stickied_pins_repo.get_all_stickied_pins()
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching stickied pins: {err}")
            return

        for stickied_pin in stickied_pins:
            if channel.id == stickied_pin.channel_id:
                channel: discord.TextChannel = self.bot.get_channel(stickied_pin.channel_id)
                if channel is None:
                    continue

                message = await channel.fetch_message(stickied_pin.message_id)

                if message.pinned:
                    await message.unpin()
                await message.pin()

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["pin"])
    async def pins(self, ctx: commands.Context):
        stickied_pins: list[StickiedPin] = []
        try:
            stickied_pins = await self.stickied_pins_repo.get_all_stickied_pins()
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching stickied pins: {err}")

        if not stickied_pins:
            return await ctx.reply("No stickied pins found.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = "Stickied Pins"
        embed.color = ctx.author.color

        for stickied_pin in stickied_pins:
            channel: discord.TextChannel = self.bot.get_channel(stickied_pin.channel_id)
            link = f"https://discord.com/channels/{ctx.guild.id}/{stickied_pin.channel_id}/{stickied_pin.message_id}"
            embed.add_field(
                name=f"{channel.name}",
                value=link,
                inline=True
            )

        return await ctx.reply(embed=embed, mention_author=False)

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @pins.command()
    async def create(self, ctx: discord.abc.GuildChannel, msg: discord.Message):
        stickied_pin_added: bool = False
        try:
            stickied_pin_added: bool = await self.stickied_pins_repo.create_stickied_pin(msg.channel.id, msg.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error creating stickied pin: {err}")
            return await ctx.reply("Error adding stickied pin.", mention_author=False)

        if not stickied_pin_added:
            return await ctx.reply(f"Stickied pin already exists.", mention_author=False)

        await self.update_pins(msg.channel)

        return await ctx.reply(f"Stickied pin created in <#{msg.channel.id}>.", mention_author=False)

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @pins.command()
    async def delete(self, ctx: discord.abc.GuildChannel, msg: discord.Message):
        stickied_pin_deleted: bool = False
        try:
            stickied_pin_deleted: bool = await self.stickied_pins_repo.delete_stickied_pin(msg.channel.id, msg.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error deleting stickied pin: {err}")
            return await ctx.reply("Error deleting stickied pin.", mention_author=False)

        if not stickied_pin_deleted:
            return await ctx.reply(f"That message was not pinned..", mention_author=False)

        await self.update_pins(msg.channel)

        return await ctx.reply(f"Stickied pin deleted from <#{msg.channel.id}>.", mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if all(
            [
                message.guild != None,
                message.type == discord.MessageType.pins_add,
                message.author != self.bot.user,
            ]
        ):

            await self.update_pins(message.channel)


async def setup(bot):
    await bot.add_cog(StickiedPins(bot))
