import time
import discord
import os
import io
import asyncio
import matplotlib
import matplotlib.pyplot as plt
import typing
import random
import platform
import hashlib
import zlib
from datetime import datetime, timezone
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.checks import ismod
from helpers.embeds import stock_embed, author_embed, sympage
from helpers.datafiles import fill_profile
from zoneinfo import ZoneInfo, available_timezones
import aiohttp
import re as ren
import html
import json


class Basic(Cog):
    def __init__(self, bot):
        self.bot = bot
        matplotlib.use("agg")

    @commands.command()
    async def choose(self, ctx, *options):
        """This will choose something at random for you.

        It's not weighted, it's completely random between
        all possible options you give.

        - `options`
        A list of options, separated by spaces."""
        return await ctx.send(f"You should `{random.choice(options)}`!")

    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(aliases=["timer"])
    async def eggtimer(self, ctx, minutes: int = 5):
        """This starts a timer.

        It'll react to your message, then ping you
        once the timer is done. Max an hour, default five minutes.

        - `minutes`
        How long you want the timer to be. Optional."""
        if minutes > 60:
            return await ctx.reply(
                "I'm not making a timer longer than an hour.", mention_author=False
            )
        time = minutes * 60
        await ctx.message.add_reaction("⏳")
        await asyncio.sleep(time)
        await ctx.message.remove_reaction("⏳", self.bot.user)
        msg = await ctx.channel.send(content=ctx.author.mention)
        await msg.edit(content="⌛", delete_after=5)

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def avy(self, ctx, target: discord.User = None):
        """This gets a user's avatar.

        If you don't specify anyone, it'll show your
        pretty avy that you have on right now.

        - `target`
        Who you wish to show the avy of. Optional."""
        if target is not None:
            if ctx.guild and ctx.guild.get_member(target.id):
                target = ctx.guild.get_member(target.id)
        else:
            target = ctx.author
        await ctx.send(content=target.display_avatar.url)

    @commands.bot_has_permissions(embed_links=True)
    @avy.command(name="server")
    async def _server(self, ctx, target: discord.Guild = None):
        """This gets a server's avatar.

        You *could* get another server's avatar with
        this if you know its ID, and the bot is on it.
        Otherwise it shows the current server's avy.

        - `target`
        The server you want to see the avy of. Optional."""
        if target is None:
            target = ctx.guild
        return await ctx.send(content=target.icon.url)

    @commands.command(aliases=["catbox", "imgur"])
    async def rehost(self, ctx, links=None):
        """This uploads a file to catbox.moe.

        These files won't expire, ever. Please respect
        their free service that they offer!
        You can also use an attachment.

        - `links`
        The links to reupload to catbox."""
        api_url = "https://catbox.moe/user/api.php"
        if not ctx.message.attachments and not links:
            return await ctx.reply(
                content="You need to supply a file or a file link to rehost.",
                mention_author=False,
            )
        links = links.split() if links else []
        for r in [f.url for f in ctx.message.attachments] + links:
            formdata = aiohttp.FormData()
            formdata.add_field("reqtype", "urlupload")
            if self.bot.config.catbox_key:
                formdata.add_field("userhash", self.bot.config.catbox_key)
            formdata.add_field("url", r)
            async with self.bot.session.post(api_url, data=formdata) as response:
                output = await response.text()
                await ctx.reply(content=output, mention_author=False)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def about(self, ctx):
        """This shows the bot info."""
        embed = discord.Embed(
            title=self.bot.user.name,
            url=self.bot.config.source_url,
            description=self.bot.config.long_desc,
            color=ctx.guild.me.color if ctx.guild else self.bot.user.color,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name=f"📊 Usage",
            value=f"**Guilds:** {len(self.bot.guilds)}\n**Users:** {len(self.bot.users)}",
            inline=True,
        )
        embed.add_field(
            name=f"⏱️ Uptime",
            value=f"{self.bot.user.name} started on <t:{self.bot.start_timestamp}:F>, or <t:{self.bot.start_timestamp}:R>.",
            inline=True,
        )
        embed.add_field(
            name=f"📡 Unit",
            value=f"Running {platform.python_implementation()} {platform.python_version()} on {platform.platform(aliased=True, terse=True)} {platform.architecture()[0]}.",
            inline=True,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    async def help(self, ctx, *, command=None):
        """This is Fluff's help command.

        Giving a `command` will show that command's help.
        Running this command by itself shows a link to the documentation.

        - `command`
        The command to get help on. Optional."""
        if not command:
            help_embed = stock_embed(self.bot)
            help_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
            help_embed.add_field(name="Image Hosting", value="Use `pls rehost`, `pls imgur`, or `pls catbox` with an attachment or link to host that attachment forever. Please respect the service.", inline=False)
            help_embed.add_field(name="Join Graph", value="`pls joingraph` shows a graph of users who have joined.", inline=False)
            help_embed.add_field(name="Join Score", value="`pls joinscore` shows when you joined in comparison to other users.", inline=False)
            help_embed.add_field(name="Rule Snippets", value="`pls rule` will display a list of rule snippets. You can individually call them with their names, `pls rule [name]`. Useful for people who are confused about the rules!")
            help_embed.add_field(name="Ping Preferences", value="`pls pingconfig` will allow you to change your ping preferences, AKA whether you'd like to be pinged always, never, or after a delay.", inline=False)
            help_embed.add_field(name="Staff List", value="`pls staff` will show all active staff.")
            return await ctx.reply(embed=help_embed,mention_author=False)
        else:
            botcommand = self.bot.get_command(command)
            if not botcommand:
                return await ctx.reply(
                    "This isn't a command.",
                    mention_author=False,
                )
            embed = stock_embed(self.bot)
            embed.title = f"❓ `{ctx.prefix}{botcommand.qualified_name}`"
            embed.color = ctx.author.color
            segments = botcommand.help.split("\n\n")
            if len(segments) != 3:
                return await ctx.reply(
                    "This command isn't configured properly yet.\nPlease look at the documentation, and yell at Ren to fix it.",
                    mention_author=False,
                )
            embed.description = f"**{segments[0]}**\n>>> {segments[1]}"
            embed.add_field(name="Arguments", value=segments[2], inline=False)
            if "ismanager" in repr(botcommand.checks):
                who = "Bot Manager Only"
            elif "isowner" in repr(botcommand.checks):
                who = "Server Owner or Higher"
            elif "isadmin" in repr(botcommand.checks):
                who = "Server Admin or Higher"
            elif "ismod" in repr(botcommand.checks):
                who = "Server Mod or Higher"
            else:
                who = "Everyone"

            if "dm_only" in repr(botcommand.checks):
                where = "DMs Only"
            elif "guild_only" in repr(botcommand.checks):
                where = "Guilds Only"
            else:
                where = "Everywhere"

            embed.add_field(
                name="Access", value="- " + who + "\n- " + where, inline=True
            )

            embed.add_field(
                name="Aliases",
                value="\n- ".join(botcommand.aliases) if botcommand.aliases else "None",
                inline=True,
            )

            try:
                await botcommand.can_run(ctx)
            except BotMissingPermissions as e:
                when = (
                    "**No.** Missing:\n```diff\n+ "
                    + "\n+ ".join(e.missing_permissions)
                    + "```"
                )
            else:
                when = "**Yes.**"

            embed.add_field(name="Executable", value=when, inline=True)

            await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    @commands.check(ismod)
    async def staffhelp(self, ctx):
        '''
        TODO: Seriously fix this up
        '''
        embed1 = stock_embed(self.bot)
        embed1.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        embed1.color = 0xce7398
        embed1.add_field(name="Kicking", value="""Use `pls kick` to kick users. If you add a reason to the end, the user will be DMed the reason. (This is useful for users who didn't respond in muted!)""", inline=False)
        embed1.add_field(name="Banning & Unbanning", value="""This information is here for posterity. Trial staff are unable to use these commands.
`pls ban` will ban users. If you add a reason to this, the user will be DMed the reason. The user will also be DMed the ban appeal form.
`pls dban` or `pls bandel` with a variable from 0-7 (referring to days) at the end will ban a user and purge their messages from the last x days. You may also provide a reason. It will be DMed to them. 
`pls massban` can be used with user IDs to massban. It will not DM the users.
`pls unban` unbans a user. The reason can't be sent to the user. 
`pls sban` bans a user without DMing them the reason.""", inline=False)

        embed1.add_field(name="Muting & Unmuting Users", value="""I can mute users! I don't use slash commands to provide a simple alternative to Smol/Tol for mobile moderation. When I mute users, I create multiple channels so nothing gets messy. I do this automatically. To mute users, you can use `pls toss`, `pls mute`, or `pls roleban`. To unmute users, you can use `pls untoss`, `pls unmute`, or `pls unroleban`.""", inline=True)
        embed1.add_field(name="Archiving & Closing Sessions", value="""When a muted session is done, please remember to archive with `pls archive`! This is handled by a separate bot for Various Reasons, but it's here for posterity. Then close the muted channel with `pls close`.""", inline=True)
        embed1.add_field(name="Namefixing & Dehoisting", value="""If somebody has a name with unmentionable characters, you can easily fix it with `pls fixname`. If somebody is purposefully hoisting themselves on the userlist, you can dehoist them with `pls dehoist`.""", inline=True)

        embed2 = stock_embed(self.bot)
        embed2.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        embed2.add_field(name="Miscellaneous Moderation",value="""`pls speak [channel] [text]` will make me repeat what you say in a specific channel.
`pls reply [message link] [text]` will make me repeat what you said, replying to somebody else.
`pls react [message link] [emoji]` will make me react to someone's message with an emote. I can only use emotes I have access to!
`pls typing [channel] [duration]` will make me look like I'm typing in a channel for however long you set.""")
        embed2.add_field(name="Rule Snippets", value="""If you need to call up a specific rule, you can use `pls rule [rulename]`. You can check the list of rule snippets with `pls rule`. You can create new rule snippets with `pls rule create`. You can delete a rule snippet with `pls rule delete`.""", inline=True)
        embed2.add_field(name="Latency Checking", value="""If I'm slow, you can check my ping with `pls ping`.""", inline=True)
        await sympage(self.bot, ctx, [embed1, embed2], ["1️⃣","2️⃣"])


    @commands.cooldown(1, 5, type=commands.BucketType.default)
    @commands.bot_has_permissions(attach_files=True)
    @commands.guild_only()
    @commands.command()
    async def joingraph(self, ctx):
        """This shows the graph of users that joined.

        This is NOT accounting for the server's entire history,
        only the members that are currently on the guild and
        their join dates. Keep that in mind!

        No arguments."""
        async with ctx.channel.typing():
            rawjoins = [m.joined_at.date() for m in ctx.guild.members]
            joindates = sorted(list(dict.fromkeys(rawjoins)))
            joincounts = []
            for i, d in enumerate(joindates):
                if i != 0:
                    joincounts.append(joincounts[i - 1] + rawjoins.count(d))
                else:
                    joincounts.append(rawjoins.count(d))
            plt.plot(joindates, joincounts)
            joingraph = io.BytesIO()
            plt.savefig(joingraph, bbox_inches="tight")
            joingraph.seek(0)
            plt.close()
        await ctx.reply(
            file=discord.File(joingraph, filename="joingraph.png"), mention_author=False
        )

    @commands.guild_only()
    @commands.command(aliases=["joinscore"])
    async def joinorder(self, ctx, target: typing.Union[discord.Member, int] = None):
        """This shows the joinscore of a user.

        See how close you are to being first!

        - `target`
        Who you want to see the joinscore of.
        This can also be an index number, like `1`."""
        members = sorted(ctx.guild.members, key=lambda v: v.joined_at)
        if not target:
            memberidx = members.index(ctx.author) + 1
        elif type(target) == discord.Member:
            memberidx = members.index(target) + 1
        else:
            memberidx = target
        message = ""
        for idx, m in enumerate(members):
            if memberidx - 6 <= idx <= memberidx + 4:
                user = self.bot.pacify_name(str(m))
                message = (
                    f"{message}\n`{idx+1}` **{user}**"
                    if memberidx == idx + 1
                    else f"{message}\n`{idx+1}` {user}"
                )
        await ctx.reply(content=message, mention_author=False)

async def setup(bot):
    await bot.add_cog(Basic(bot))
