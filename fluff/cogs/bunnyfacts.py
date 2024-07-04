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
            ],
            "flopping": [
                "https://live.staticflickr.com/2541/4222032144_9d2be8fdaa_b.jpg",
                "https://i.ytimg.com/vi/BNusKhdWYPw/maxresdefault.jpg",
                "https://files.catbox.moe/eezsl8.webp",
                "https://files.catbox.moe/vko0fw.webp",
                "https://files.catbox.moe/j13oqw.jpg"
            ],
            "periscoping": [

            ],
            "thumping": [

            ],
            "chinning": [

            ],
            "honking": [

            ],
            "grunting": [

            ],
            "boxing": [

            ],
            "getting": [

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
        help_embed.add_field(name="Binky", value="When a rabbit does a weird twist and jump in the air, it\'s called a binky. Rabbits do this when they have so much happy energy that they just can\'t contain it. A binkying bunny is a very happy bunny!\n**Why do rabbits binky?**\n We don\'t really know why rabbits binky. All we know is that it\'s a normal instinct in rabbits. It\'s like an inexplicable expression of joy, much like laughing is for humans.\n[Link](https://bunnylady.com/bunny-binkies/)", inline=False)
        random_image = random.choice(self.image_urls.get("binky",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="flopping", aliases = ["flop"])
    async def flopping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Flopping", value="In most cases, a rabbit laying on their side is just sleeping. They aren\'t sick or dying in any way. Instead, this is a position rabbits will sleep in when they feel completely safe and secure in their environment.\n**Why do rabbits flop?**\nSince rabbits are at the bottom of the food chain, they need to be prepared to run away at the first sign of danger. When they sleep like this, rabbits cannot come to awareness and get up as quickly as other sleeping positions. Moreover, rabbits tend to sleep more deeply when they lay on their sides, not waking up as easily as when they sleep in a loaf position. This means that they need to have a high amount of trust in you before they\'ll be willing to flop over to sleep.\n[Link](https://bunnylady.com/laying-on-their-side/)", inline=True)
        random_image = random.choice(self.image_urls.get("flopping",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="periscoping")
    async def periscoping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Periscoping", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("periscoping",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="thumping", aliases = ["thump"])
    async def thumping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Thumping", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("thumping",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="chinning", aliases = ["chin"])
    async def chinning(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Chinning", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("chinning",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="honking", aliases = ["honk"])
    async def honking(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Honking", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("honking",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="grunting", aliases = ["grunt"])
    async def grunting(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Grunting", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("grunting",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="boxinglunging", aliases = ["boxing", "lunging"])
    async def boxinglunging(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Boxing & Lunging", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("boxing",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="getting", aliases = ["get"])
    async def getting(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Getting a Rabbit", value="Not yet implemented...", inline=True)
        random_image = random.choice(self.image_urls.get("getting",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))
