import discord
from discord.ext import commands

"""Helper class that ensures that the parameter that was passed is either a discord user mention or a user ID"""
class MentionOrIDMember(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        if not (argument.isdigit() or argument.startswith('<@')):
            raise commands.BadArgument("please use a user mention or user ID.")
        return await commands.MemberConverter().convert(ctx, argument)