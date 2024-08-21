import discord
from discord.ext.commands import Cog
from discord.ext import commands, tasks
from helpers.sv_config import get_config
from datetime import datetime, UTC
class Tenure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_joindelta(self, member):
        return (datetime.now(UTC) - member.joined_at).days
    
    @commands.group(invoke_without_command=True)
    async def tenure(self, ctx):
        tenure = await self.check_joindelta(ctx.author)
        return await ctx.reply(f"You last joined around {tenure} days ago.",mention_author=False)

    @Cog.listener()
    async def on_message(self, msg):
        await self.bot.wait_until_ready()
        if (
            msg.author.bot
            or msg.is_system()
            or not msg.guild
        ):
            return
        member = msg.author
        guild = msg.guild

        member_joindelta = (datetime.now(UTC) - member.joined_at).days
        

async def setup(bot):
    await bot.add_cog(Tenure(bot))