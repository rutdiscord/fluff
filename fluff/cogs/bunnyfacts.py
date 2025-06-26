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
                    "https://global.discourse-cdn.com/business5/uploads/gemsofwar/original/3X/8/4/84364684586e83b84361ea90fce93dae8d0888d7.gif",
                    "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/93c11ea7-9de5-46e6-a1d7-b613cf57e399/d9753cz-e8e8a691-6bc2-4bfb-a9b3-af87a62809af.gif?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7InBhdGgiOiJcL2ZcLzkzYzExZWE3LTlkZTUtNDZlNi1hMWQ3LWI2MTNjZjU3ZTM5OVwvZDk3NTNjei1lOGU4YTY5MS02YmMyLTRiZmItYTliMy1hZjg3YTYyODA5YWYuZ2lmIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmZpbGUuZG93bmxvYWQiXX0._B1a6DK7z1wDt50Ml0xWlyZN6BRDJBRyhviGmTHf4c8",
                    "https://elizabethannemartins.com/wp-content/uploads/2016/05/tumblr_mn7spsxk191ss93ulo1_400.gif?w=350&h=276",
                    "https://files.catbox.moe/m8us2w.gif",
                    "https://files.catbox.moe/p2fg1y.gif",
                },
                "fact": "A funky little jump along with a flick of the back legs (or head, if it's a smaller binky!). It's a way rabbits express excess energy they can't contain, usually joy. A binkying bunny is a very happy bunny!\n\n**Why do rabbits binky?**\n Nobody really knows why rabbits binky. All we know is that it's an instinct, an inexplicable expression of joy, much like laughing is for humans.\n\n Baby rabbits binky more often than adult rabbits - they're more energetic while adults are generally sleepier and calmer. Like puppies!\n[Link](https://bunnylady.com/bunny-binkies/)",
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
                "fact": "In most cases, a rabbit laying on their side is just sleeping. They aren't sick or dying in any way. Instead, this is a position rabbits will sleep in when they feel completely safe and secure in their environment.\n**Why do rabbits flop?**\nSince rabbits are at the bottom of the food chain, they need to be prepared to run away at the first sign of danger. When they sleep like this, rabbits cannot come to awareness and get up as quickly as other sleeping positions. Moreover, rabbits tend to sleep more deeply when they lay on their sides, not waking up as easily as when they sleep in a loaf position. This means that they need to have a high amount of trust in you before they'll be willing to flop over to sleep.\n[Link](https://bunnylady.com/laying-on-their-side/)",
            },
            "periscoping": {
                "summary": "Why he stand on his hind leg",
                "images": {
                    "https://files.catbox.moe/dzgwnr.jpg",
                    "https://farm2.static.flickr.com/1069/1473341276_980253934b.jpg",
                    "https://files.catbox.moe/qc50g5.jpg",
                    "https://www.budgetbunny.ca/wp-content/uploads/2013/09/IMG_6163-510x729.gif",
                },
                "fact": "This is when a rabbit stands on their hind legs, it means they are curious and are trying to get a better vantage point. They often beg for treats like this.\n[Link](https://bunnylady.com/rabbit-care-guide/)",
            },
            "thumping": {
                "summary": "Why that loud noise",
                "images": {"https://tenor.com/view/bunny-thumper-thump-rabbit-tantrum-gif-18111178"},
                "fact": "When a rabbit thumps their hind legs against the ground. This means that a rabbit senses danger or is very upset with something.\n[Link](https://bunnylady.com/rabbit-care-guide/)\n[Link to Video](https://www.youtube.com/watch?v=g9kiuQ1pql8)",
            },
            "chinning": {
                "summary": "Why is it rubbing its chin everywhere",
                "images": {
                    "https://64.media.tumblr.com/f2dc3fbe0834c9903e48a2c6818ed3d7/tumblr_o8158dq9Wh1uronh1o1_400.gif"
                },
                "fact": "",
            },
            "honking": {"summary": "Bunnies honk!?", "images": {""}, "fact": ""},
            "grunting": {"summary": "Bunnies grunt too!?", "images": {""}, "fact": ""},
            "boxing": {
                "summary": "Bunneis box and lunge at each other!?",
                "images": {"https://files.catbox.moe/2zk4ql.gif"},
                "fact": "",
            },
            "purring": {"summary": "They can puur!?", "images": {""}, "fact": ""},
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
