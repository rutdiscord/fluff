import discord
import json
import datetime
import typing

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

        "left": []

        },
    }
"""


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

    async def session_manager(
        self,
        action: str,
        guild: discord.Guild,
        user: discord.Member = None,
        channel: discord.TextChannel = None,
    ):  # this is mostly to provide a predictable path to frequently used functions

        if action not in ["get", "create", "clean_destroy", "all_sessions"]:
            raise NotImplementedError(
                "Action not implemented"
            )  # if action not supported, bail

        if not self.enabled(guild):
            return

        rulepush_config_category = self.bot.pull_category(
            guild, get_config(guild.id, "rulepush", "rulepushcategory")
        )

        rulepush_config_topic = get_config(guild.id, "rulepush", "rulepushtopic")

        rulepush_config_role = self.bot.pull_role(
            guild, get_config(guild.id, "rulepush", "rulepushrole")
        )

        rulepush_sessions = get_tossfile(guild.id, "rulepush")  # Pull tosses
        if rulepush_sessions == {}:
            rulepush_sessions = {
                "pushed": {},
                "idle_kicked": {},
                "left": [],
            }  # If no sessions, create empty dict

        match action:
            case "all_sessions":
                if not rulepush_sessions:
                    return
                else:
                    return rulepush_sessions
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
                        session = {
                            "user_id": str(user.id),
                            "channel": channel,
                            "session_data": rulepush_sessions["pushed"][channel][
                                str(user.id)
                            ],
                        }  # Found session
                        break

                return session
            case "create":

                user_current_session = await self.session_manager("get", guild, user)

                if user_current_session:
                    return user_current_session

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
                        try:
                            if str(user.id) in rulepush_sessions["pushed"][channel]:
                                return False
                        except KeyError:
                            pass

                        if channel not in rulepush_sessions:
                            rulepush_sessions["pushed"][channel] = {
                                f"{user.id}": {
                                    "roles": [role.id for role in user.roles],
                                    "timestamp": int(
                                        datetime.datetime.now().timestamp()
                                    ),
                                }
                            }
                            set_tossfile(
                                guild.id, "rulepush", json.dumps(rulepush_sessions)
                            )
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
                                category=rulepush_config_category,
                                overwrites=overwrites,
                                topic=rulepush_config_topic,
                            )

                            await rulepush_channel.set_permissions(
                                user, read_messages=True
                            )

                            await user.add_roles(rulepush_config_role)

                            for role in user.roles:
                                if role != rulepush_config_role:
                                    if role.is_assignable():
                                        await user.remove_roles(
                                            role,
                                            reason="Generating rulepush session (Fluff)",
                                            atomic=False,
                                        )
                                    else:
                                        return

                            return rulepush_channel

            case "clean_destroy":
                rulepush_config_category = self.bot.pull_category(
                    guild, get_config(guild.id, "rulepush", "rulepushcategory")
                )

                session = await self.session_manager("get", guild, user)

                if session and session["channel"] == channel.name:
                    await user.remove_roles(
                        rulepush_config_role,
                        reason="Dismantling rulepush session (Fluff)",
                    )

                    if session["session_data"]["roles"]:
                        for role in session["session_data"]["roles"]:
                            if guild.get_role(role) is not guild.default_role:
                                await user.add_roles(
                                    guild.get_role(role), atomic=False
                                )  # two api calls for the price of one

                    await channel.delete()
                    del rulepush_sessions["pushed"][session["channel"]]
                    set_tossfile(guild.id, "rulepush", json.dumps(rulepush_sessions))
                    return True
                else:
                    return False

    async def setup_session(session: discord.channel.TextChannel, user: discord.Member):
        pass

    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.group(invoke_without_command=True)
    async def session_debug(self, ctx: commands.Context):
        sessions = await self.session_manager("all_sessions", ctx.guild)
        await ctx.reply(f"```\n{sessions}```", mention_author=False)

    @session_debug.command()
    async def get(self, ctx: commands.Context, user: discord.Member):
        session = await self.session_manager("get", ctx.guild, user)
        await ctx.reply(f"```\n{session}```", mention_author=False)

    @session_debug.command()
    async def create(self, ctx: commands.Context, user: discord.Member):
        session = await self.session_manager("create", ctx.guild, user)
        await ctx.reply(f"```\n{session}```", mention_author=False)

    @session_debug.command()
    async def destroy(
        self,
        ctx: commands.Context,
        us: discord.Member,
        chan: discord.TextChannel,
    ):
        session = await self.session_manager("clean_destroy", ctx.guild, us, chan)
        await ctx.reply(f"```\n{session}```", mention_author=False)

    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.check(ismod)
    @commands.command()
    async def rulepush(self, ctx, user: discord.Member):
        if not self.enabled(ctx.guild):
            return

        potential_session = await self.session_manager("get", ctx.guild, user)

        if (potential_session) is not None:
            return await ctx.reply(
                f"User already has a session... *thump*", mention_author=False
            )

        new_session = await self.session_manager("create", ctx.guild, user)

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
