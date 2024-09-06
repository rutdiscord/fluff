import discord
import json
import datetime
import logging

from discord.ext import commands
from discord.ext.commands import Cog

from helpers.checks import ismod, ismanager
from helpers.sv_config import get_config
from helpers.datafiles import get_tossfile, set_tossfile

"""
    JSON format for rulepushes:
    {
        "pushed": {
            "channel_name": {
                "user_id": [
                    "roles": [role_id, role_id, ...], 
                    timestamp: 0
                ]
            },
        },

        "idle_kicked": {
            "user_id": [
            "roles": [role_id, role_id, ...], 
            ],
        },

        },

        "left": [],
    }
"""


class RulePushV2(Cog):

    def __init__(self, bot):
        self.bot = bot

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

    async def session_manager(
        self, action: str, guild: discord.Guild, user: discord.Member
    ):
        assert action in ["get", "create"]  # if action not supported throw assert

        if not self.enabled(guild):
            return

        rulepush_sessions = get_tossfile(guild.id, "rulepush")  # Pull tosses

        match action:
            case "get":
                if not rulepush_sessions:  # Prevention of Chaos
                    return None

                session = None

                if (
                    "left" in rulepush_sessions
                    and str(user.id) in rulepush_sessions["left"]
                ):
                    session = False  # User left

                for channel in rulepush_sessions["pushed"]:
                    if str(user.id) in rulepush_sessions["pushed"][channel]:
                        session = rulepush_sessions[channel][
                            str(user.id)
                        ]  # Found session
                        break

                return session
            case "create":

                rulepush_config_role = self.bot.pull_role(
                    guild.id, get_config(guild.id, "rulepush", "rulepushrole")
                )
                rulepush_config_category = self.bot.pull_category(
                    guild.id, get_config(guild.id, "rulepush", "rulepushcategory")
                )

                staff_roles = [
                    self.bot.pull_role(guild, get_config(guild.id, "staff", "modrole")),
                    self.bot.pull_role(
                        guild, get_config(guild.id, "staff", "adminrole")
                    ),
                ]

                bot_role = self.bot.pull_role(
                    guild, get_config(guild.id, "staff", "botrole")
                )

                for channel in get_config(guild.id, "rulepush", "rulepushchannels"):
                    if channel not in [iterc.name for iterc in guild.channels]:
                        if channel not in rulepush_sessions:
                            rulepush_sessions["pushed"][channel] = {
                                f"{user.id}": {
                                    "roles": [role.id for role in user.roles],
                                    "timestamp": int(
                                        datetime.datetime.now().timestamp()
                                    ),
                                }
                            }
                            set_tossfile("rulepush", json.dumps(rulepush_sessions))
                            overwrites = {
                                guild.default_role: discord.PermissionOverwrite(
                                    read_messages=False
                                ),
                                guild.me: discord.PermissionOverwrite(
                                    read_messages=True
                                ),
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
                            rulepush_channel = await guild.create_text_channel(
                                channel,
                                reason="Fluff Rulepush",
                                category=self.bot.pull_category(
                                    guild,
                                    get_config(
                                        guild.id, "rulepush", "rulepushcategory"
                                    ),
                                ),
                                overwrites=overwrites,
                                topic=get_config(guild.id, "rulepush", "rulepushtopic"),
                            )

                            return rulepush_channel

    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.check(ismod)
    @commands.command()
    async def rulepush(self, ctx, user: discord.Member):
        pass

    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.check(ismanager)
    @commands.command()
    async def session_debug(self, ctx, action: str, user: discord.Member):
        match action:
            case "get":
                await ctx.send(await self.session_manager("get", ctx.guild, user))
            case "create":
                await ctx.send(await self.session_manager("create", ctx.guild, user))

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.bot.wait_until_ready()
        if message.author.bot or message.is_system() or not message.guild:
            return

        rulepush_channels = get_config(message.guild.id, "rulepush", "rulepushchannels")

        if message.author.bot:
            return

        if str(message.channel.id) not in rulepush_channels:
            return


async def setup(bot):
    await bot.add_cog(RulePushV2(bot))
