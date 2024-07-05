import discord
from discord.ext.commands import Cog
from discord.ext import commands, tasks
import json
import re
import datetime
import asyncio
from helpers.datafiles import get_guildfile, get_userfile
from helpers.checks import ismod
from helpers.sv_config import get_config
from helpers.datafiles import get_userfile, fill_profile, set_userfile
from helpers.embeds import stock_embed, author_embed


class Reply(Cog):
    """
    A cog that stops people from ping replying people who don't want to be.
    """

    def __init__(self, bot):
        self.bot = bot
        self.pingreminders = {}
        self.timers = {}
        self.counttimer.start()
        self.last_eval_result = None
        self.previous_eval_code = None

    def cog_unload(self):
        self.counttimer.cancel()

    def check_override(self, message):
        if not message.guild:
            return None
        setting_roles = [
            (self.bot.pull_role(message.guild, "Please Ping"), "pleaseping"),
            (
                self.bot.pull_role(message.guild, "Ping after Delay"),
                "pingafterdelay",
            ),
            (self.bot.pull_role(message.guild, "No Ping"), "noping"),
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
        if not get_config(message.guild.id, "staff", "noreplythreshold"):
            return
        maximum = (
            10
            if get_config(message.guild.id, "staff", "noreplythreshold") > 10
            else get_config(message.guild.id, "staff", "noreplythreshold")
        )
        if (
            not maximum
            or not any(staff_roles)
            or any([staff_role in message.author.roles for staff_role in staff_roles])
            or self.bot.is_owner(message.author)
        ):
            return

        if message.guild.id not in self.nopingreminders:
            self.nopingreminders[message.guild.id] = {}
        if message.author.id not in self.nopingreminders[message.guild.id]:
            self.nopingreminders[message.guild.id][message.author.id] = False
            usertracks = get_guildfile(message.guild.id, "usertrack")
            if (
                self
            ):
                return await message.reply(
                    content="**Do not reply ping users who do not wish to be pinged.**\n"
                    + "Be mindful of others' preferences. This message will not be shown again, but may result in consequences, so please be mindful.",
                    file=discord.File("assets/noreply.png"),
                    mention_author=True,
                )

        self.nopingreminders[message.guild.id][message.author.id] = True

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def replyconfig(self, ctx):
        """This sets your reply ping preferences.

        Use the reactions to pick your setting.
        See the [documentation](https://3gou.0ccu.lt/as-a-user/reply-ping-preferences/) for more info.

        No arguments."""
        override = self.check_override(ctx.message)
        if override:
            return await ctx.reply(
                content="You already have an indicator role, you don't need to set your preferences here.",
                mention_author=False,
            )

        profile = fill_profile(ctx.author.id)
        embed = stock_embed(self.bot)
        embed.title = "Your reply preference"
        embed.color = discord.Color.red()
        author_embed(embed, ctx.author)
        allowed_mentions = discord.AllowedMentions(replied_user=False)

        def fieldadd():
            unconfigured = "🔘" if not profile["replypref"] else "⚫"
            embed.add_field(
                name="🤷 Unconfigured",
                value=unconfigured + " Indicates that you have no current preference.",
                inline=False,
            )

            pleaseping = "🔘" if profile["replypref"] == "pleasereplyping" else "⚫"
            embed.add_field(
                name="<:pleaseping:1258418052651942053> Please Reply Ping",
                value=pleaseping
                + " Indicates that you would like to be pinged in replies.",
                inline=False,
            )

            waitbeforeping = (
                "🔘" if profile["replypref"] == "waitbeforereplyping" else "⚫"
            )
            embed.add_field(
                name="<:waitbeforeping:1258418064781738076> Wait Before Reply Ping",
                value=waitbeforeping
                + " Indicates that you would only like to be pinged after some time has passed.",
                inline=False,
            )

            noping = "🔘" if profile["replypref"] == "noreplyping" else "⚫"
            embed.add_field(
                name="<:noping:1258418038504689694> No Reply Ping",
                value=noping
                + " Indicates that you do not wish to be reply pinged whatsoever.",
                inline=False,
            )

        fieldadd()

        reacts = [
            "🤷",
            "<:pleaseping:1258418052651942053>",
            "<:waitbeforeping:1258418064781738076>",
            "<:noping:1258418038504689694",
        ]
        configmsg = await ctx.reply(embed=embed, mention_author=False)
        for react in reacts:
            await configmsg.add_reaction(react)
        embed.color = discord.Color.green()
        await configmsg.edit(embed=embed, allowed_mentions=allowed_mentions)

        def reactioncheck(r, u):
            return u.id == ctx.author.id and str(r.emoji) in reacts

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=30.0, check=reactioncheck
            )
        except asyncio.TimeoutError:
            embed.color = discord.Color.default()
            for react in reacts:
                await configmsg.remove_reaction(react, ctx.bot.user)
            return await configmsg.edit(
                embed=embed,
                allowed_mentions=allowed_mentions,
            )
        else:
            if str(reaction) == reacts[0]:
                profile["replypref"] = None
            elif str(reaction) == reacts[1]:
                profile["replypref"] = "pleasereplyping"
            elif str(reaction) == reacts[2]:
                profile["replypref"] = "waitbeforereplyping"
            elif str(reaction) == reacts[3]:
                profile["replypref"] = "noreplyping"
            set_userfile(ctx.author.id, "profile", json.dumps(profile))
            embed.clear_fields()
            fieldadd()
            embed.color = discord.Color.gold()
            for react in reacts:
                await configmsg.remove_reaction(react, ctx.bot.user)
            await configmsg.edit(embed=embed, allowed_mentions=allowed_mentions)

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
            preference = fill_profile(refmessage.author.id)["replypref"]
            if not preference:
                return

        async def wrap_violation(message):
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

                await message.author.timeout(datetime.timedelta(minutes=10))
                return await message.reply(
                    content=f"**Congratulations, {message.author.mention}, you absolute dumbass.**\nAs your reward for blocking me to disrupt my function, here is a time out, just for you.",
                    mention_author=True,
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
            await message.add_reaction("<:pleaseping:1258418052651942053>")
            pokemsg = await message.reply(content=refmessage.author.mention,mention_author=False)
            await self.bot.await_message(message.channel, refmessage.author, 86400)
            return await pokemsg.delete()

        # If reply pinged at all...
        elif preference == "noreplyping" and refmessage.author in message.mentions:
            await message.add_reaction("<:noping:1258418038504689694>")
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
                await message.add_reaction("<:waitbeforeping:1258418064781738076>")
            return
        
        @Cog.listener()
        async def on_member_update(self, before, after):
            await self.bot.wait_until_ready()

            if before.roles == after.roles:
                return
            
            role_mapping = {
                "Please Ping": "pleaseping",
                "Ping after Delay": "pingafterdelay",
                "No Ping": "norping"
            }

            new_setting = None
            for role_name, setting in role_mapping.items():
                role = self.bot.pull_role(after.guild, role_name)
                if role in after.roles:
                    new_setting = setting
                    break

            if new_setting:
                profile = fill_profile(after.id)
                profile["replypref"] = new_setting
                set_userfile(after.id, "profile", json.dumps(profile))
            else:
                profile = fill_profile(after.id)
                profile["replypref"] = None
                set_userfile(after.id, "profile", json.dumps(profile))

    @tasks.loop(hours=24)
    async def counttimer(self):
        await self.bot.wait_until_ready()
        self.nopingreminders = {}


async def setup(bot):
    await bot.add_cog(Reply(bot))
