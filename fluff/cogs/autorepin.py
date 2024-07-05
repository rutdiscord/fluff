import discord
from discord.ext import commands, tasks
import json
import os
import re
from helpers.placeholders import random_msg

class Autorepin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def repin(self, ctx, msglink):
        # Setup regular expression
        message_link_regex = r"\/([0-9].*)\/([0-9].*)\/([0-9].*[^/])\/{0,}"
        regex_match = re.search(message_link_regex, msglink)
        link_matches = {}

        try:
            link_matches = {'guild': regex_match.group(1), # Guild
                        'channel': regex_match.group(2),  # Channel
                        'message': regex_match.group(3)} # Message
            return await ctx.reply(f"Guild: {link_matches[0]}\nChannel:{link_matches[1]}\nMessage:{link_matches[2]}")
        except (AttributeError, KeyError):
            return await ctx.reply(random_msg("err_generic") + ("(Regex failed to find a valid message link)"))


async def setup(bot):
   await bot.add_cog(Autorepin(bot))