import discord, json, asyncio
from discord.ext.commands import Cog
from discord.ext import commands, tasks
from helpers.datafiles import get_guildfile, set_guildfile
from helpers.sv_config import get_config
from helpers.embeds import stock_embed, author_embed


class Reply(Cog):
    """
    A cog that stops people from ping replying people who don't want to be.
    """

    def __init__(self, bot):
        self.bot = bot
        self.violations = {}
        self.timers = {}
        self.counttimer.start()
        self.mode_enabled = False 
        self.angwy_enabled = False

    def cog_unload(self):
        self.counttimer.cancel()

    def check_override(self, message):
        if not message.guild:
            return None
        setting_roles = [
            (self.bot.pull_role(message.guild, "Please Ping"), "pleasereplyping"),
            (
                self.bot.pull_role(message.guild, "Ping after Delay"),
                "waitbeforereplyping",
            ),
            (self.bot.pull_role(message.guild, "No Ping"), "noreplyping"),
        ]
        for role, identifier in setting_roles:
            if role == None:
                continue
            elif role in message.author.roles:
                return identifier
        return None

    async def add_violation(self, message):
        staff_roles = [
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "modrole")
            ),
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "adminrole")
            ),
        ]
        if not get_config(message.guild.id, "reaction", "noreply_remind_every"):
            return
        noreply_remind = (
            3
            if get_config(message.guild.id, "reaction", "noreply_remind_every") > 3
            else get_config(message.guild.id, "reaction", "noreply_remind_every")
        )

        if not get_config(message.guild.id, "reaction", "noreply_threshold"):
            return
        noreply_thres = (
            10
            if get_config(message.guild.id, "reaction", "noreply_threshold") > 10
            else get_config(message.guild.id, "reaction", "noreply_threshold")
        )
        if (
            not any(staff_roles)
            or any([staff_role in message.author.roles for staff_role in staff_roles])
            or await self.bot.is_owner(message.author)
        ):
            return

        message_author = message.author
        message_guild = message.guild

        if message_guild.id not in self.violations:
            self.violations[message_guild.id] = {}
        if message_author.id not in self.violations[message.guild.id]:
            self.violations[message_guild.id][message.author.id] = 0
            acknowledgements = get_guildfile(message.guild.id, "acknowledgements")
            if str(message.author.id) not in acknowledgements:
                temp_reminder_msg = await message_author.send(
                    content="**Please do not reply ping users who do not wish to be pinged.**\n"
                    + "This incident will be excused, but further incidents will be counted as **violations**. (Reply to this message or wait sixty seconds to acknowledge)",
                    file=discord.File("assets/noreply.png"),
                    mention_author=False,
                )

                def wait_check(new_msg):
                    return new_msg.author == message.author and isinstance(
                        new_msg.channel, discord.DMChannel
                    )

                try:
                    await self.bot.wait_for("message", timeout=60, check=wait_check)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    await temp_reminder_msg.delete()

            acknowledgements[str(message.author.id)] = True
            return set_guildfile(
                message_guild.id, "acknowledgements", json.dumps(acknowledgements)
            )

        self.violations[message.guild.id][message.author.id] += 1
        violation_count = self.violations[message.guild.id][message.author.id]

        modlog_channel = self.bot.pull_channel(
            message.guild, get_config(message.guild.id, "logging", "modlog")
        )

        async def notify_modlog(additional=None):
            return await modlog_channel.send(
                f":infinity: **{message_author.global_name}** (**{message_author.id}**) has received a reply ping preference violation. Their current violation count is {violation_count}. ({additional})"
            )

        try:
            if self.violations[message.guild.id][message.author.id] == (
                noreply_thres - 1
            ):
                await notify_modlog(additional="Next violation will result in penalty.")
                await message.reply(
                    content=f"# {message.author.mention}, your next violation will result in penalty.\n"
                    + f"You have currently received {str(violation_count)} violations.\n"
                    + f"As a reminder, **please respect ping preferences, and do not reply ping users who do not wish to be pinged**.",
                    file=discord.File("assets/noreply.png"),
                )

            elif (
                self.violations[message.guild.id][message.author.id] % noreply_remind
                == 0
            ):
                await notify_modlog("Reminder sent.")
                return await message.author.send(
                    content="**Do not reply ping users who do not wish to be pinged.**\n"
                    + f"You have currently received {str(violation_count)} violations.\n"
                    + f"{noreply_thres} violations will result in a penalty.",
                    file=discord.File("assets/noreply.png"),
                )
            elif self.violations[message.guild.id][message.author.id] >= noreply_thres:
                return self.bot.dispatch(
                    "violation_threshold_reached", message, message.author
                )
        except ZeroDivisionError:
            return

# Command disabled due to use of fill_profile.
# At the time of disablement, it hadn't been used by anyone in six months.
# If you need this functionality, use role assignment via another bot.
# TODO: DELETE ENTIRELY
    #@commands.bot_has_permissions(embed_links=True)
    #@commands.command()
    #async def replyconfig(self, ctx):
    #    """This sets your reply ping preferences.
