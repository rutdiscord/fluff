# This is the initialization file for Fluff. You're meant to run this.

# Imports.
import os
import sys
import logging
import logging.handlers
import asyncio
import aiohttp
import config
import discord
import datetime
import itertools
from discord.ext import commands
from helpers.datafiles import get_botfile
from helpers.errors import handle_code_error, handle_command_error


# Setup temp dir
if not os.path.exists("temp"):
    os.makedirs("temp")

# Logging setup to file and stdout.
if not os.path.exists("logs"):
    os.makedirs("logs")
log_format = logging.Formatter(
    "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(log_format)
logfile_handler = logging.FileHandler("logs/fluff.log", mode="w")
logfile_handler.setFormatter(log_format)
log = logging.getLogger("discord")
log.setLevel(logging.INFO)
log.addHandler(stdout_handler)
log.addHandler(logfile_handler)


# Utility functions.
def cap_permutations(s):
    # thank you to https://stackoverflow.com/a/11165671
    lu_sequence = ((c.lower(), c.upper()) for c in s)
    return ["".join(x) for x in itertools.product(*lu_sequence)]


def get_prefix(bot, message):
    prefixes = []
    for prefix in config.prefixes:
        prefixes += cap_permutations(prefix)
    userprefixes = [] #get_userprefix(message.author.id)
    if userprefixes is not None:
        return commands.when_mentioned_or(*prefixes + userprefixes)(bot, message)
    return commands.when_mentioned_or(*prefixes)(bot, message)


# Bot setup.
intents = discord.Intents.all()
intents.typing = False
intents.presences = False

bot = commands.Bot(
    command_prefix=get_prefix,
    description=config.short_desc,
    owner_ids=set(config.managers),
    intents=intents,
    enable_debug_events=True,
)
bot.help_command = None
bot.log = log
bot.config = config
bot.errors = []
bot.version = "0.5.0"


# Bot listeners.
@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    bot.start_timestamp = int(datetime.datetime.now().timestamp())
    log.info(
        f"Fluff version {bot.version} is logged in as {bot.user} ({bot.user.id}) running discord.py version {discord.__version__}"
    )


@bot.event
async def on_command(ctx):
    log_text = (
        f'{ctx.message.author} ({ctx.message.author.id}) used "{ctx.message.content}" '
        + (
            f'in "#{ctx.channel.name}" ({ctx.channel.id}) on "{ctx.guild.name}" ({ctx.guild.id})'
            if ctx.guild
            else f"in DMs ({ctx.channel.id})"
        )
    )
    log.info(log_text)


@bot.event
async def on_message(message):
    await bot.wait_until_ready()

    if message.author.bot:
        return
    if (
        "botban" in get_botfile("botusers")
        and message.author.id in get_botfile("botusers")["botban"]
    ):
        return

    ctx = await bot.get_context(message)
    if not ctx.valid:

        def check(b, a):
            return a.id == message.id

        while True:
            if ctx.valid:
                break
            try:
                author, message = await bot.wait_for(
                    "message_edit", timeout=15.0, check=check
                )
            except (asyncio.TimeoutError, discord.errors.NotFound):
                return
            else:
                ctx = await bot.get_context(message)
                if ctx.valid:
                    break
    await bot.invoke(ctx)


@bot.event
async def on_error(event_method, *args, **kwargs):
    await handle_code_error(bot, event_method, args, kwargs)


@bot.event
async def on_command_error(ctx, error):
    await handle_command_error(bot, ctx, error)


# Bot startup.
async def main():
    async with bot:
        for cog in [
            "cogs." + f[:-3]
            for f in os.listdir("cogs/")
            if os.path.isfile("cogs/" + f) and f[-3:] == ".py"
        ]:
            try:
                await bot.load_extension(cog)
            except:
                log.exception(f"Failed to load cog {cog}.")
        await bot.start(config.token)


if __name__ == "__main__":
    asyncio.run(main())
