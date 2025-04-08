import json
import discord
from discord.ext import commands
from helpers.datafiles import get_guildfile, set_guildfile
from helpers.checks import ismod, ismanager


class StickiedPins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_pins(
        self, guild: discord.Guild, channel: discord.abc.GuildChannel
    ):
        guild_pins = get_guildfile(guild.id, "pins")
        if str(channel.id) in guild_pins:
            for pin in guild_pins[str(channel.id)]:
                message = await channel.fetch_message(pin)

                if message.pinned:
                    await message.unpin()
                await message.pin()
        else:
            return False

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True, aliases=["pin", "sticky"])
    async def pins(self, ctx):
        guild_pins = get_guildfile(ctx.guild.id, "pins")

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @pins.command()
    async def create(self, ctx: discord.abc.GuildChannel, msg: discord.Message):
        guild_pins = get_guildfile(ctx.guild.id, "pins")
        if str(msg.channel.id) not in guild_pins:
            guild_pins[str(msg.channel.id)] = []
        channel_pins = guild_pins[str(msg.channel.id)]

        if msg.id in channel_pins:
            return await ctx.reply(
                f"Stickied pin already exists in channel: {msg.jump_url}",
                mention_author=False,
            )
        else:
            channel_pins.append(msg.id)
            set_guildfile(ctx.guild.id, "pins", json.dumps(guild_pins))
            return await ctx.reply(
                f"Stickied pin created in <#{msg.channel.id}>.", mention_author=False
            )
        # await msg.channel.pins()
        # guild_pins = get_guildfile(ctx.guild.id, "pins")
        # channel_pins = None
        # if str(msg.channel.id) not in guild_pins:
        #     guild_pins[str(msg.channel.id)] = {}
        #     channel_pins = guild_pins[str(msg.channel.id)]

        # if msg.id in guild_pins[str(msg.channel.id)]:
        #     return await ctx.reply(f"Stickied pin already exists in channel: {msg.jump_url}", mention_author=False)

        # channel_pins.append(msg.id)
        # set_guildfile(ctx.guild.id, "pins", json.dumps(guild_pins))

        # try:
        #     if msg.id in guild_pins[str(msg.channel.id)]:
        #       self.update_pins(ctx.guild, msg.channel)
        #       return await ctx.reply(f"Stickied pin created in <#{msg.channel.id}>.", mention_author=False)
        # except Exception as reason:
        #     return await ctx.reply(f"Stickied pin failed to be created. {reason}")

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismanager)
    @commands.guild_only()
    @pins.command()
    async def force_update(
        self,
        ctx: discord.abc.GuildChannel,
        target_channel: discord.abc.GuildChannel = None,
    ):
        guild = ctx.guild
        channel = target_channel or ctx.channel
        return await self.update_pins(guild, channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if all(
            [
                message.guild != None,
                message.type == discord.MessageType.pins_add,
                message.author != self.bot.user,
            ]
        ):

            await self.update_pins(message.guild, message.channel)


async def setup(bot):
    await bot.add_cog(StickiedPins(bot))
