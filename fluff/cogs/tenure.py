import discord
from discord.ext.commands import Cog
from discord.ext import commands, tasks
from helpers.sv_config import get_config
from helpers.checks import ismanager, isadmin
from datetime import datetime, timedelta, UTC
from config import logchannel
class Tenure(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nocfgmsg = "Tenure isn't configured for this server.."
    
    async def check_joindelta(self, member: discord.Member):
        return (datetime.now(UTC) - member.joined_at)
    
    def enabled(self, guild: discord.Guild):
        return all(
        (
            self.bot.pull_role(guild, get_config(guild.id, "tenure", "role")),
            get_config(guild.id, "tenure", "threshold") >= 0,
        )
        )
    
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def tenure(self, ctx):
        """This shows the user their tenure in the server.
        
        Any guild channel that has Tenure configured.

        No arguments."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        
        tenure_dt = await self.check_joindelta(ctx.author)
        tenure_days = tenure_dt.days
        tenure_threshold = get_config(ctx.guild.id, "tenure", "threshold")
        tenure_role = self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "tenure", "role"))

        if tenure_threshold < tenure_days:
           if tenure_role not in ctx.author.roles:
            await ctx.author.add_roles(tenure_role, reason="Fluff Tenure")
            return await ctx.reply(f"You joined around {tenure_days} days ago! You've been here long enough to be assigned the {tenure_role.name} role!",mention_author=False)
           else:
            await ctx.reply(f"You joined around {tenure_days} days ago, and you've already been assigned the {tenure_role.name} role!",mention_author=False)
        else:
            await ctx.reply(f"You joined around {tenure_days} days ago! Not long enough, though.. try again in {(timedelta(days=tenure_threshold)-tenure_dt).days} days!",mention_author=False)
    
    @commands.check(ismanager)
    @tenure.command()
    async def force_sync(self,ctx):
       """THIS WILL FORCEFULLY SYNCHRONIZE THE SERVER MEMBERS WITH THE TENURE ROLE.

       THIS IS VERY TIME CONSUMING.

       RUN ONCE, NEVER AGAIN.
       """
       if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
       tenure_threshold = get_config(ctx.guild.id, "tenure", "threshold")
       tenure_role = self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "tenure", "role"))
       await ctx.reply("Oh boy..", mention_author=False)

       for member in ctx.guild.members:
            tenure_dt = await self.check_joindelta(member)
            tenure_days = tenure_dt.days
            print(f"{member.global_name} ({member.id}) joined {tenure_days} ago")



    # @Cog.listener()
    # async def on_message(self, msg):
    #     await self.bot.wait_until_ready()
    #     if (
    #         msg.author.bot
    #         or msg.is_system()
    #         or not msg.guild
    #     ):
    #         return
    #     member = msg.author
    #     guild = msg.guild

    #     member_joindelta = (datetime.now(UTC) - member.joined_at).days
        

async def setup(bot: discord.Client):
    await bot.add_cog(Tenure(bot))