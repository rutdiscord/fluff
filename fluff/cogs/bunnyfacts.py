import discord
import random
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
        self.image_urls = {
            "binky" [
                "https://media-be.chewy.com/wp-content/uploads/2022/05/24112223/rabbit-binkying.gif",
                "https://global.discourse-cdn.com/business5/uploads/gemsofwar/original/3X/8/4/84364684586e83b84361ea90fce93dae8d0888d7.gif"
            ]
        }

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

    @bunfact.command(name="binky", aliases = ["binkying"])
    async def binky(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="People unfamiliar to pet rabbits may not know that bunnies have a very dramatic way of expressing excitement and joy. They dance! Leaping in the air, contorting and twisting their bodies, and kicking their feet out, binkying rabbits are quite the spectacle. Sometimes rabbits lead up to a binky by taking a running start. Other times, a binky is a sudden burst to the side. What\'s really fun is when the binkies occur in succession, creating a grand acrobatic display. \n[Link](https://myhouserabbit.com/rabbit-behavior/binkies-nose-bonks-and-flops-bunny-behavior-explained/)", inline=False)
        random_image = random.choice(self.image_urls.get("binky",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="flopping", aliases = ["flop"])
    async def flopping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="periscoping")
    async def periscoping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="thumping", aliases = ["thump"])
    async def thumping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="chinning", aliases = ["chin"])
    async def chinning(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="honking", aliases = ["honk"])
    async def honking(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="grunting", aliases = ["grunt"])
    async def grunting(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Binky", value="What is a binky!?", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))
