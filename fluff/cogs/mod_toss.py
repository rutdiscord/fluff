# This Cog contained code from Tosser2, which was made by OblivionCreator.
import discord
import json
import os
import asyncio
import zipfile
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.checks import ismod
from helpers.datafiles import toss_userlog, get_tossfile, set_tossfile
from helpers.placeholders import random_msg
from helpers.archive import log_channel
from helpers.embeds import (
    stock_embed,
    mod_embed,
    author_embed,
    createdat_embed,
    joinedat_embed,
)
from helpers.sv_config import get_config
from helpers.google import upload


class ModToss(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.poketimers = dict()
        # self.spamcounter = {}
        self.nocfgmsg = "Tossing isn't enabled for this server."

    def enabled(self, g):
        return all(
            (
                self.bot.pull_role(g, get_config(g.id, "toss", "tossrole")),
                self.bot.pull_category(g, get_config(g.id, "toss", "tosscategory")),
                get_config(g.id, "toss", "tosschannels"),
            )
        )

    def username_system(self, user):
        return (
            "**"
            + self.bot.pacify_name(user.global_name)
            + f"** [{self.bot.pacify_name(str(user))}]"
            if user.global_name
            else f"**{self.bot.pacify_name(str(user))}**"
        )

    # Thank you to https://stackoverflow.com/a/29489919 for this function.
    def principal_period(self, s):
        i = (s + s).find(s, 1, -1)
        return None if i == -1 else s[:i]

    def is_rolebanned(self, member, hard=True):
        roleban = [
            r
            for r in member.guild.roles
            if r
            == self.bot.pull_role(
                member.guild, get_config(member.guild.id, "toss", "tossrole")
            )
        ]
        if roleban:
            if (
                self.bot.pull_role(
                    member.guild, get_config(member.guild.id, "toss", "tossrole")
                )
                in member.roles
            ):
                if hard:
                    return len([r for r in member.roles if not (r.managed)]) == 2
                return True

    def get_session(self, member):
        tosses = get_tossfile(member.guild.id, "tosses")
        if not tosses:
            return None
        session = None
        if "LEFTGUILD" in tosses and str(member.id) in tosses["LEFTGUILD"]:
            session = False
        for channel in tosses:
            if channel == "LEFTGUILD":
                continue
            if str(member.id) in tosses[channel]["tossed"]:
                session = channel
                break
        return session

    async def new_session(self, guild):
        staff_roles = [
            self.bot.pull_role(guild, get_config(guild.id, "staff", "modrole")),
            self.bot.pull_role(guild, get_config(guild.id, "staff", "adminrole")),
        ]
        bot_role = self.bot.pull_role(guild, get_config(guild.id, "staff", "botrole"))
        tosses = get_tossfile(guild.id, "tosses")

        for c in get_config(guild.id, "toss", "tosschannels"):
            if c not in [g.name for g in guild.channels]:
                if c not in tosses:
                    tosses[c] = {"tossed": {}, "untossed": [], "left": []}
                    set_tossfile(guild.id, "tosses", json.dumps(tosses))

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=False
                    ),
                    guild.me: discord.PermissionOverwrite(read_messages=True),
                }
                if bot_role:
                    overwrites[bot_role] = discord.PermissionOverwrite(
                        read_messages=True
                    )
                for staff_role in staff_roles:
                    if not staff_role:
                        continue
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        read_messages=True
                    )
                toss_channel = await guild.create_text_channel(
                    c,
                    reason="Fluff Toss",
                    category=self.bot.pull_category(
                        guild, get_config(guild.id, "toss", "tosscategory")
                    ),
                    overwrites=overwrites,
                    topic=get_config(guild.id, "toss", "tosstopic"),
                )

                return toss_channel

    async def perform_toss(self, user, staff, toss_channel):
        toss_role = self.bot.pull_role(
            user.guild, get_config(user.guild.id, "toss", "tossrole")
        )

        if toss_role in user.roles:
            return False

        roles = []
        for rx in user.roles:
            if rx != user.guild.default_role and rx != toss_role:
                roles.append(rx)

        tosses = get_tossfile(user.guild.id, "tosses")
        tosses[toss_channel.name]["tossed"][str(user.id)] = [role.id for role in roles]
        set_tossfile(user.guild.id, "tosses", json.dumps(tosses))

        await user.add_roles(toss_role, reason="User tossed.")
        fail_roles = []
        if roles:
            for rr in roles:
                if not rr.is_assignable():
                    fail_roles.append(rr)
                    roles.remove(rr)
            await user.remove_roles(
                *roles,
                reason=f"User tossed by {staff} ({staff.id})",
                atomic=False,
            )

        return fail_roles, roles

    @commands.bot_has_permissions(embed_links=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["tossed", "session"])
    async def sessions(self, ctx):
        """This shows the open toss sessions.

        Use this in a toss channel to show who's in it.

        No arguments."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        embed = stock_embed(self.bot)
        embed.title = "👁‍🗨 Toss Channel Sessions..."
        embed.color = ctx.author.color
        tosses = get_tossfile(ctx.guild.id, "tosses")

        if ctx.channel.name in get_config(ctx.guild.id, "toss", "tosschannels"):
            channels = [ctx.channel.name]
        else:
            channels = get_config(ctx.guild.id, "toss", "tosschannels")

        for c in channels:
            if c in [g.name for g in ctx.guild.channels]:
                if c not in tosses or not tosses[c]["tossed"]:
                    embed.add_field(
                        name=f"🟡 #{c}",
                        value="__Empty__\n> Please close the channel.",
                        inline=True,
                    )
                else:
                    userlist = "\n".join(
                        [
                            f"> {self.username_system(user)}"
                            for user in [
                                await self.bot.fetch_user(str(u))
                                for u in tosses[c]["tossed"].keys()
                            ]
                        ]
                    )
                    embed.add_field(
                        name=f"🔴 #{c}",
                        value=f"__Occupied__\n{userlist}",
                        inline=True,
                    )
            else:
                embed.add_field(name=f"🟢 #{c}", value="__Available__", inline=True)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.bot_has_permissions(
        manage_roles=True, manage_channels=True, add_reactions=True
    )
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["roleban", "mute"])
    async def toss(self, ctx, users: commands.Greedy[discord.Member]):
        """This tosses a user.

        Please refer to the tossing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/).

        - `users`
        The users to toss."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)

        staff_roles = [
            self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "staff", "modrole")),
            self.bot.pull_role(
                ctx.guild, get_config(ctx.guild.id, "staff", "adminrole")
            ),
        ]
        toss_role = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "toss", "tossrole")
        )
        if not any(staff_roles) or not toss_role:
            return await ctx.reply(
                content="PLACEHOLDER no staff or toss role configured",
                mention_author=False,
            )
        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )
        modlog_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "logging", "modlog")
        )

        errors = ""
        for us in users:
            if us.id == ctx.author.id:
                errors += f"\n- {self.username_system(us)}\n  You cannot toss yourself."
            elif us.id == self.bot.application_id:
                errors += f"\n- {self.username_system(us)}\n  You cannot toss the bot."
            elif self.get_session(us) and toss_role in us.roles:
                errors += (
                    f"\n- {self.username_system(us)}\n  This user is already tossed."
                )
            else:
                continue
            users.remove(us)
        if not users:
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in toss command from {ctx.author.mention}...\n- Nobody was tossed.\n```diff"
                + errors
                + "\n```\n"
            )

        if ctx.channel.name in get_config(ctx.guild.id, "toss", "tosschannels"):
            addition = True
            toss_channel = ctx.channel
        elif all(
            [
                c in [g.name for g in ctx.guild.channels]
                for c in get_config(ctx.guild.id, "toss", "tosschannels")
            ]
        ):
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in toss command from {ctx.author.mention}...\n- No toss channels available.\n```diff"
                + errors
                + "\n```\n"
            )
        else:
            addition = False
            toss_channel = await self.new_session(ctx.guild)

        for us in users:
            try:
                failed_roles, previous_roles = await self.perform_toss(
                    us, ctx.author, toss_channel
                )
                await toss_channel.set_permissions(us, read_messages=True)
            except commands.MissingPermissions:
                errors += f"\n- {self.username_system(us)}\n  Missing permissions to toss this user."
                continue

            toss_userlog(
                ctx.guild.id,
                us.id,
                ctx.author,
                ctx.message.jump_url,
                toss_channel.id,
            )

            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed, us, True)
                embed.color = ctx.author.color
                embed.title = "🚷 Toss"
                embed.description = f"{us.mention} was tossed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]\n> This toss takes place in {toss_channel.mention}..."
                createdat_embed(embed, us)
                joinedat_embed(embed, us)
                prevlist = []
                if len(previous_roles) > 0:
                    for role in previous_roles:
                        prevlist.append("<@&" + str(role.id) + ">")
                    prevlist = ",".join(reversed(prevlist))
                else:
                    prevlist = "None"
                embed.add_field(
                    name="🎨 Previous Roles",
                    value=prevlist,
                    inline=False,
                )
                if failed_roles:
                    faillist = []
                    for role in failed_roles:
                        faillist.append("<@&" + str(role.id) + ">")
                    faillist = ",".join(reversed(faillist))
                    embed.add_field(
                        name="🚫 Failed Roles",
                        value=faillist,
                        inline=False,
                    )
                await notify_channel.send(embed=embed)

            if modlog_channel and modlog_channel != notify_channel:
                embed = stock_embed(self.bot)
                embed.color = discord.Color.from_str("#FF0000")
                embed.title = "🚷 Toss"
                embed.description = f"{us.mention} was tossed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]"
                mod_embed(embed, us, ctx.author)
                await modlog_channel.send(embed=embed)

        await ctx.message.add_reaction("🚷")

        if errors and notify_channel:
            return await notify_channel.send(
                f"Error in toss command from {ctx.author.mention}...\n- Some users could not be tossed.\n```diff"
                + errors
                + "\n```\n"
            )

        if not addition:
            toss_pings = ", ".join([us.mention for us in users])
            await toss_channel.send(
                f"{toss_pings}\nYou were tossed by {self.bot.pacify_name(ctx.author.display_name)}.\n{get_config(ctx.guild.id, 'toss', 'tossmsg')}"
            )

            def check(m):
                return m.author in users and m.channel == toss_channel

            try:
                self.poketimers[str(toss_channel.id)] = await self.bot.wait_for(
                    "message", timeout=300, check=check
                )
            except asyncio.TimeoutError:
                del self.poketimers[str(toss_channel.id)]
                pokemsg = await toss_channel.send(ctx.author.mention)
                await pokemsg.edit(content="⏰", delete_after=5)
            else:
                try:
                    pokemsg = await toss_channel.send(ctx.author.mention)
                    await pokemsg.edit(content="🫳⏰", delete_after=5)
                except discord.errors.NotFound:
                    return

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["unroleban", "unmute"])
    async def untoss(self, ctx, users: commands.Greedy[discord.Member] | None):
        """This untosses a user.

        Please refer to the tossing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/).

        - `users`
        The users to untoss. Optional."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        if ctx.channel.name not in get_config(ctx.guild.id, "toss", "tosschannels"):
            return await ctx.reply(
                content="This command must be run inside of a toss channel.",
                mention_author=False,
            )

        tosses = get_tossfile(ctx.guild.id, "tosses")
        if not users:
            users = [
                ctx.guild.get_member(int(u))
                for u in tosses[ctx.channel.name]["tossed"].keys()
            ]

        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )
        toss_role = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "toss", "tossrole")
        )
        output = ""
        invalid = []

        for us in users:
            if us.id == self.bot.application_id:
                output += "\n" + random_msg(
                    "warn_targetbot", authorname=ctx.author.name
                )
            elif us.id == ctx.author.id:
                output += "\n" + random_msg(
                    "warn_targetself", authorname=ctx.author.name
                )
            elif (
                str(us.id) not in tosses[ctx.channel.name]["tossed"]
                and toss_role not in us.roles
            ):
                output += "\n" + f"{self.username_system(us)} is not already tossed."
            else:
                continue
            users.remove(us)
        if not users:
            return await ctx.reply(
                output
                + "\n\n"
                + "There's nobody left to untoss, so nobody was untossed.",
                mention_author=False,
            )

        for us in users:
            self.busy = True
            roles = tosses[ctx.channel.name]["tossed"][str(us.id)]
            if us.id not in tosses[ctx.channel.name]["untossed"]:
                tosses[ctx.channel.name]["untossed"].append(us.id)
            del tosses[ctx.channel.name]["tossed"][str(us.id)]

            if roles:
                roles = [ctx.guild.get_role(r) for r in roles]
                for r in roles:
                    if not r or not r.is_assignable():
                        roles.remove(r)
                await us.add_roles(
                    *roles,
                    reason=f"Untossed by {ctx.author} ({ctx.author.id})",
                    atomic=False,
                )
            await us.remove_roles(
                toss_role,
                reason=f"Untossed by {ctx.author} ({ctx.author.id})",
            )

            await ctx.channel.set_permissions(us, overwrite=None)

            output += "\n" + f"{self.username_system(us)} has been untossed."
            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed, us)
                embed.color = ctx.author.color
                embed.title = "🚶 Untoss"
                embed.description = f"{us.mention} was untossed by {ctx.author.mention} [`#{ctx.channel.name}`]"
                createdat_embed(embed, us)
                joinedat_embed(embed, us)
                prevlist = []
                if len(roles) > 0:
                    for role in roles:
                        prevlist.append("<@&" + str(role.id) + ">")
                    prevlist = ",".join(reversed(prevlist))
                else:
                    prevlist = "None"
                embed.add_field(
                    name="🎨 Restored Roles",
                    value=prevlist,
                    inline=False,
                )
                await notify_channel.send(embed=embed)

        set_tossfile(ctx.guild.id, "tosses", json.dumps(tosses))
        self.busy = False

        if invalid:
            output += (
                "\n\n"
                + "I was unable to untoss these users: "
                + ", ".join([str(iv) for iv in invalid])
            )

        if not tosses[ctx.channel.name]:
            output += "\n\n" + "There is nobody left in this session."

        await ctx.reply(content=output, mention_author=False)

    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def close(self, ctx, archive=True):
        """This closes a mute session.

        Please refer to the tossing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/).
        In Fluff, this command also sends archival data to Google Drive.

        - No arguments.
        """
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        if ctx.channel.name not in get_config(ctx.guild.id, "toss", "tosschannels"):
            return await ctx.reply(
                content="This command must be run inside of a muted channel.",
                mention_author=False,
            )

        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )
        logging_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "logging", "modlog")
        )
        tosses = get_tossfile(ctx.guild.id, "tosses")

        try:
            if tosses[ctx.channel.name]["tossed"]:
                return await ctx.reply(
                    content="You must unmute everyone first!", mention_author=True
                )
        except KeyError:
            # This might be a bad idea.
            return await ctx.channel.delete(
                reason="Fluff Mute (No one was muted, KeyError except)"
            )

        embed = stock_embed(self.bot)
        embed.title = "Muted Session Closed (Fluff)"
        embed.description = f"`#{ctx.channel.name}`'s session was closed by {ctx.author.mention} ({ctx.author.id})."
        embed.color = ctx.author.color
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

        if archive:
            async with ctx.channel.typing():
                dotraw, dotzip = await log_channel(
                    self.bot, ctx.channel, zip_files=True
                )

            users = []
            for uid in (
                tosses[ctx.channel.name]["untossed"] + tosses[ctx.channel.name]["left"]
            ):
                if self.bot.get_user(uid):
                    users.append(self.bot.get_user(uid))
                else:
                    user = await self.bot.fetch_user(uid)
                    users.append(user)
            user = f""

            if users:
                firstuser = f"{users[0].name} {users[0].id}"
            else:
                firstuser = f"unspecified (logged by {ctx.author.name})"

            filename = (
                ctx.message.created_at.astimezone().strftime("%Y-%m-%d")
                + f" {firstuser}"
            )
            reply = (
                f"📕 I've archived that as: `{filename}.txt`\nThis mute session had the following users:\n- "
                + "\n- ".join([f"{self.username_system(u)} ({u.id})" for u in users])
            )
            dotraw += f"\n{ctx.message.created_at.astimezone().strftime('%Y/%m/%d %H:%M')} {self.bot.user} [BOT]\n{reply}"

            if not os.path.exists(
                f"data/servers/{ctx.guild.id}/toss/archives/sessions/{ctx.channel.id}"
            ):
                os.makedirs(
                    f"data/servers/{ctx.guild.id}/toss/archives/sessions/{ctx.channel.id}"
                )
            with open(
                f"data/servers/{ctx.guild.id}/toss/archives/sessions/{ctx.channel.id}/{filename}.txt",
                "w",
                encoding="UTF-8",
            ) as filetxt:
                filetxt.write(dotraw)
            if dotzip:
                with open(
                    f"data/servers/{ctx.guild.id}/toss/archives/sessions/{ctx.channel.id}/{filename} (files).zip",
                    "wb",
                ) as filezip:
                    filezip.write(dotzip.getbuffer())

            embed.add_field(
                name="🗒️ Text",
                value=f"{filename}.txt\n"
                + f"`"
                + str(len(dotraw.split("\n")))
                + "` lines, "
                + f"`{len(dotraw.split())}` words, "
                + f"`{len(dotraw)}` characters.",
                inline=True,
            )
            if dotzip:
                embed.add_field(
                    name="📁 Files",
                    value=f"{filename} (files).zip"
                    + "\n"
                    + f"`{len(zipfile.ZipFile(dotzip, 'r', zipfile.ZIP_DEFLATED).namelist())}` files in the zip file.",
                    inline=True,
                )

            await upload(
                ctx,
                filename,
                f"data/servers/{ctx.guild.id}/toss/archives/sessions/{ctx.channel.id}/",
                dotzip,
            )

        del tosses[ctx.channel.name]
        set_tossfile(ctx.guild.id, "tosses", json.dumps(tosses))

        channel = notify_channel if notify_channel else logging_channel
        if channel:
            await channel.send(embed=embed)
            await ctx.channel.delete(reason="Fluff Mute")
        return

    @Cog.listener()
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        if not self.enabled(member.guild):
            return
        notify_channel = self.bot.pull_channel(
            member.guild, get_config(member.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                member.guild, get_config(member.guild.id, "staff", "staffchannel")
            )

        tosses = get_tossfile(member.guild.id, "tosses")
        toss_channel = None

        if "LEFTGUILD" in tosses and str(member.id) in tosses["LEFTGUILD"]:
            for channel in tosses:
                if "left" in tosses[channel] and member.id in tosses[channel]["left"]:
                    toss_channel = discord.utils.get(
                        member.guild.channels, name=channel
                    )
                    break
            if toss_channel:
                toss_role = self.bot.pull_role(
                    member.guild, get_config(member.guild.id, "toss", "tossrole")
                )
                await member.add_roles(toss_role, reason="User tossed.")
                tosses[toss_channel.name]["tossed"][str(member.id)] = tosses[
                    "LEFTGUILD"
                ][str(member.id)]
                tosses[toss_channel.name]["left"].remove(member.id)
            else:
                toss_channel = await self.new_session(member.guild)
                failed_roles, previous_roles = await self.perform_toss(
                    member, member.guild.me, toss_channel
                )
                tosses = get_tossfile(member.guild.id, "tosses")
                tosses[toss_channel.name]["tossed"][str(member.id)] = tosses[
                    "LEFTGUILD"
                ][str(member.id)]
        else:
            return

        del tosses["LEFTGUILD"][str(member.id)]
        if not tosses["LEFTGUILD"]:
            del tosses["LEFTGUILD"]
        set_tossfile(member.guild.id, "tosses", json.dumps(tosses))

        await toss_channel.set_permissions(member, read_messages=True)
        tossmsg = await toss_channel.send(
            content=f"🔁 {self.username_system(member)} rejoined while tossed.\n{get_config(member.guild.id, 'toss', 'tossmsg_rejoin')}"
        )

        def check(m):
            return m.author in tosses and m.channel == toss_channel

        try:
            msg = await self.bot.wait_for("message", timeout=300, check=check)
        except asyncio.TimeoutError:
            try:
                pokemsg = await toss_channel.send(member.mention)
                await pokemsg.edit(content="⏰", delete_after=5)
            except discord.NotFound:
                return
        except discord.NotFound:
            return
        except asyncio.exceptions.CancelledError:
            return
        else:
            pokemsg = await toss_channel.send(member.mention)
            await pokemsg.edit(content="🫳⏰", delete_after=5)

        if notify_channel:
            tossmsg = await notify_channel.send(
                content=f"🔁 {self.username_system(member)} ({member.id}) rejoined while tossed. Continuing in {toss_channel.mention}..."
            )
        toss_userlog(
            member.guild.id,
            member.id,
            member.guild.me,
            tossmsg.jump_url,
            toss_channel.id,
        )
        return

    @Cog.listener()
    async def on_member_remove(self, member):
        await self.bot.wait_until_ready()
        if not self.enabled(member.guild):
            return

        session = self.get_session(member)
        if not session:
            return

        tosses = get_tossfile(member.guild.id, "tosses")
        if "LEFTGUILD" not in tosses:
            tosses["LEFTGUILD"] = {}
        tosses["LEFTGUILD"][str(member.id)] = tosses[session]["tossed"][str(member.id)]
        tosses[session]["left"].append(member.id)
        del tosses[session]["tossed"][str(member.id)]
        set_tossfile(member.guild.id, "tosses", json.dumps(tosses))

        notify_channel = self.bot.pull_channel(
            member.guild, get_config(member.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                member.guild, get_config(member.guild.id, "staff", "staffchannel")
            )
        toss_channel = self.bot.pull_channel(member.guild, session)
        try:
            await member.guild.fetch_ban(member)
            out = f"🔨 {self.username_system(member)} got banned while tossed."
        except discord.NotFound:
            out = f"🚪 {self.username_system(member)} left while tossed."
        except discord.Forbidden:
            out = f"❓ {self.username_system(member)} was removed from the server.\nI do not have Audit Log permissions to tell why."
        if notify_channel:
            await notify_channel.send(out)
        if toss_channel:
            await toss_channel.send(out)

    # @Cog.listener()
    # async def on_member_update(self, before, after):
    #     await self.bot.wait_until_ready()
    #     if not self.enabled(after.guild):
    #         return
    #     while self.busy:
    #         await asyncio.sleep(1)
    #     if self.is_rolebanned(before) and not self.is_rolebanned(after):
    #         session = self.get_session(after)
    #         if not session:
    #             return

    #         tosses = get_tossfile(after.guild.id, "tosses")
    #         tosses[session]["untossed"].append(after.id)
    #         del tosses[session]["tossed"][str(after.id)]
    #         set_tossfile(after.guild.id, "tosses", json.dumps(tosses))

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.bot.wait_until_ready()
        if self.enabled(channel.guild) and channel.name in get_config(
            channel.guild.id, "toss", "tosschannels"
        ):
            tosses = get_tossfile(channel.guild.id, "tosses")
            if channel.name not in tosses:
                return
            await self.poketimers[str(channel.id)].cancel()
            del self.poketimers[str(channel.id)]
            del tosses[channel.name]
            set_tossfile(channel.guild.id, "tosses", json.dumps(tosses))

    @Cog.listener()
    async def on_autotoss_blocked(
        self, message, msgauthor
    ):  # lazily copied and pasted 2!
        await self.bot.wait_until_ready()

        if not self.enabled(
            message.guild
        ):  # this should never ever fire but its here anyway
            return await message.reply(self.nocfgmsg, mention_author=False)

        staff_roles = [
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "modrole")
            ),
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "adminrole")
            ),
        ]
        toss_role = self.bot.pull_role(
            message.guild, get_config(message.guild.id, "toss", "tossrole")
        )
        if not any(staff_roles) or not toss_role:
            return await message.reply(
                content="PLACEHOLDER no staff or toss role configured",
                mention_author=False,
            )
        notify_channel = self.bot.pull_channel(
            message.guild, get_config(message.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                message.guild, get_config(message.guild.id, "staff", "staffchannel")
            )
        modlog_channel = self.bot.pull_channel(
            message.guild, get_config(message.guild.id, "logging", "modlog")
        )
        # end logic lazily ported from actual tossing
        error = ""

        if self.get_session(msgauthor) and toss_role in msgauthor.roles:
            error += (
                f"\n- {self.username_system(msgauthor)}\n  This user is already tossed."
            )

        if all(
            [
                c in [g.name for g in message.guild.channels]
                for c in get_config(message.guild.id, "toss", "tosschannels")
            ]
        ):
            await message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in toss command from {msgauthor.mention}...\n- No toss channels available.\n```diff"
                + error
                + "\n```\n"
            )
        else:
            toss_channel = await self.new_session(message.guild)
            try:
                failed_roles, previous_roles = await self.perform_toss(
                    msgauthor, message.guild.me, toss_channel
                )
                await toss_channel.set_permissions(msgauthor, read_messages=True)
                await message.reply(
                    f"{self.username_system(message.author)} has been automatically muted for blocking Fluff."
                )
                await toss_channel.send(
                    f"{msgauthor.mention}, {get_config(message.guild.id, 'toss', 'tossmsg_noreply_blocked')}",
                    file=discord.File("assets/noreply.png"),
                )
            except commands.MissingPermissions:
                error += f"\n- {self.username_system(msgauthor)}\n  Missing permissions to toss this user."

        toss_userlog(
            message.guild.id,
            msgauthor.id,
            message.guild.me,
            message.jump_url,
            toss_channel.id,
        )

        if notify_channel:
            embed = stock_embed(self.bot)
            author_embed(embed, msgauthor, True)
            embed.color = msgauthor.color
            embed.title = "🚷 Toss"
            embed.description = f"{msgauthor.mention} was tossed by {message.guild.me.mention} [`#{message.channel.name}`] [[Jump]({message.jump_url})]\n> This toss takes place in {toss_channel.mention}..."
            createdat_embed(embed, msgauthor)
            joinedat_embed(embed, msgauthor)
            prevlist = []
            if len(previous_roles) > 0:
                for role in previous_roles:
                    prevlist.append("<@&" + str(role.id) + ">")
                prevlist = ",".join(reversed(prevlist))
            else:
                prevlist = "None"
            embed.add_field(
                name="🎨 Previous Roles",
                value=prevlist,
                inline=False,
            )
            if failed_roles:
                faillist = []
                for role in failed_roles:
                    faillist.append("<@&" + str(role.id) + ">")
                faillist = ",".join(reversed(faillist))
                embed.add_field(
                    name="🚫 Failed Roles",
                    value=faillist,
                    inline=False,
                )
            await notify_channel.send(embed=embed)

        if modlog_channel and modlog_channel != notify_channel:
            embed = stock_embed(self.bot)
            embed.color = discord.Color.from_str("#FF0000")
            embed.title = "🚷 Toss"
            embed.description = f"{msgauthor.mention} was tossed by {message.guild.me.mention} [`#{message.channel.name}`] [[Jump]({message.jump_url})]"
            mod_embed(embed, msgauthor, message.guild.me)
            await modlog_channel.send(embed=embed)

    @Cog.listener()
    async def on_violation_threshold_reached(self, message, msgauthor):
        await self.bot.wait_until_ready()

        if not self.enabled(
            message.guild
        ):  # this should never ever fire but its here anyway
            return await message.reply(self.nocfgmsg, mention_author=False)

        # begin logic lazily ported from actual tossing
        staff_roles = [
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "modrole")
            ),
            self.bot.pull_role(
                message.guild, get_config(message.guild.id, "staff", "adminrole")
            ),
        ]
        toss_role = self.bot.pull_role(
            message.guild, get_config(message.guild.id, "toss", "tossrole")
        )
        if not any(staff_roles) or not toss_role:
            return await message.reply(
                content="PLACEHOLDER no staff or toss role configured",
                mention_author=False,
            )
        notify_channel = self.bot.pull_channel(
            message.guild, get_config(message.guild.id, "toss", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                message.guild, get_config(message.guild.id, "staff", "staffchannel")
            )
        modlog_channel = self.bot.pull_channel(
            message.guild, get_config(message.guild.id, "logging", "modlog")
        )
        # end logic lazily ported from actual tossing

        if self.get_session(msgauthor) or toss_role in msgauthor.roles:
            return

        if all(
            [
                c in [g.name for g in message.guild.channels]
                for c in get_config(message.guild.id, "toss", "tosschannels")
            ]
        ):
            await message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in toss command from {msgauthor.mention}'s reply ping preference violation...\n- No toss channels available.\n```diff"
                + error
                + "\n```\n"
            )
        else:
            toss_channel = await self.new_session(message.guild)
            try:
                failed_roles, previous_roles = await self.perform_toss(
                    msgauthor, msgauthor.guild.me, toss_channel
                )
                await toss_channel.set_permissions(msgauthor, read_messages=True)
                await message.reply(
                    f"{self.username_system(message.author)} has been automatically muted for reaching the threshold for reply ping preference violation."
                )
                await toss_channel.send(
                    f"{msgauthor.mention}, {get_config(message.guild.id, 'toss', 'tossmsg_noreply')}",
                    file=discord.File("assets/noreply.png"),
                )
            except commands.MissingPermissions:
                error += f"\n- {self.username_system(msgauthor)}\n  Missing permissions to toss this user."

        toss_userlog(
            message.guild.id,
            msgauthor.id,
            message.guild.me,
            message.jump_url,
            toss_channel.id,
        )

        if notify_channel:
            embed = stock_embed(self.bot)
            author_embed(embed, msgauthor, True)
            embed.color = msgauthor.color
            embed.title = "🚷 Toss"
            embed.description = f"{msgauthor.mention} was tossed by {message.guild.me.mention} [`#{message.channel.name}`] [[Jump]({message.jump_url})]\n> This toss takes place in {toss_channel.mention}..."
            createdat_embed(embed, msgauthor)
            joinedat_embed(embed, msgauthor)
            prevlist = []
            if len(previous_roles) > 0:
                for role in previous_roles:
                    prevlist.append("<@&" + str(role.id) + ">")
                prevlist = ",".join(reversed(prevlist))
            else:
                prevlist = "None"
            embed.add_field(
                name="🎨 Previous Roles",
                value=prevlist,
                inline=False,
            )
            if failed_roles:
                faillist = []
                for role in failed_roles:
                    faillist.append("<@&" + str(role.id) + ">")
                faillist = ",".join(reversed(faillist))
                embed.add_field(
                    name="🚫 Failed Roles",
                    value=faillist,
                    inline=False,
                )
            await notify_channel.send(embed=embed)

        if modlog_channel and modlog_channel != notify_channel:
            embed = stock_embed(self.bot)
            embed.color = discord.Color.from_str("#FF0000")
            embed.title = "🚷 Toss"
            embed.description = f"{msgauthor.mention} was tossed by {message.guild.me.mention} [`#{message.channel.name}`] [[Jump]({message.jump_url})]"
            mod_embed(embed, msgauthor, message.guild.me)
            await modlog_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModToss(bot))
