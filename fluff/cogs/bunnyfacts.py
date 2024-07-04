import discord
import random
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.embeds import stock_embed, author_embed, sympage
from helpers.sv_config import get_config

# this entire page is made wholesale by marr so it looks like absolute shit

class BunnyFacts(Cog):
    """
    Bunny facts!
    """

    def __init__(self, bot):
        self.bot = bot
        self.image_urls = {
            "binky": [
                "https://media-be.chewy.com/wp-content/uploads/2022/05/24112223/rabbit-binkying.gif",
                "https://global.discourse-cdn.com/business5/uploads/gemsofwar/original/3X/8/4/84364684586e83b84361ea90fce93dae8d0888d7.gif",
                "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/93c11ea7-9de5-46e6-a1d7-b613cf57e399/d9753cz-e8e8a691-6bc2-4bfb-a9b3-af87a62809af.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzkzYzExZWE3LTlkZTUtNDZlNi1hMWQ3LWI2MTNjZjU3ZTM5OVwvZDk3NTNjei1lOGU4YTY5MS02YmMyLTRiZmItYTliMy1hZjg3YTYyODA5YWYuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0._B1a6DK7z1wDt50Ml0xWlyZN6BRDJBRyhviGmTHf4c8",
                "https://elizabethannemartins.com/wp-content/uploads/2016/05/tumblr_mn7spsxk191ss93ulo1_400.gif?w=350&h=276",
                "https://files.catbox.moe/m8us2w.gif",
                "https://files.catbox.moe/p2fg1y.gif"
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
