import discord
from discord.ext import commands, tasks
import json
import os
import re

class Autorepin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def repin(self, ctx, msglink):
        message_link_regex = r"\/([0-9].*)\/([0-9].*)\/([0-9].*[^/])\/{0,}"
        link_matches = re.findall(message_link_regex, msglink)
        if len(link_matches) > 0:
            return await ctx.reply(f"Guild: {link_matches[0]}\nChannel:{link_matches[1]}\nMessage:{link_matches[2]}")
        else:
            return await ctx.reply("No matches were found.. time to cry!!")


def setup(bot):
    bot.add_cog(Autorepin(bot))