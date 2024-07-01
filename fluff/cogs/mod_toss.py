# This Cog contained code from Tosser2, which was made by OblivionCreator.
import discord
import json
import os
import asyncio
# import random
import zipfile
# from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord.ext.commands import Cog
# from io import BytesIO
from helpers.checks import ismod
from helpers.datafiles import mute_userlog, get_mutefile, set_mutefile
from helpers.placeholders import random_msg
from helpers.archive import log_channel
from helpers.embeds import (
    stock_embed,
    # mod_embed,
    author_embed,
    createdat_embed,
    joinedat_embed,
)
from helpers.sv_config import get_config
from helpers.google import upload


class ModMute(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.spamcounter = {}
        self.nocfgmsg = "Muting isn't enabled in this server."

    def enabled(self, g):
        return all(
            (
                self.bot.pull_role(g, get_config(g.id, "mute", "muterole")),
                self.bot.pull_category(g, get_config(g.id, "mute", "mutecategory")),
                get_config(g.id, "mute", "mutechannels"),
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
                member.guild, get_config(member.guild.id, "mute", "muterole")
            )
        ]
        if roleban:
            if (
                self.bot.pull_role(
                    member.guild, get_config(member.guild.id, "mute", "muterole")
                )
                in member.roles
            ):
                if hard:
                    return len([r for r in member.roles if not (r.managed)]) == 2
                return True

    def get_session(self, member):
        mutes = get_mutefile(member.guild.id, "mutes")
        if not mutes:
            return None
        session = None
        if "LEFTGUILD" in mutes and str(member.id) in mutes["LEFTGUILD"]:
            session = False
        for channel in mutes:
            if channel == "LEFTGUILD":
                continue
            if str(member.id) in mutes[channel]["muted"]:
                session = channel
                break
        return session

    async def new_session(self, guild):
        staff_roles = [
            self.bot.pull_role(guild, get_config(guild.id, "staff", "modrole")),
            self.bot.pull_role(guild, get_config(guild.id, "staff", "adminrole")),
        ]
        bot_role = self.bot.pull_role(guild, get_config(guild.id, "staff", "botrole"))
        mutes = get_mutefile(guild.id, "mutes")

        for c in get_config(guild.id, "mute", "mutechannels"):
            if c not in [g.name for g in guild.channels]:
                if c not in mutes:
                    mutes[c] = {"muted": {}, "unmuted": [], "left": []}
                    set_mutefile(guild.id, "mutes", json.dumps(mutes))

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
                mute_channel = await guild.create_text_channel(
                    c,
                    reason="Fluff Mute",
                    category=self.bot.pull_category(
                        guild, get_config(guild.id, "mute", "mutecategory")
                    ),
                    overwrites=overwrites,
                    topic=get_config(guild.id, "mute", "mutetopic"),
                )

                return mute_channel

    async def perform_mute(self, user, staff, mute_channel):
        mute_role = self.bot.pull_role(
            user.guild, get_config(user.guild.id, "mute", "muterole")
        )
        roles = []
        for rx in user.roles:
            if rx != user.guild.default_role and rx != mute_role:
                roles.append(rx)

        mutes = get_mutefile(user.guild.id, "mutes")
        mutes[mute_channel.name]["muted"][str(user.id)] = [role.id for role in roles]
        set_mutefile(user.guild.id, "mutes", json.dumps(mutes))

        await user.add_roles(mute_role, reason="User muted.")
        fail_roles = []
        if roles:
            for rr in roles:
                if not rr.is_assignable():
                    fail_roles.append(rr)
                    roles.remove(rr)
            await user.remove_roles(
                *roles,
                reason=f"User muted by {staff} ({staff.id})",
                atomic=False,
            )

        return fail_roles, roles

    @commands.bot_has_permissions(embed_links=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["tossed", "session"])
    async def sessions(self, ctx):
        """This shows the open mute sessions.

        Use this in a mute channel to show who's in it.

        No arguments."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        embed = stock_embed(self.bot)
        embed.title = "👁‍🗨 Muted Sessions... (Fluff)"
        embed.color = ctx.author.color
        mutes = get_mutefile(ctx.guild.id, "mutes")

        if ctx.channel.name in get_config(ctx.guild.id, "mute", "mutechannels"):
            channels = [ctx.channel.name]
        else:
            channels = get_config(ctx.guild.id, "mute", "mutechannels")

        for c in channels:
            if c in [g.name for g in ctx.guild.channels]:
                if c not in mutes or not mutes[c]["muted"]:
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
                                for u in mutes[c]["muted"].keys()
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

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.bot_has_permissions(
        manage_roles=True, manage_channels=True, add_reactions=True
    )
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["roleban", "toss"])
    async def mute(self, ctx, users: commands.Greedy[discord.Member]):
        """This mutes a user.

        Please refer to the tossing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/).

        - `users`
        The users to mute."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)

        staff_roles = [
            self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "staff", "modrole")),
            self.bot.pull_role(
                ctx.guild, get_config(ctx.guild.id, "staff", "adminrole")
            ),
        ]
        mute_role = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "mute", "muterole")
        )
        if not any(staff_roles) or not mute_role:
            return await ctx.reply(
                content="PLACEHOLDER no staff or muted role configured",
                mention_author=False,
            )
        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "mute", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )

        errors = ""
        for us in users:
            if us.id == ctx.author.id:
                errors += f"\n- {self.username_system(us)}\n  You cannot mute yourself."
            elif us.id == self.bot.application_id:
                errors += f"\n- {self.username_system(us)}\n  You cannot mute the bot."
            elif self.get_session(us) and mute_role in us.roles:
                errors += (
                    f"\n- {self.username_system(us)}\n  This user is already muted."
                )
            else:
                continue
            users.remove(us)
        if not users:
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in mute command from {ctx.author.mention}...\n- Nobody was muted.\n```diff"
                + errors
                + "\n```\n"
            )

        if ctx.channel.name in get_config(ctx.guild.id, "mute", "mutechannels"):
            addition = True
            mute_channel = ctx.channel
        elif all(
            [
                c in [g.name for g in ctx.guild.channels]
                for c in get_config(ctx.guild.id, "mute", "mutechannels")
            ]
        ):
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in mute command from {ctx.author.mention}...\n- No muted channels available.\n```diff"
                + errors
                + "\n```\n"
            )
        else:
            addition = False
            mute_channel = await self.new_session(ctx.guild)

        for us in users:
            try:
                failed_roles, previous_roles = await self.perform_mute(
                    us, ctx.author, mute_channel
                )
                await mute_channel.set_permissions(us, read_messages=True)
            except commands.MissingPermissions:
                errors += f"\n- {self.username_system(us)}\n  Missing permissions to mute this user."
                continue

            mute_userlog(
                ctx.guild.id,
                us.id,
                ctx.author,
                ctx.message.jump_url,
                mute_channel.id,
            )

            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed, us, True)
                embed.color = ctx.author.color
                embed.title = "🚷 mute"
                embed.description = f"{us.mention} was muted by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]\n> This mute takes place in {mute_channel.mention}..."
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
                    name="Previous Roles",
                    value=prevlist,
                    inline=False,
                )
                if failed_roles:
                    faillist = []
                    for role in failed_roles:
                        faillist.append("<@&" + str(role.id) + ">")
                    faillist = ",".join(reversed(faillist))
                    embed.add_field(
                        name="Failed Roles",
                        value=faillist,
                        inline=False,
                    )
                await notify_channel.send(embed=embed)

        await ctx.message.add_reaction("🚷")

        if errors and notify_channel:
            return await notify_channel.send(
                f"Error in mute command from {ctx.author.mention}...\n- Some users could not be muted.\n```diff"
                + errors
                + "\n```\n"
            )

        if not addition:
            mute_pings = ", ".join([us.mention for us in users])
            await mute_channel.send(
                f"{mute_pings}\nYou were muted by {self.bot.pacify_name(ctx.author.display_name)}.\n"
                '> *For reference, this means a Staff member wishes to speak with you one on one! This does not necessarily mean you are in trouble. This session will be archived for Staff only once completed.*'
            )

            def check(m):
                return m.author in users and m.channel == mute_channel

            try:
                await self.bot.wait_for("message", timeout=300, check=check)
            except asyncio.TimeoutError:
                pokemsg = await mute_channel.send(ctx.author.mention)
                await pokemsg.edit(content="⏰", delete_after=5)
            except discord.NotFound:
                return
            else:
                pokemsg = await mute_channel.send(ctx.author.mention)
                await pokemsg.edit(content="🫳⏰", delete_after=5)

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["unroleban", "untoss"])
    async def unmute(self, ctx, users: commands.Greedy[discord.Member] = None):
        """This unmutes a user.

        Please refer to the muteing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/).

        - `users`
        The users to unmute. Optional."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        if ctx.channel.name not in get_config(ctx.guild.id, "mute", "mutechannels"):
            return await ctx.reply(
                content="This command must be run inside of a muted channel.",
                mention_author=False,
            )

        mutes = get_mutefile(ctx.guild.id, "mutes")
        if not users:
            users = [
                ctx.guild.get_member(int(u))
                for u in mutes[ctx.channel.name]["muted"].keys()
            ]

        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "mute", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )
        mute_role = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "mute", "muterole")
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
                str(us.id) not in mutes[ctx.channel.name]["muted"]
                and mute_role not in us.roles
            ):
                output += "\n" + f"{self.username_system(us)} is not muted."
            else:
                continue
            users.remove(us)
        if not users:
            return await ctx.reply(
                output
                + "\n\n"
                + "There's nobody to unmute!",
                mention_author=False,
            )

        for us in users:
            self.busy = True
            roles = mutes[ctx.channel.name]["muted"][str(us.id)]
            if us.id not in mutes[ctx.channel.name]["unmuted"]:
                mutes[ctx.channel.name]["unmuted"].append(us.id)
            del mutes[ctx.channel.name]["muted"][str(us.id)]

            if roles:
                roles = [ctx.guild.get_role(r) for r in roles]
                for r in roles:
                    if not r or not r.is_assignable():
                        roles.remove(r)
                await us.add_roles(
                    *roles,
                    reason=f"Unmuted by {ctx.author} ({ctx.author.id})",
                    atomic=False,
                )
            await us.remove_roles(
                mute_role,
                reason=f"Unmuted by {ctx.author} ({ctx.author.id})",
            )

            await ctx.channel.set_permissions(us, overwrite=None)

            output += "\n" + f"{self.username_system(us)} has been unmuted."
            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed, us)
                embed.color = ctx.author.color
                embed.title = "Unmute (Fluff)"
                embed.description = f"{us.mention} was unmuted by {ctx.author.mention} [`#{ctx.channel.name}`]"
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
                    name="Restored Roles",
                    value=prevlist,
                    inline=False,
                )
                await notify_channel.send(embed=embed)

        set_mutefile(ctx.guild.id, "mutes", json.dumps(mutes))
        self.busy = False

        if invalid:
            output += (
                "\n\n"
                + "I was unable to unmute these users: "
                + ", ".join([str(iv) for iv in invalid])
            )

        if not mutes[ctx.channel.name]:
            output += "\n\n" + "There is nobody left in this session."

        await ctx.reply(content=output, mention_author=False)

    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def close(self, ctx, archive=True):
        """This closes a mute session.

        Please refer to the tossing section of the [documentation](https://3gou.0ccu.lt/as-a-moderator/the-tossing-system/)."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        if ctx.channel.name not in get_config(ctx.guild.id, "mute", "mutechannels"):
            return await ctx.reply(
                content="This command must be run inside of a muted channel.",
                mention_author=False,
            )

        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "mute", "notificationchannel")
        )
        if not notify_channel:
            notify_channel = self.bot.pull_channel(
                ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel")
            )
        logging_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "logging", "modlog")
        )
        mutes = get_mutefile(ctx.guild.id, "mutes")

        if mutes[ctx.channel.name]["muted"]:
            return await ctx.reply(
                content="You must unmute everyone first!", mention_author=True
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
                mutes[ctx.channel.name]["unmuted"] + mutes[ctx.channel.name]["left"]
            ):
                if self.bot.get_user(uid):
                    users.append(self.bot.get_user(uid))
                else:
                    user = await self.bot.fetch_user(uid)
                    users.append(user)
            user = ""

            if users:
                firstuser = f'{users[0].name} {users[0].id}'
            else:
                firstuser = f'unspecified (logged by {ctx.author.name})'

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
                f"data/servers/{ctx.guild.id}/mute/archives/sessions/{ctx.channel.id}"
            ):
                os.makedirs(
                    f"data/servers/{ctx.guild.id}/mute/archives/sessions/{ctx.channel.id}"
                )
            with open(
                f"data/servers/{ctx.guild.id}/mute/archives/sessions/{ctx.channel.id}/{filename}.txt",
                "w", encoding='UTF-8'
            ) as filetxt:
                filetxt.write(dotraw)
            if dotzip:
                with open(
                    f"data/servers/{ctx.guild.id}/mute/archives/sessions/{ctx.channel.id}/{filename} (files).zip",
                    "wb",
                ) as filezip:
                    filezip.write(dotzip.getbuffer())

            # embed = stock_embed(self.bot)
            # embed.title = "Mute Session Closed (Fluff)"
            # embed.description = f"`#{ctx.channel.name}`'s session was closed by {ctx.author.mention} ({ctx.author.id})."
            # embed.color = ctx.author.color
            # embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

            embed.add_field(
                name="🗒️ Text",
                value=f"{filename}.txt\n"
                + "`"
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
            
            await upload(ctx, filename, f"data/servers/{ctx.guild.id}/mute/archives/sessions/{ctx.channel.id}/", dotzip)

        del mutes[ctx.channel.name]
        set_mutefile(ctx.guild.id, "mutes", json.dumps(mutes))

        channel = notify_channel if notify_channel else logging_channel
        if channel:
            await channel.send(embed=embed)
        else:
            await ctx.message.add_reaction("📦")
            await asyncio.sleep(5)

        await ctx.channel.delete(reason="Fluff Mute")
        return

    @Cog.listener()
    async def on_member_update(self, before, after):
        await self.bot.wait_until_ready()
        if not self.enabled(after.guild):
            return
        while self.busy:
            await asyncio.sleep(1)
        if self.is_rolebanned(before) and not self.is_rolebanned(after):
            session = self.get_session(after)
            if not session:
                return

            mutes = get_mutefile(after.guild.id, "mutes")
            mutes[session]["unmuted"].append(after.id)
            del mutes[session]["muted"][str(after.id)]
            set_mutefile(after.guild.id, "mutes", json.dumps(mutes))

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.bot.wait_until_ready()
        if self.enabled(channel.guild) and channel.name in get_config(
            channel.guild.id, "mute", "mutechannels"
        ):
            mutes = get_mutefile(channel.guild.id, "mutes")
            if channel.name not in mutes:
                return
            del mutes[channel.name]
            set_mutefile(channel.guild.id, "mutes", json.dumps(mutes))


async def setup(bot):
    await bot.add_cog(ModMute(bot))
