import discord
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.embeds import stock_embed, author_embed, sympage
from helpers.sv_config import get_config

# this entire page is made wholesale by marr so it looks like absolute shit, if anybody wants to come and fix it and make it function like the help command 
# where ppl can call individual commands linked to this feel free

class BunnyFacts(Cog):
    """
    Bunny facts!
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def bunfact(self, ctx):
            help_embed = stock_embed(self.bot)
            help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
            help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
            help_embed.add_field(name="Flopping", value="Is that bunny dead? (No)", inline=True)
            help_embed.add_field(name="Periscoping", value="Why he stand on his hind leg", inline=True)
            help_embed.add_field(name="Thumping", value="Why that loud noise", inline=True)
            help_embed.add_field(name="Chinning", value="Why is it rubbing its chin everywhere", inline=True)
            help_embed.add_field(name="Honking", value="Bunnies honk!?", inline=True)
            help_embed.add_field(name="Grunting", value="Bunnies grunt too!?", inline=True)
            help_embed.add_field(name="Boxing & Lunging", value="Bunnies box and lunge at each other!?", inline=True)
            help_embed.add_field(name="Getting a Bunny", value="Rescuing a bunny...", inline=True)
            await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="binky")
    async def binky(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))
