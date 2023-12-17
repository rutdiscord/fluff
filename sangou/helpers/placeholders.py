import random
import config
import discord
import datetime
import json

placeholders = json.load(open("assets/placeholders.json", "r"))
game_type = discord.ActivityType.listening
game_names = placeholders["games"]


def random_msg(variant, ctx):
    replacements = placeholders["shorthands"] | {"authorname": ctx.author.name}
    return random.choice(placeholders[variant]).format(**replacements)


def create_log_embed(bot, color, title, desc, author, fields, thumbnail=None):
    embed = discord.Embed(
        color=color,
        title=title,
        description=desc,
        timestamp=datetime.datetime.now(),
    )
    embed.set_footer(text=bot.user.name, icon_url=bot.user.display_avatar)
    embed.set_author(
        name=str(author),
        icon_url=author.display_avatar.url,
    )
    return embed