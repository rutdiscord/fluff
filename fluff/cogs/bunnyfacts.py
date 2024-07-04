import discord
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.embeds import stock_embed, author_embed, sympage
from helpers.sv_config import get_config

class BunnyFacts(Cog):
    """
    Bunny facts!
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def bunfact(self, ctx, *, fact=None):
        """This is Fluff's bunny facts command.

        Giving the fact name will show that fact's description.

        - `fact name`
        The fact to see. Optional."""
        if not fact:
            help_embed = stock_embed(self.bot)
            help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
            help_embed.add_field(name="Test1", value="test1", inline=True)
            help_embed.add_field(name="Test2", value="test2", inline=True)
            help_embed.add_field(name="Test3", value="test3", inline=True)
            help_embed.add_field(name="Test4", value="test4", inline=False)
            help_embed.add_field(name="Test5", value="test5", inline=True)
            help_embed.add_field(name="Test6", value="test6", inline=True)
            help_embed.add_field(name="Test7", value="test7", inline=True)
            help_embed.add_field(name="Test8", value="test8", inline=False)
            help_embed.add_field(name="Test9", value="test9", inline=True)
            help_embed.add_field(name="Test10", value="test10", inline=True)
            help_embed.add_field(name="Test11", value="test11", inline=True)
            return await ctx.reply(embed=help_embed,mention_author=False)
        else:
            botcommand = self.bot.get_fact(fact)
            if not botcommand:
                return await ctx.reply(
                    "This isn't a configured bunny fact.",
                    mention_author=False,
                )
async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))
