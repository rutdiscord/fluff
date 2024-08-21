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
    
    @commands.command()
    async def tenure(self, ctx):
        tenure = await self.check_joindelta(ctx.author)
        tenure_threshold = get_config(ctx.guild.id, "tenure", "threshold")
        tenure_role = ctx.guild.get_role(get_config(ctx.guild.id, "tenure", "role"))
        if not tenure_threshold or tenure_role:
            return await ctx.reply("Tenure is not configured on this server!", mention_author=False)
        if tenure_threshold < tenure:
            await ctx.reply(f"You joined around {tenure} days ago! You've been here long enough to be assigned the `",mention_author=False)

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