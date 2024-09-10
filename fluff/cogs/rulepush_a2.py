import discord
import json
import datetime
import typing

from discord.ext import commands
from discord.ext.commands import Cog

from helpers.checks import ismod, ismanager
from helpers.sv_config import get_config
from helpers.datafiles import get_tossfile, set_tossfile


class RulePushV2(Cog):

    def __init__(self, bot):
        self.bot = bot
        self.eph_timers = {}

    def enabled(self, g):
        return all(
            (
                self.bot.pull_role(g, get_config(g.id, "rulepush", "rulepushrole")),
                self.bot.pull_category(
                    g, get_config(g.id, "rulepush", "rulepushcategory")
                ),
                get_config(g.id, "rulepush", "rulepushchannels"),
            )
        )

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

    async def start_managed_session(self, user, staff, push_channel):
        push_role = self.bot.pull_role(
            user.guild, get_config(user.guild.id, "rulepush", "rulepushrole")
        )

        if push_role in user.roles:
            return False

        roles = []
        for rx in user.roles:
            if rx != user.guild.default_role and rx != push_role:
                roles.append(rx)

        pushes = get_tossfile(user.guild.id, "rulepushes")
        pushes[push_channel.name]["pushed"][str(user.id)] = [role.id for role in roles]
        set_tossfile(user.guild.id, "rulepushes", json.dumps(pushes))

        await user.add_roles(push_role, reason="Fluff Rulepush")
        fail_roles = []
        if roles:
            for rr in roles:
                if not rr.is_assignable():
                    fail_roles.append(rr)
                    roles.remove(rr)
            await user.remove_roles(
                *roles,
                reason=f"User rulepushed by {staff} ({staff.id})",
                atomic=False,
            )

        return fail_roles, roles


async def setup(bot):
    await bot.add_cog(RulePushV2(bot))
