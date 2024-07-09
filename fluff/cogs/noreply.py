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
        self.violations = {}
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
        guild_id = message.guild.id
        user_id = message.author.id

        #checks if youre staff so this doesnt trigger
        staff_roles = [
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "modrole")
            ),
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "adminrole")
            ),
            self.bot.pull_role(
                message.guild, get_config(message.guuild.id, "staff", "botrole")
            )
        ]
        if any ([staff_role in message.author.roles for staff_role in staff_roles]):
            return
        
        if guild_id not in self.violations:
            self.violations[guild_id] = {}
        if user_id not in self.violations[guild_id]:
            self.violations[guild_id][user_id] = 0
        
        self.violations[guild_id][user_id] += 1

        if self.violations[guild_id][user_id] % 5 == 0:
            await message.reply(
                "**Do not reply ping users who do not wish to be pinged.**\nBe mindful of others' preferences. Failure to follow this rule may result in consequences.",
                mention_author=False
            )

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

    @tasks.loop(hours=24)
    async def counttimer(self):
        await self.bot.wait_until_ready()
        self.nopingreminders = {}

    @Cog.listener()
    async def on_member_update(self, before, after):
        new_roles = set(after.roles) - set(before.roles)

        role_preferences = {
            "Please Ping": "pleasereplyping",
            "Ping after Delay": "waitbeforereplyping",
            "No Ping": "noreplyping",
        }
        for role in new_roles:
            if role.name in role_preferences:
                profile = fill_profile(after.id)
                profile["replypref"] = role_preferences[role.name]
                set_userfile(after.id, "profile", json.dumps(profile))
                break

async def setup(bot):
    await bot.add_cog(Reply(bot))