#
    #    Use the reactions to pick your setting.
    #    See the [documentation](https://3gou.0ccu.lt/as-a-user/reply-ping-preferences/) for more info.
#
    #    No arguments."""
    #    override = self.check_override(ctx.message)
    #    if override:
    #        return await ctx.reply(
    #            content="You already have an indicator role, you don't need to set your preferences here.",
    #            mention_author=False,
    #        )
#
    #    profile = fill_profile(ctx.author.id)
    #    embed = stock_embed(self.bot)
    #    embed.title = "Your reply preference"
    #    embed.color = discord.Color.red()
    #    author_embed(embed, ctx.author)
    #    allowed_mentions = discord.AllowedMentions(replied_user=False)
#
    #    def fieldadd():
    #        unconfigured = "🔘" if not profile["replypref"] else "⚫"
    #        embed.add_field(
    #            name="🤷 Unconfigured",
    #            value=unconfigured + " Indicates that you have no current preference.",
    #            inline=False,
    #        )
#
    #        pleaseping = "🔘" if profile["replypref"] == "pleasereplyping" else "⚫"
    #        embed.add_field(
    #            name="<:pleaseping:1258418052651942053> Please Reply Ping",
    #            value=pleaseping
    #            + " Indicates that you would like to be pinged in replies.",
    #            inline=False,
    #        )
#
    #        waitbeforeping = (
    #            "🔘" if profile["replypref"] == "waitbeforereplyping" else "⚫"
    #        )
    #        embed.add_field(
    #            name="<:waitbeforeping:1258418064781738076> Wait Before Reply Ping",
    #            value=waitbeforeping
    #            + " Indicates that you would only like to be pinged after some time has passed.",
    #            inline=False,
    #        )
#
    #        noping = "🔘" if profile["replypref"] == "noreplyping" else "⚫"
    #        embed.add_field(
    #            name="<:noping:1258418038504689694> No Reply Ping",
    #            value=noping
    #            + " Indicates that you do not wish to be reply pinged whatsoever.",
    #            inline=False,
    #        )
#
    #    fieldadd()
#
    #    reacts = [
    #        "🤷",
    #        "<:pleaseping:1258418052651942053>",
    #        "<:waitbeforeping:1258418064781738076>",
    #        "<:noping:1258418038504689694>",
    #    ]
    #    configmsg = await ctx.reply(embed=embed, mention_author=False)
    #    for react in reacts:
    #        await configmsg.add_reaction(react)
    #    embed.color = discord.Color.green()
    #    await configmsg.edit(embed=embed, allowed_mentions=allowed_mentions)
#
    #    def reactioncheck(r, u):
    #        return u.id == ctx.author.id and str(r.emoji) in reacts
#
    #    try:
    #        reaction, user = await self.bot.wait_for(
    #            "reaction_add", timeout=30.0, check=reactioncheck
    #        )
    #    except asyncio.TimeoutError:
    #        embed.color = discord.Color.default()
    #        for react in reacts:
    #            await configmsg.remove_reaction(react, ctx.bot.user)
    #        return await configmsg.edit(
    #            embed=embed,
    #            allowed_mentions=allowed_mentions,
    #        )
    #    else:
    #        if str(reaction) == reacts[0]:
    #            profile["replypref"] = None
    #            role_name = None
    #        elif str(reaction) == reacts[1]:
    #            profile["replypref"] = "pleasereplyping"
    #            role_name = "Please Ping"
    #        elif str(reaction) == reacts[2]:
    #            profile["replypref"] = "waitbeforereplyping"
    #            role_name = "Ping after Delay"
    #        elif str(reaction) == reacts[3]:
    #            profile["replypref"] = "noreplyping"
    #            role_name = "No Ping"
