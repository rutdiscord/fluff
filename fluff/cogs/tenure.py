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
    print(msg)
    # return await modlog_channel.send(f"♾ **{member.global_name}** (**{member.id}**) has been in this server since {datetime.now() - member.joined_at}")
        

async def setup(bot):
    await bot.add_cog(Tenure(bot))