import discord
import asyncio
from discord.ext.commands import Cog
from discord.ext import commands
from helpers.sv_config import get_config

class NoSticker(Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_tenurerole(self, guild: discord.Guild):
        return self.bot.pull_role(guild, get_config(guild.id, "tenure", "role"))
    
    def enabled(self, guild: discord.Guild):
        return all(
        (
            self.bot.pull_role(guild, get_config(guild.id, "tenure", "role")),
            get_config(guild.id, "tenure", "threshold"),
        )
        )
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        await self.bot.wait_until_ready()
        if (
            msg.author.bot
            or msg.is_system()
            or not msg.guild
        ):
            return print("Ignoring message")
        
        if not self.enabled(msg.guild):
            return print("Tenure not even enabled here")
        
        tenure_role = self.get_tenurerole(msg.guild)
        print(tenure_role not in msg.author.roles, msg.stickers)
        if tenure_role not in msg.author.roles and msg.stickers:
            return await msg.delete()

async def setup(bot: discord.Client):
   await bot.add_cog(NoSticker(bot))