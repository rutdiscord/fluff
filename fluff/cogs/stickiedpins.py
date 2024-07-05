import json
import os
import re
import discord
from discord.ext import commands, tasks
from helpers.placeholders import random_msg
from helpers.datafiles import get_guildfile, set_guildfile
from helpers.checks import ismod
from helpers.embeds import stock_embed, sympage

class StickiedPins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot        

    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def pins(self, ctx):
        # Setup regular expression

        guild_pins = get_guildfile(ctx.guild.id, "pins") 
        await ctx.reply(f"DEBUG LOL ({len(guild_pins)} pins in guild)", mention_author=False)
       
        for channel, message in guild_pins.items():
          #  fetched_channel = ctx.guild.fetch_channel(channel)
          #  print(f"")
          return
        
    @commands.bot_has_permissions(manage_messages=True)
    @commands.check(ismod)
    @commands.guild_only()
    @pins.command()
    async def create(self, ctx, msglink):
        message_link_regex = r"\/([0-9].*)\/([0-9].*)\/([0-9].*[^/])\/{0,}"
        regex_match = re.search(message_link_regex, msglink)
        link_matches = {}
        link_matches = {'channel': regex_match.group(2),  # Channel
                        'message': regex_match.group(3)}  # Message
                                                            # Removed the guild part because we can just assume from CTX...?
        guild_pins = get_guildfile(ctx.guild.id, "pins")
        channel_pins = None
        if link_matches["channel"] not in guild_pins:
            guild_pins[link_matches['channel']] = []
            channel_pins = guild_pins[link_matches['channel']]
        
        if link_matches['message'] in guild_pins[link_matches['channel']]:
            raise ValueError('Message to be pinned already exists in stickied messages.')
            
        channel_pins.append(link_matches['message'])
        set_guildfile(ctx.guild.id, "pins", json.dumps(guild_pins))

        try:
            if link_matches['message'] in guild_pins[link_matches['channel']]:
              return await ctx.reply(f"Stickied pin created in <#{link_matches['channel']}>.", mention_author=False)
        except Exception as reason:
            return await ctx.reply(f"Stickied pin failed to be created. {reason}")


    def update_pins(guild, channel):
        guild_pins = get_guildfile(guild.id, "pins")
        if channel.id in guild_pins:
            for pin in guild_pins[channel.id]:
                channel.fetch_message(pin)                
        else: 
            raise LookupError('Channel not found in pins, not bothering')
        
async def setup(bot):
   await bot.add_cog(StickiedPins(bot))