import time
import discord
import io
import asyncio
import matplotlib
import matplotlib.pyplot as plt
import typing
import random
import platform
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.checks import ismod, ismanager
from helpers.embeds import stock_embed, sympage
from helpers.sv_config import get_config
import aiohttp
from helpers.placeholders import random_msg


class Basic(Cog):
    def __init__(self, bot):
        self.bot = bot
        matplotlib.use("agg")

    """
    TODO: stop this from being stupid
    """

    @commands.command()
    @commands.check(ismod)
    async def drive(self, ctx):
        """This spits out the Undertale Discord's Google Drive, but only if you're a mod."""
        await ctx.send(
            f"https://drive.google.com/drive/folders/{get_config(ctx.guild.id, 'drive', 'folder')}?usp=sharing"
        )

    @commands.command()
    async def choose(self, ctx: commands.Context, *options):
        """This will choose something at random for you.

        It's not weighted, it's completely random between
        all possible options you give.

        - `options`
        A list of options, separated by spaces."""
        return await ctx.send(f"You should `{random.choice(options)}`!")

    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(aliases=["timer"])
    async def eggtimer(self, ctx: commands.Context, minutes: int = 5):
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
        try:
            await ctx.message.remove_reaction("⏳", self.bot.user)
            msg = await ctx.channel.send(content=ctx.author.mention)
            await msg.edit(content="⌛", delete_after=5)
        except discord.errors.NotFound:
            return

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def banner(self, ctx: commands.Context, target: discord.User | None):
        """This gets a user's banner.

        If you don't specify anyone, it'll show your
        pretty banner that you have on right now.

        - `target`
        Who you wish to show the banner of. Optional."""
        if target is not None:
            target = self.bot.get_user(target.id)
        else:
            target = ctx.author

        if target is None:
            return await ctx.reply(
                "This user is not visible to me! *thump\*", mention_author=False
            )

        if target.banner == None:
            return await ctx.reply(
                "This user has no banner! *thump\*", mention_author=False
            )

        return await ctx.send(content=target.banner.url)

    @commands.bot_has_permissions(embed_links=True)
    @banner.command(name="server")
    async def bserver(self, ctx: commands.Context, target: discord.Guild | None):
        """This gets a server's banner.

        You *could* get another server's banner with
        this if you know its ID, and the bot is on it.
        Otherwise it shows the current server's banner.

        - `target`
        The server you want to see the banner of. Optional."""
        if target is None:
            target = ctx.guild

        if target.banner == None:
            return await ctx.reply(
                "This server has no banner! \*thump\*", mention_author=False
            )

        return await ctx.send(content=target.banner.url)

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def avy(self, ctx: commands.Context, target: discord.User | None):
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
        return await ctx.reply(content=target.display_avatar.url, mention_author=False)

    @commands.bot_has_permissions(embed_links=True)
    @avy.command(name="server")
    async def aserver(self, ctx: commands.Context, target: discord.Guild | None):
        """This gets a server's avatar.

        You *could* get another server's avatar with
        this if you know its ID, and the bot is on it.
        Otherwise it shows the current server's avy.

        - `target`
        The server you want to see the avy of. Optional."""
        if target is None:
            target = ctx.guild

            if target.icon == None:
                return await ctx.reply(
                    "This server has no icon! \*thump\*", mention_author=False
                )

        return await ctx.send(content=target.icon.url)

    @commands.command(aliases=["catbox", "imgur"])
    async def rehost(self, ctx: commands.Context, links=None):
        """This uploads a file to catbox.moe.

        These files won't expire, ever. Please respect
        their free service that they offer!
        You can also use an attachment.

        - `links`
        The links to reupload to catbox."""
        """
        TODO: Move away from Catbox due to user-facing slurs 
        """
        api_url = "https://catbox.moe/user/api.php"
        if not ctx.message.attachments and not links:
            return await ctx.reply(
                content="You need to supply a file or a file link to rehost.",
                mention_author=False,
            )
        # String multiple attachments/links together
        links = links.split() if links else []
        for r in [f.url for f in ctx.message.attachments] + links:
            # Formulate form data for Catbox
            formdata = aiohttp.FormData()
            formdata.add_field("reqtype", "urlupload")
            if self.bot.config.catbox_key:
                formdata.add_field("userhash", self.bot.config.catbox_key)
            formdata.add_field("url", r)
            # Post form data
            async with self.bot.session.post(api_url, data=formdata) as response:
                if response.status == 412:
                    # Catbox 412 response conflicts with server rules. Overriding this makes it both friendlier and an opportunity to direct users somewhere they can fix it
                    return await ctx.reply(
                        content=f"Your file is too large. If you're uploading a GIF, try optimizing with something like [Ezgif](https://ezgif.com).",
                        mention_author=False,
                    )
                else:
                    # If there's no issue, then assume it's safe to send the response back
                    whats_supposed_to_be_the_image_link = await response.text()
                    return await ctx.reply(
                        content=whats_supposed_to_be_the_image_link,
                        mention_author=False,
                    )

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
            help_embed.set_author(
                name="Fluff",
                url="https://github.com/dfault-user/fluff",
                icon_url="https://cdn.discordapp.com/attachments/629713406651531284/1256428667345834014/3be16Ny.png?ex=668164a1&is=66801321&hm=d60b695a687388f6b7de1911b788676f12b56c630157e4a2c0249cc431faa5f6&",
            )

            help_data = {
                "Image Hosting": "Use `pls rehost`, `pls imgur`, or `pls catbox` with an attachment or link to host that attachment forever. Please respect the service.",
                "Staff List": "`pls staff` will show all active staff.",
                "Join Graph": "`pls joingraph` shows a graph of users who have joined.",
                "Join Score": "`pls joinscore` shows when you joined in comparison to other users.",
                "Rules and Snippets": "`pls rule` will display a list of rules, while `pls snippets` will display frequently recalled information that is good to have on hand.",
                "Ping Preferences": "`pls replyconfig` will allow you to change your ping preferences, AKA whether you'd like to be pinged always, never, or after a delay.",
                "Rolling the Dice": "`pls choose [options separated by spaces]` will choose something at random for you.",
                "Timer": "`pls timer [duration in minutes, max 60]` I will start a timer for you and ping you when it's done. By default I will set it for 5 minutes.",
                "User Avy": "`pls avy [user]` will tell me to post your avatar. Without any user specified, I will post your current avatar.",
                "Server Avy": "`pls avy server` will tell me to post the avatar of the server.",
                "About Me": "`pls about` shows my info!",
                "Bunfact": "`pls bunfact` and `pls bunfact [fact name]` shows a fun bun fact, and sometimes an associated gif or image!",
                "Mutedmute": "`pls mutedmute [user]` will mute a user in a special way. You can use it even when you're not staff!",
            }

            for name, value in help_data.items():
                help_embed.add_field(name=name, value=value, inline=True)
            return await ctx.reply(embed=help_embed, mention_author=False)
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
                    "This command isn't properly documented  yet.\nPlease yell at DFU or Marr to fix it.",
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
            except commands.BotMissingPermissions as e:
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
        """This is Fluff's staff help command.

        Spits out two internally defined embeds with pagination to help staff out on the ropes.

        No arguments."""
        embed1 = stock_embed(self.bot)
        fields = [
            {
                "name": "Kicking",
                "value": """Use `pls kick` to kick users. If you add a reason to the end, the user will be DMed the reason. (This is useful for users who didn't respond in muted!)""",
                "inline": False,
            },
            {
                "name": "Banning & Unbanning",
                "value": """This information is here for posterity. Trial staff are unable to use these commands.
`pls ban` will ban users. If you add a reason to this, the user will be DMed the reason. The user will also be DMed the ban appeal form.
`pls dban` or `pls bandel` with a variable from 0-7 (referring to days) at the end will ban a user and purge their messages from the last x days. You may also provide a reason. It will be DMed to them. 
`pls massban` can be used with user IDs to massban. It will not DM the users.
`pls unban` unbans a user. The reason can't be sent to the user. 
`pls sban` bans a user without DMing them the reason.""",
                "inline": False,
            },
            {
                "name": "Muting & Unmuting Users",
                "value": """I can mute users! I don't use slash commands to provide a simple alternative to Smol/Tol for mobile moderation. When I mute users, I create multiple channels so nothing gets messy. I do this automatically. To mute users, you can use `pls toss`, `pls mute`, or `pls roleban`. To unmute users, you can use `pls untoss`, `pls unmute`, or `pls unroleban`.""",
                "inline": True,
            },
            {
                "name": "Session Commands",
                "value": """Some commands are to be used inside of a toss session. Most imperatively is the `pls close` command, which closes the session that the command is invoked in. Sometimes though, a user may need to send an image or two during a toss session, which is why `pls unlockimages` is used to enable those permissions.""",
                "inline": True,
            },
            {
                "name": "Namefixing & Dehoisting",
                "value": """If somebody has a name with unmentionable characters, you can easily fix it with `pls fixname` (or `fixname`, if you prefer). If somebody is purposefully hoisting themselves on the userlist, you can dehoist them with `pls dehoist`.""",
                "inline": True,
            },
            {
                "name": "Miscellaneous Moderation",
                "value": """`pls speak [channel] [text]` will make me repeat what you say in a specific channel.
`pls reply [message link] [text]` will make me repeat what you said, replying to somebody else.
`pls react [message link] [emoji]` will make me react to someone's message with an emote. I can only use emotes I have access to!
`pls typing [channel] [duration]` will make me look like I'm typing in a channel for however long you set.""",
                "inline": False,
            },
            {
                "name": "Google Drive",
                "value": """Access the Undertale Discord's Google Drive with `pls drive`.""",
                "inline": False,
            },
            {
                "name": "Tenure Querying",
                "value": """If you need to query a user's Tenure status, you can use `pls tenure [user]`. This will return the user's tenure status, as well as when they last joined the server, in days.""",
                "inline": False,
            },
            {
                "name": "Rules and Snippets",
                "value": """If you need to call up a specific rule, you can use `pls rule [rulename]`. Some rules have specific information which needs to be recalled repetitively, which is done with `pls snippets [snippet]`. All rules and snippets can be summarized by calling `pls rule` or `pls snippets` on their own.""",
                "inline": False,
            },
            {
                "name": "Latency Checking",
                "value": """If I'm slow, you can check my ping with `pls ping`.""",
                "inline": False,
            },
            {
                "name": "Checking Permissions",
                "value": """`pls permcheck` will check a user's permissions for a certain channel.""",
                "inline": False,
            },
        ]

        half = len(fields) // 2
        first_half = fields[:half]
        second_half = fields[half:]

        embed1 = stock_embed(self.bot)
        embed2 = stock_embed(self.bot)

        for field in first_half:
            embed1.add_field(
                name=field["name"], value=field["value"], inline=field["inline"]
            )

        for field in second_half:
            embed2.add_field(
                name=field["name"], value=field["value"], inline=field["inline"]
            )

        await sympage(self.bot, ctx, [embed1, embed2], ["1️⃣", "2️⃣"])

    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """This shows the bot's ping to Discord.

        RTT = Round-trip time.
        GW = Ping to Gateway.

        No arguments."""
        before = time.monotonic()
        tmp = await ctx.reply("⌛", mention_author=False)
        after = time.monotonic()
        rtt_ms = (after - before) * 1000
        gw_ms = self.bot.latency * 1000

        message_text = f":ping_pong:\nRound-Time Trip (Receive-to-Response): `{rtt_ms:.1f}ms`\nGateway (Connection to Discord): `{gw_ms:.1f}ms`"
        self.bot.log.info(message_text)
        await tmp.edit(content=message_text)

    @commands.command()
    @commands.check(ismanager)
    async def managerhelp(self, ctx):
        """This is Fluff's manager help command.

        Spits out two internally defined embeds with pagination to help staff out on the ropes.

        No arguments."""
        title = "These are commands that may only be used by the bot manager."
        embed1 = stock_embed(self.bot)
        fields = [
            {
                "name": "pls quit",
                "value": """shuts down the bot""",
                "inline": True,
            },
            {
                "name": "pls errors",
                "value": """checks error log""",
                "inline": True,
            },
            {
                "name": "pls getdata",
                "value": """sends you current bot data files""",
                "inline": True,
            },
            {
                "name": "pls getsdata [server ID]",
                "value": """gets server data files""",
                "inline": True,
            },
            {
                "name": "pls setsdata [server ID] {attachment}",
                "value": """replaces server data files""",
                "inline": True,
            },
            {
                "name": "pls getudata [user ID]",
                "value": """gets user data files""",
                "inline": True,
            },
            {
                "name": "pls setudata [user ID] {attachment}",
                "value": """replaces user data files""",
                "inline": True,
            },
            {
                "name": "pls getlogs",
                "value": """gets bots log file""",
                "inline": True,
            },
            {
                "name": "pls taillogs",
                "value": """gets the last 10 lines of the log file""",
                "inline": True,
            },
            {
                "name": "pls guilds",
                "value": """shows what guilds the bot is in""",
                "inline": True,
            },
            {
                "name": "pls setdata {attachment}",
                "value": """replaces bot data files
only to use with backups if the bot explodes or something""",
                "inline": False,
            },
            {
                "name": "pls threadlock [channel]",
                "value": """locks all threads in one channel""",
                "inline": True,
            },
            {
                "name": "pls botban [user]",
                "value": """bans a user from using me. naughty!""",
                "inline": True,
            },
            {
                "name": "pls unbotban [user]",
                "value": """back on the nice list. lets a user use me again""",
                "inline": True,
            },
            {
                "name": "pls setavy",
                "value": """sets my avy!""",
                "inline": True,
            },
            {
                "name": "pls setbanner",
                "value": """sets my banner!""",
                "inline": True,
            },
            {
                "name": "pls eval {code}",
                "value": """evaluates some code""",
                "inline": True,
            },
            {
                "name": "pls exec {code}",
                "value": """executes some code""",
                "inline": True,
            },
            {
                "name": "pls load cogs.[cog name]",
                "value": """loads a cog""",
                "inline": True,
            },
            {
                "name": "pls unload cogs.[cog name]",
                "value": """unloads a cog""",
                "inline": True,
            },
            {
                "name": "pls reload cogs.[cog name]",
                "value": """reloads a cog""",
                "inline": True,
            },
            {
                "name": "pls pull [true/false]",
                "value": """you can pull from git
the true/false portion tells me whether to reload cogs""",
                "inline": False,
            },
        ]

        half = len(fields) // 2
        first_half = fields[:half]
        second_half = fields[half:]

        embed1 = stock_embed(self.bot)
        embed1.title = title

        embed2 = stock_embed(self.bot)
        embed2.title = title

        for field in first_half:
            embed1.add_field(
                name=field["name"], value=field["value"], inline=field["inline"]
            )

        for field in second_half:
            embed2.add_field(
                name=field["name"], value=field["value"], inline=field["inline"]
            )

        await sympage(self.bot, ctx, [embed1, embed2], ["1️⃣", "2️⃣"])

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
    async def joinorder(self, ctx, target: typing.Union[discord.Member, int] | None):
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

    @commands.cooldown(1, 5, type=commands.BucketType.default)
    @commands.guild_only()
    @commands.command(aliases=["banne"])
    async def mutedmute(self, ctx, target: typing.Union[discord.Member, int] | None):
        """This mutes a user in a special way.

        You can use it even if you aren't staff!

        - `target`
        Who you want to 'mute'. This is a user mention."""
        if not target:
            return
        else:
            if isinstance(target, discord.Member):
                target_mention = target.mention
            else:
                return
            reply_messages = [
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been demoted to muted mute.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been forever silenced.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been erased from history.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been sent to a farm upstate.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been sentenced to 50 years in the dungeon.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been muted muted muted muted muted mute.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} is gone.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} is dead now.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} will be back. They always come back.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been sent Somewhere Else.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been sent to gay baby jail.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been sent to Non-Denominational Vaguely Romantic Infant Gulag.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} is over there now.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has been shaved bald.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} is in your house now.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} has had every bone in their body shattered.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} went on vacation.",
                f"{self.bot.pacify_name(ctx.message.mentions[0].display_name)} was let cook.",
            ]
            random_message = random.choice(reply_messages)

            await ctx.send(random_message, mention_author=False)

            async for message in ctx.channel.history(limit=20):
                if message.author == target:
                    await message.add_reaction("<:rubberhammer:1281079056820998185>")
                    break

    @commands.guild_only()
    @commands.command()
    async def postrules(self, ctx):
        """This posts the rules.

        No arguments."""
        await ctx.send(content=random_msg("rules_1"))


async def setup(bot):
    await bot.add_cog(Basic(bot))
