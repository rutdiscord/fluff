import json
import discord
from discord.ext import commands
from helpers.datafiles import get_guildfile, set_guildfile
from helpers.checks import ismod, ismanager


class StickyMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(StickiedPins(bot))
