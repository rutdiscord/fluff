import random
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.embeds import stock_embed

# i rewrote it :3


class BunnyFacts(Cog):
    """
    Bunny facts!
    """

    def __init__(self, bot):
        self.bot = bot

        self.facts = {
            "binky": {
                "summary": "'An inexplicable expression of joy...'",
                "images": {
                    "https://media-be.chewy.com/wp-content/uploads/2022/05/24112223/rabbit-binkying.gif",
                    "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/93c11ea7-9de5-46e6-a1d7-b613cf57e399/d9753cz-e8e8a691-6bc2-4bfb-a9b3-af87a62809af.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzkzYzExZWE3LTlkZTUtNDZlNi1hMWQ3LWI2MTNjZjU3ZTM5OVwvZDk3NTNjei1lOGU4YTY5MS02YmMyLTRiZmItYTliMy1hZjg3YTYyODA5YWYuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0._B1a6DK7z1wDt50Ml0xWlyZN6BRDJBRyhviGmTHf4c8",
                    "https://elizabethannemartins.com/wp-content/uploads/2016/05/tumblr_mn7spsxk191ss93ulo1_400.gif?w=350&h=276",
                    "https://files.catbox.moe/m8us2w.gif",
                    "https://files.catbox.moe/p2fg1y.gif",
                    "https://files.catbox.moe/hoh0xv.gif",
                    "https://files.catbox.moe/6jmpus.gif",
                    "https://files.catbox.moe/pxrfil.gif",
                    "https://files.catbox.moe/3rbnjk.gif",
                    "https://files.catbox.moe/bxh2im.gif",
                    "https://files.catbox.moe/nw1qid.gif",
                    "https://files.catbox.moe/6we66x.gif",
                    "https://files.catbox.moe/fxuect.gif",
                    "https://files.catbox.moe/n9dc5d.gif",
                    "https://files.catbox.moe/wgcmvs.gif",
                    "https://files.catbox.moe/rvipql.gif",
                },
                "fact": "A funky little jump along with a flick of the back legs (or head, if it's a smaller binky!). It's a way rabbits express excess energy they can't contain, usually joy. A binkying bunny is a very happy bunny!",
            },
            "flopping": {
                "summary": "Is that bunny dead? (no)",
                "images": {
                    "https://live.staticflickr.com/2541/4222032144_9d2be8fdaa_b.jpg",
                    "https://i.ytimg.com/vi/BNusKhdWYPw/maxresdefault.jpg",
                    "https://files.catbox.moe/eezsl8.webp",
                    "https://files.catbox.moe/vko0fw.webp",
                    "https://files.catbox.moe/j13oqw.jpg",
                },
                "fact": "Bunnies will flop over on their sides when they feel safe and able to relax. When a bunny flops, it means they are comfortable and trust their environment (which often contains you!)",
            },
            "periscoping": {
                "summary": "Why do bunnies stand on their hind legs?",
                "images": {
                    "https://files.catbox.moe/dzgwnr.jpg",
                    "https://farm2.static.flickr.com/1069/1473341276_980253934b.jpg",
                    "https://files.catbox.moe/qc50g5.jpg",
                    "https://www.budgetbunny.ca/wp-content/uploads/2013/09/IMG_6163-510x729.gif",
                },
                "fact": "This behavior is often called 'periscoping'. Bunnies will stand on their hind legs to get a better view of their surroundings. They do this to investigate their environment to see if there are any potential dangers or interesting things to explore. This behavior is similar to how some animals, like meerkats, will stand on their hind legs to look around.",
            },
            "thumping": {
                "summary": "Why do bunnies thump their feet?",
                "images": {"https://files.catbox.moe/bwri44.gif",
                           "https://files.catbox.moe/i12b9v.webp",
                           "https://files.catbox.moe/9qkql8.gif",},
                "fact": "Rabbits will thump when they're scared or annoyed. They thump to warn other rabbits of danger or to express their displeasure with something.",
            },
            "chinning": {
                "summary": "Why do bunnies rub their chins on things?",
                "images": {
                    "https://64.media.tumblr.com/f2dc3fbe0834c9903e48a2c6818ed3d7/tumblr_o8158dq9Wh1uronh1o1_400.gif",
                    "https://files.catbox.moe/0d7ir4.gif",
                    "https://files.catbox.moe/c3lblc.gif",
                },
                "fact": "Rabbits have scent glands under their chin, and they will rub their chin on objects to mark them with their scent. This is a way for them to claim ownership of their territory and belongings. Sometimes they will also do this to show affection to their owners or other rabbits.",
            },
            "honking": {
                "summary": "Do bunnies honk?",
                "images": {
                    ""
                }, 
                "fact": "Rabbits will make a noise when they are excited or happy. This noise is often described as a honking sound. It tends to be a sign of affection."
            },
            "grunting": {
                "summary": "Do bunnies grunt?",
                "images": {
                ""
                },
                "fact": "Rabbits will grunt when they are annoyed or angry. This noise is often accompanied by a thump. It is a way for them to express their displeasure with something or someone.",
            },
            "boxing": {
                "summary": "Do bunnies fight?",
                "images": {"https://files.catbox.moe/2zk4ql.gif"},
                "fact": "Rabbits will box as a way to establish dominance or defend themselves.\nIn the gif below, these are jackrabbits, which are a type of hare. Regardless, rabbits do the same thing.",
            },
            "purring": {
                "summary": "Bunnies can pur!",
                "images": {""}, 
                "fact": "Rabbits can purr too! They make this sound by lightly chattering their teeth together. This is a sign of contentment and affection."},
        }

    @commands.group(invoke_without_command=True, aliases=["bunfacts", "bunnyfacts"])
    async def bunfact(self, ctx: commands.Context):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(
            name="Fluff",
            url="https://github.com/dfault-user/fluff",
            icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&",
        )

        for key, value in self.facts.items():
            help_embed.add_field(
                name=key.capitalize(), value=value["summary"], inline=True
            )

        await ctx.reply(embed=help_embed, mention_author=False)

    @bunfact.command(name="binky", aliases=["binkying"])
    async def binky(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="flopping", aliases=["flop"])
    async def flopping(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="periscoping", aliases=[])
    async def periscoping(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="thumping", aliases=["thump"])
    async def thumping(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="chinning", aliases=["chin"])
    async def chinning(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="honking", aliases=["honk"])
    async def honking(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="grunting", aliases=["grunt"])
    async def grunting(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="boxing", aliases=["box", "lunge", "lunging"])
    async def boxing(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)

    @bunfact.command(name="purring", aliases=["purr"])
    async def purring(self, ctx: commands.Context):
        fact = self.facts.get(ctx.command.name, [])
        fact_embed = stock_embed(self.bot)

        if "images" in fact:
            images = fact["images"]
            image = random.choice(list(images))
            fact_embed.set_image(url=image)

        fact_embed.title = ctx.command.name.capitalize()
        fact_embed.description = fact["fact"]
        await ctx.send(embed=fact_embed)


async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))
