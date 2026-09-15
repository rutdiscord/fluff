from discord.ext import commands
import discord

class GuildContext(commands.Context):
    guild: discord.Guild
    author: discord.Member