#
    #        set_userfile(ctx.author.id, "profile", json.dumps(profile))
    #        if role_name != None and ctx.guild:
    #            role = self.bot.pull_role(ctx.guild, role_name)
    #            if role:
    #                await ctx.author.add_roles(role)
    #        embed.clear_fields()
    #        fieldadd()
    #        embed.color = discord.Color.gold()
    #        for react in reacts:
    #            await configmsg.remove_reaction(react, ctx.bot.user)
    #        await configmsg.edit(embed=embed, allowed_mentions=allowed_mentions)

    # marr is pissed off mode
    @commands.command(name='pissedmode')
    async def pissedmode(self, ctx):
        if ctx.author.id != 212719295124209664:
            await ctx.send ("You cannot use this command. Only Marr can use this command.")
            return 
        self.mode_enabled = not self.mode_enabled
        status = "enabled" if self.mode_enabled else "disabled"
        await ctx.send(f"Pissed off mode is now {status}.")

    # golden is pissed off mode
    @commands.command(name='angwymode')
    async def angwymode(self, ctx):
        if ctx.author.id != 765919439202811938:
            await ctx.send ("You cannot use this command. Only Golden can use this command.")
            return
        self.angwy_enabled = not self.angwy_enabled
        status = "enabled" if self.angwy_enabled else "disabled"
        await ctx.send(f"Angwy mode is now {status}.")

    @Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()

        if (
            message.author.bot
            or message.is_system()
            or not message.guild
            or not message.reference
            or message.type != discord.MessageType.reply
        ):
            return

        try:
            refmessage = await message.channel.fetch_message(
                message.reference.message_id
            )
            if (
                refmessage.author.id == message.author.id
                or not message.guild.get_member(refmessage.author.id)
            ):
                return
        except:
            return
    
        preference = self.check_override(refmessage)
        if not preference:
                return

        async def wrap_violation(message):
            if not get_config(message.guild.id, "reaction", "noreply_remind_every"):
                return
            noreply_remind = (
                3
                if get_config(message.guild.id, "reaction", "noreply_remind_every") > 3
                else get_config(message.guild.id, "reaction", "noreply_remind_every")
            )

            if not get_config(message.guild.id, "reaction", "noreply_threshold"):
                return
            noreply_thres = (
                10
                if get_config(message.guild.id, "reaction", "noreply_threshold") > 10
                else get_config(message.guild.id, "reaction", "noreply_threshold")
            )
            try:
                await self.add_violation(message)
                return
            except discord.errors.Forbidden:
                if not (
                    message.channel.permissions_for(message.guild.me).add_reactions
                    and message.channel.permissions_for(
                        message.guild.me
                    ).manage_messages
                    and message.channel.permissions_for(
                        message.guild.me
                    ).moderate_members
                ):
                    return
                self.violations[message.guild.id][message.author.id] += 1
                cur_violation_count = self.violations[message.guild.id][
                    message.author.id
                ]
                if (
                    cur_violation_count > 1
                    and cur_violation_count % noreply_remind == 0
                ):
                    try:
                        await message.reply(
                            content=f"""**{message.author.mention}, You have me blocked, or you have DMs disabled!**
    **Do not reply ping users who do not wish to be pinged.**
    You have currently received {cur_violation_count} violation(s).
    {noreply_thres} violations will result in a penalty.""",
                            file=discord.File("assets/noreply.png"),
                        )
                    except discord.errors.NotFound:
                        return await message.reply(
                            content=f"{message.author.mention} immediately deleted their own message.\n{message.author.display_name} now has `{self.violations[message.guild.id][message.author.id]}` violation(s).",
                            mention_author=True,
                        )

        # If not reply pinged...
        if (
            preference == "pleasereplyping"
            and refmessage.author not in message.mentions
        ):
            try:
                await message.add_reaction("<:pleaseping:1258418052651942053>")
            except discord.errors.NotFound:
                pass
            except discord.errors.Forbidden as err:
                if err.code == 90001:
                    pass
            pokemsg = await message.reply(
                content=refmessage.author.mention, mention_author=False
            )
            await self.bot.await_message(message.channel, refmessage.author, 86400)
            return await pokemsg.delete()

        # If reply pinged at all...
        elif preference == "noreplyping" and refmessage.author in message.mentions:
            try:
                await message.add_reaction("<:noping:1258418038504689694>")
            except discord.errors.NotFound:
                await message.channel.send(
                    f"*thump thump* {message.author.mention} Quickdeleting a message that violates ping preferences is not cool!",
                    delete_after=5.0,
                )
            except discord.errors.Forbidden as err:
                if err.code == 90001:
                    return self.bot.dispatch(
                        "autotoss_blocked", message, message.author
                    )
            if self.mode_enabled and refmessage.author.id == 212719295124209664:
                await message.reply(content="# Stop pinging Marr. Marr has the 'No Ping' role. DO NOT PING MARR.", mention_author=True)
            if self.angwy_enabled and refmessage.author.id == 765919439202811938:
                await message.reply(content="# Stop pinging Golden. Golden has the 'No Ping' role. DO NOT PING GOLDEN.", mention_author=True)
            await wrap_violation(message)
            return

        # If reply pinged in a window of time...
        elif (
            preference == "waitbeforereplyping"
            and refmessage.author in message.mentions
        ):
            if message.guild.id not in self.timers:
                self.timers[message.guild.id] = {}
            self.timers[message.guild.id][refmessage.author.id] = int(
                refmessage.created_at.timestamp()
            )
            if (
                int(message.created_at.timestamp()) - 30
                <= self.timers[message.guild.id][refmessage.author.id]
            ):
                try:
                    await message.add_reaction("<:waitbeforeping:1258418064781738076>")
                except discord.errors.NotFound:
                    await message.channel.send(
                        f"*thump thump* {message.author.mention} Quickdeleting a message that violates ping preferences is not cool!",
                        delete_after=5.0,
                    )
                except discord.errors.Forbidden as err:
                    if err.code == 90001:
                        return self.bot.dispatch(
                            "autotoss_blocked", message, message.author
                        )
                await wrap_violation(message)
            return

    @tasks.loop(hours=1)
    async def counttimer(self):
        await self.bot.wait_until_ready()
        self.violations = {}


async def setup(bot):
    await bot.add_cog(Reply(bot))
