import discord
import random
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.embeds import stock_embed, author_embed, sympage
from helpers.sv_config import get_config

# this entire page is made wholesale by marr so it looks like absolute shit
# its kind of just coding practice but educating is fun too

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
                "https://files.catbox.moe/dzgwnr.jpg",
                "https://farm2.static.flickr.com/1069/1473341276_980253934b.jpg",
                "https://files.catbox.moe/qc50g5.jpg",
                "https://www.budgetbunny.ca/wp-content/uploads/2013/09/IMG_6163-510x729.gif",
            ],  
            "chinning": [
                "https://64.media.tumblr.com/f2dc3fbe0834c9903e48a2c6818ed3d7/tumblr_o8158dq9Wh1uronh1o1_400.gif"
            ],
            "boxing": [
                "https://files.catbox.moe/2zk4ql.gif"
            ],
        }

#this displays the list of bunfacts

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
            help_embed.add_field(name="Purring", value="They can purr!?", inline=True)
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
        help_embed.add_field(name="Periscoping", value="This is when a rabbit stands on their hind legs, it means they are curious and are trying to get a better vantage point. They often beg for treats like this.\n[Link](https://bunnylady.com/rabbit-care-guide/)", inline=True)
        random_image = random.choice(self.image_urls.get("periscoping",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="thumping", aliases = ["thump"])
    async def thumping(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Thumping", value="When a rabbit thumps their hind legs against the ground. This means that a rabbit senses danger or is very upset with something.\n[Link](https://bunnylady.com/rabbit-care-guide/)\n[Link to Video](https://www.youtube.com/watch?v=g9kiuQ1pql8)", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="chinning", aliases = ["chin"])
    async def chinning(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Chinning", value="The rabbit will rub their chin against an object to claim it as their own. Rabbits have scent glands under their chins, so this spreads their scent around and lets any other rabbits know that this is your rabbit\'s territory.", inline=True)
        random_image = random.choice(self.image_urls.get("chinning",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="honking", aliases = ["honk"])
    async def honking(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Honking", value="Honking is often a sign of pleasure. Some bunnies honk when they are eating, getting treats, getting attention, or snuggling.\nIt can also be a hormonal behavior in unfixed rabbits.\n[Link](https://www.rabbithaven.org/vocalizations)\n[Link to Video](https://www.youtube.com/watch?v=9d8JViSZ9vY)", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="grunting", aliases = ["grunt"])
    async def grunting(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Grunting", value="Rabbits grunting usually means they're angry and possibly feel threatened. Sometimes, the grunting is followed by a nip or bite. Some rabbits do not like it when you rearrange their cages as you clean. So they might grunt, charge, or even nip you when you try.\n[Link](https://bestfriends.org/pet-care-resources/pet-rabbit-body-language-and-bunny-behavior)\n[Link to Video](https://www.youtube.com/watch?v=OycSzdxCKQE)", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="boxinglunging", aliases = ["boxing", "lunging"])
    async def boxinglunging(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Boxing & Lunging", value="Boxing and lunging are aggressive behaviors. A rabbit will stand on their hind legs and punch with their front legs as if to “box” you or lunge at you. A rabbit may exhibit this behavior if they are frightened or uncomfortable with you entering their territory and touching their belongings.\nThose aren't rabbits in the gif but same behavior - boxing.\n[Link](https://www.thinkingoutsidethecage.org/understanding-rabbit-body-language/)", inline=True)
        random_image = random.choice(self.image_urls.get("boxing",[]))
        help_embed.set_image(url=random_image)
        await ctx.reply(embed=help_embed,mention_author=False)

    @bunfact.command(name="purring", aliases = ["purr"])
    async def getting(self, ctx):
        help_embed = stock_embed(self.bot)
        help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        help_embed.add_field(name="Purring", value="This is when the rabbit gently grinds their teeth together, making a soft vibration in their head. Sometimes it even makes an audible sound. This is called a purr because, although the mechanism is different, it means the same thing as a cat\'s purr. Your rabbit is calm and content.\n[Link](https://bunnylady.com/bunny-binkies/)\n[Link to Video](https://www.youtube.com/watch?v=PvRBpY55JmE)", inline=True)
        await ctx.reply(embed=help_embed,mention_author=False)

async def setup(bot):
    await bot.add_cog(BunnyFacts(bot))