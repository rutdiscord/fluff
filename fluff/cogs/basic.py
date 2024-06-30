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
            help_embed.add_field(name="Server Information", value="`pls server` displays the server's info.", inline=False)
            help_embed.add_field(name="Rule Snippets", value="`pls rule` will display a list of rule snippets. You can individually call them with their names, `pls rule [name]`. Useful for people who are confused about the rules!")
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
        test_embed = stock_embed(self.bot)
        test_embed.set_author(name="Fluff", url="https://github.com/dfault-user/fluff", icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&")
        test_embed.color = 0xce7398
        test_embed.add_field(name="Muting & Unmuting Users", value="""I can mute users! I don't use slash commands to provide a simple alternative to Smol/Tol for mobile moderation. When I mute users, I create multiple channels so nothing gets messy. I do this automatically. To mute users, you can use `pls toss`, `pls mute`, or `pls roleban`. To unmute users, you can use `pls untoss`, `pls unmute`, or `pls unroleban`.""", inline=True)
        test_embed.add_field(name="Archiving & Closing Sessions", value="""When a muted session is done, please remember to archive with `pls archive`! This is handled by a separate bot for Various Reasons, but it's here for posterity. Then close the muted channel with `pls close`.""", inline=True)
        test_embed.add_field(name="Namefixing & Dehoisting", value="""If somebody has a name with unmentionable characters, you can easily fix it with `pls fixname`. If somebody is purposefully hoisting themselves on the userlist, you can dehoist them with `pls dehoist`.""", inline=True)        
        test_embed.add_field(name="Banning & Unbanning", value="""This information is here for posterity. Trial staff are unable to use these commands.
`pls ban` will ban users. If you add a reason to this, the user will be DMed the reason. The user will also be DMed the ban appeal form.
`pls dban` or `pls bandel` with a variable from 0-7 (referring to days) at the end will ban a user and purge their messages from the last x days. You may also provide a reason. It will be DMed to them. 
`pls massban` can be used with user IDs to massban. It will not DM the users.
`pls unban` unbans a user. The reason can't be sent to the user. 
`pls sban` bans a user without DMing them the reason.""")
        test_embed.add_field(name="Miscellaneous Moderation",value="""`pls speak [channel] [text]` will make me repeat what you say in a specific channel.
`pls reply [message link] [text]` will make me repeat what you said, replying to somebody else.
`pls react [message link] [emoji]` will make me react to someone's message with an emote. I can only use emotes I have access to!
`pls typing [channel] [duration]` will make me look like I'm typing in a channel for however long you set.""")
        test_embed.add_field(name="Latency Checking", value="""If I'm slow, you can check my ping with `pls ping`.""", inline=True)
        test_embed.add_field(name="Rule Snippets", value="""If you need to call up a specific rule, you can use `pls rule [rulename]`. You can check the list of rule snippets with `pls rule`. You can create new rule snippets with `pls rule create`. You can delete a rule snippet with `pls rule delete`.""", inline=True)
        test_embed.add_field(name="Kicking", value="""Use `pls kick` to kick users. If you add a reason to the end, the user will be DMed the reason. (This is useful for users who didn't respond in muted!)""", inline=True)
        await ctx.reply(embed=test_embed)

    @commands.command()
    async def jump(self, ctx):
        """This posts a link to the first message in the channel.

        Not much more to it.

        No arguments."""
        async for message in ctx.channel.history(oldest_first=True):
            return await ctx.reply(content=message.jump_url, mention_author=False)

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """This shows the bot's ping to Discord.

        No arguments."""
        before = time.monotonic()
        tmp = await ctx.reply("⌛", mention_author=False)
        after = time.monotonic()
        rtt_ms = (after - before) * 1000
        gw_ms = self.bot.latency * 1000

        message_text = f":ping_pong:\nRound-Time Trip (Message-to-Response): `{rtt_ms:.1f}ms`\n Gateway (Discord Websocket): `{gw_ms:.1f}ms`"
        self.bot.log.info(message_text)
        await tmp.edit(content=message_text)

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

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def info(self, ctx, *, target: discord.User = None):
        """This gets user information.

        Useful for getting a quick overview of someone.
        It will default to showing your information.

        - `target`
        Who you want to see info of. Optional."""
        if not target:
            target = ctx.author

        if not ctx.guild.get_member(target.id):
            # Memberless code.
            color = discord.Color.lighter_gray()
            nickname = ""
        else:
            # Member code.
            target = ctx.guild.get_member(target.id)
            color = target.color
            nickname = f"\n**Nickname:** `{ctx.guild.get_member(target.id).nick}`"

        embed = discord.Embed(
            color=color,
            title=f"Info for {'user' if ctx.guild.get_member(target.id) else 'member'} {target}{' [BOT]' if target.bot else ''}",
            description=f"**ID:** `{target.id}`{nickname}",
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        embed.set_author(name=f"{target}", icon_url=f"{target.display_avatar.url}")
        embed.set_thumbnail(url=f"{target.display_avatar.url}")
        embed.add_field(
            name="⏰ Account Created",
            value=f"<t:{int(target.created_at.astimezone().timestamp())}:f>\n<t:{int(target.created_at.astimezone().timestamp())}:R>",
            inline=True,
        )
        if ctx.guild.get_member(target.id):
            embed.add_field(
                name="⏱️ Account Joined",
                value=f"<t:{int(target.joined_at.astimezone().timestamp())}:f>\n<t:{int(target.joined_at.astimezone().timestamp())}:R>",
                inline=True,
            )
            embed.add_field(
                name="🗃️ Joinscore",
                value=f"`{sorted(ctx.guild.members, key=lambda v: v.joined_at).index(target)+1}` of `{len(ctx.guild.members)}`",
                inline=True,
            )
            try:
                emoji = f"{target.activity.emoji} " if target.activity.emoji else ""
            except:
                emoji = ""
            try:
                details = (
                    f"\n{target.activity.details}" if target.activity.details else ""
                )
            except:
                details = ""
            try:
                name = f"{target.activity.name}" if target.activity.name else ""
            except:
                name = ""
            if emoji or name or details:
                embed.add_field(
                    name="💭 Status", value=f"{emoji}{name}{details}", inline=False
                )
            roles = []
            if len(target.roles) > 1:
                for role in target.roles:
                    if role.name == "@everyone":
                        continue
                    roles.append("<@&" + str(role.id) + ">")
                rolelist = ",".join(reversed(roles))
            else:
                rolelist = "None"
            embed.add_field(name=f"🎨 Roles", value=rolelist, inline=False)

        await ctx.reply(embed=embed, mention_author=False)

    @info.command(aliases=["guild"])
    async def server(self, ctx, *, server: discord.Guild = None):
        """This gets server information.

        Useful for getting a quick overview of a server.
        It will default to showing the current server.

        - `server`
        What server you want to see info of. Optional."""
        if server == None:
            server = ctx.guild

        serverdesc = "*" + server.description + "*" if server.description else ""
        embed = discord.Embed(
            color=server.me.color,
            title=f"Info for server {server}",
            description=f"{serverdesc}\n**ID:** `{server.id}`\n**Owner:** {server.owner.mention}",
            timestamp=datetime.now(),
        )
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        embed.set_author(name=server.name, icon_url=server.icon.url)
        embed.set_thumbnail(url=(server.icon.url if server.icon else None))
        embed.add_field(
            name="⏰ Server created:",
            value=f"<t:{int(server.created_at.astimezone().timestamp())}:f>\n<t:{int(server.created_at.astimezone().timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="👥 Server members:",
            value=f"`{server.member_count}`",
            inline=True,
        )
        embed.add_field(
            name="#️⃣ Counters:",
            value=f"**Text Channels:** {len(server.text_channels)}\n**Voice Channels:** {len(server.voice_channels)}\n**Forum Channels:** {len(server.forums)}\n**Roles:** {len(server.roles)}\n**Emoji:** {len(server.emojis)}\n**Stickers:** {len(server.stickers)}\n**Boosters:** {len(server.premium_subscribers)}",
            inline=False,
        )

        if server.banner:
            embed.set_image(url=server.banner.url)

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(Basic(bot))
