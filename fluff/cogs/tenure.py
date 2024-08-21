import discord
from discord.ext.commands import Cog
from discord.ext import commands, tasks
from helpers.sv_config import get_config
from datetime import datetime
class Tenure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

@Cog.listener()
async def on_message(self, msg):
    await self.bot.wait_until_ready()
    member = msg.member
    guild = msg.guild

    modlog_channel = self.bot.pull_channel(
            guild, get_config(guild.id, "logging", "modlog")
            )
    
    if not member.bot:
        await modlog_channel.send(f"♾ **{member.global_name}** (**{member.id}**) has been in this server since {datetime.now() - member.joined_at}")
        

def setup(bot):
    bot.add_cog(Tenure(bot))