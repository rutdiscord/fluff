import discord
import json
import os
import asyncio
import random
import zipfile
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord.ext.commands import Cog
from io import BytesIO
from helpers.checks import ismod
from helpers.datafiles import add_userlog, toss_userlog, get_tossfile, set_tossfile
from helpers.placeholders import random_msg
from helpers.archive import log_channel, get_members
from helpers.embeds import (
    stock_embed,
    mod_embed,
    author_embed,
    createdat_embed,
    joinedat_embed,
)
from helpers.sv_config import get_config
from helpers.google import upload

class RulePush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_timers = {}

    async def new_session(self, guild):
        staff_roles = [
            self.bot.pull_role(guild, get_config(guild.id, "staff", "modrole")),
            self.bot.pull_role(guild, get_config(guild.id, "staff", "adminrole")),
        ]
        bot_role = self.bot.pull_role(guild, get_config(guild.id, "staff", "botrole"))
        tosses = get_tossfile(guild.id, "rulepushes")

        for c in get_config(guild.id, "rulepush", "rulepushchannels"):
            if c not in [g.name for g in guild.channels]:
                if c not in tosses:
                    tosses[c] = {"pushed": {}, "unpushed": [], "left": []}
                    set_tossfile(guild.id, "rulepushes", json.dumps(tosses))

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
                    reason="Fluff Rule Push",
                    category=self.bot.pull_category(
                        guild, get_config(guild.id, "rulepush", "rulepushcategory")
                    ),
                    overwrites=overwrites,
                    topic=get_config(guild.id, "rulepush", "rulepushtopic"),
                )

                return toss_channel

    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def rulepush(self, ctx, users: commands.Greedy[discord.Member]):
        staff_roles = [
            self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "staff", "modrole")),
            self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "staff", "adminrole")),
        ]
        rulepush_role = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "rulepush", "rulepushrole")
            )
        if not any(staff_roles) or not rulepush_role:
            return await ctx.reply(
                content="PLACEHOLDER No staff or rulepush role configured",
                mention_author=False,
            )
        notify_channel = self.bot.pull_channel(
            ctx.guild, get_config(ctx.guild.id, "rulepush", "notificationchannel")
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
                errors += f"\n- {us.display_name}\n  You cannot rulepush yourself."
            elif us.id == self.bot.user.id:
                errors += f"\n- {us.display_name}\n  You cannot rulepush the bot."
            elif self.get_session(us) and rulepush_role in us.roles:
                errors += (
                    f"\n- {us.display_name}\n  This user has already rulepushed."
                )
            else:
                continue
            users.remove(us)
        if not users:
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention}...\n- Nobody was rulepushed.\n```diff"
                + errors
                + "\n```\n"
            )

        if ctx.channel.name in get_config(ctx.guild.id, "rulepush", "rulepushchannels"):
            addition = True
            rulepush_channel = ctx.channel
        elif all(
            [
                c in [g.name for g in ctx.guild.channels] 
                for c in get_config(ctx.guild.id, "rulepush", "rulepushchannels")
            ]
        ):
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention}...\n- No rulepush channels available.\n```diff"
                + errors
                + "\n```\n"
            )
        else:
            addition = False
            rulepush_channel = self.new_session(ctx.guild)
        for us in users:
            try:
                failed_roles, previous_roles = await self.start_rule_push(
                    us, rulepush_channel
                )
                await rulepush_channel.set_permissions(us, read_messages=True)
            except commands.MissingPermissions:
                errors += f"\n- {us.display_name}\n  Missing permissions to rulepush this user."
                continue

            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed, us, True)
                embed.color = ctx.author.color
                embed.title = "📖 RulePush"
                embed.description = f"{us.mention} was rulepushed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]\n> This rulepush takes place in {rulepush_channel.mention}..."
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
                embed.title = "📖 RulePush"
                embed.description = f"{us.mention} was rulepushed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]"
                mod_embed(embed, us, ctx.author)
                await modlog_channel.send(embed=embed)

        await ctx.message.add_reaction("📖")

        if errors and notify_channel:
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention}...\n- Some users could not be rulepushed.\n```diff"
                + errors
                + "\n```\n"
            )

        if not addition:
            rulepush_pings = ", ".join([us.mention for us in users])
            await rulepush_channel.send(
                f"{rulepush_pings}\nYou have been pushed to read the rules due to suspicious activity indicating you have not read them\nYou must solve a puzzle before accessing the server again.\n{get_config(ctx.guild.id, 'rulepush', 'intro_message')}"
            )

    async def start_rule_push(self, member, rolepush_channel):
        guild = member.guild
        role = self.bot.pull_role(guild,
                                  get_config(guild.id, "rulepush", "rulepushrole")
                                  )
        category = self.bot.pull_category(
                        guild, get_config(guild.id, "rulepush", "rulepushcategory")
                    )
        
        if not role or not category:
            return
        elif role in member.roles:
            return False


        channel = await self.new_session(guild)
        intro_message = get_config(guild.id, "rulepush", "intro_message")
        await channel.send(intro_message)
        
        roles = []
        for rx in member.roles:
            if rx != member.guild.default_role and rx != role:
                roles.append(rx)
        
        pushes = get_tossfile(member.guild.id, "rulepushes")
        pushes[rolepush_channel.name]["pushed"][str(member.id)] = [role.id for role in roles]
        set_tossfile(member.guild.id, "rulepushes", json.dumps(pushes))

        await member.add_roles(role, reason="User pushed to read rules")
        self.user_timers[member.id] = {
            'channel': channel,
            'timer': self.bot.loop.call_later(43200, self.kick_user, member),
            'kick': True
        }

    async def kick_user(self, member):
        if self.user_timers[member.id]['kick']:
            await member.kick(reason="Failed to solve rule puzzle in time.")
            await self.user_timers[member.id]['channel'].delete()
            self.sessions["left"].append(member.id)
            del self.sessions["current"][member.id]
            self.save_sessions()
            del self.user_timers[member.id]

        notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "rulepush", "notificationchannel"))
        if not notify_channel:
            notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "staff", "staffchannel"))
        modlog_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "logging", "modlog"))

        if notify_channel:
            embed = stock_embed(self.bot)
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
            embed.color = discord.Color.orange()
            embed.title = "⏰ RulePush Timed Out"
            embed.description = f"{member.mention} has been kicked for not completing the rulepush puzzle within 12 hours."
            await notify_channel.send(embed=embed)

        if modlog_channel and modlog_channel != notify_channel:
            embed = stock_embed(self.bot)
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
            embed.color = discord.Color.orange()
            embed.title = "⏰ RulePush Timed Out"
            embed.description = f"{member.mention} has been kicked for not completing the rulepush puzzle within 12 hours."
            await modlog_channel.send(embed=embed)

    def get_session(self, member):
        pushes = get_tossfile(member.guild.id, "rulepushes")
        if not pushes:
            return None
        session = None
        if "LEFTGUILD" in pushes and str(member.id) in pushes["LEFTGUILD"]:
            session = False
        

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        member = message.author
        if member.id in self.user_timers:
            channel = self.user_timers[member.id]['channel']
            if message.channel == channel:
                keywords = {"pineapple", "pancake", "coconut"}

                if 'keywords_sent' not in self.user_timers[member.id]:
                    self.user_timers[member.id]['keywords_sent'] = []
                
                for keyword in keywords:
                    if keyword in message.content.lower():
                        self.user_timers[member.id]['keywords_sent'].append(keyword)

                if self.user_timers[member.id]['keywords_sent'] == keywords:
                    self.user_timers[member.id]['kick'] = False
                    await channel.send("Congratulations! Please be mindful of the rules.\nYou may be pushed to read the rules again at a later date if you participate in further suspicious activity.\n**You will be free to participate in the server in 60 seconds...**")
                    await asyncio.sleep(30)
                    await channel.delete()
                    del self.user_timers[member.id]
                    del self.sessions["current"][member.id]
                    self.save_sessions()
                else:
                    await message.delete()

                    ctx = await self.bot.get_context(message)
                    us = member

                    notify_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "rulepush", "notificationchannel"))
                    if not notify_channel:
                        notify_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel"))
                    modlog_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "logging", "modlog"))

                    if notify_channel:
                        embed = stock_embed(self.bot)
                        embed.set_author(name=us.display_name, icon_url=us.display_avatar.url)
                        embed.color = discord.Color.green()
                        embed.title = "🎉 RulePush Completed"
                        embed.description = f"{us.mention} has successfully completed the rulepush puzzle and has been released."
                        await notify_channel.send(embed=embed)

                    if modlog_channel and modlog_channel != notify_channel:
                        embed = stock_embed(self.bot)
                        embed.set_author(name=us.display_name, icon_url=us.display_avatar.url)
                        embed.color = discord.Color.green()
                        embed.title = "🎉 RulePush Completed"
                        embed.description = f"{us.mention} has successfully completed the rulepush puzzle and has been released."
                        await modlog_channel.send(embed=embed)

    async def kick(self, ctx, member: discord.Member, *, reason= None):
        await member.kick(reason="Could not read the rules in time.")
        self.sessions["kicks"][member.id] = datetime.now(tz=timezone.utc).timestamp()
        self.savesessions()
        await ctx.send(f'Kicked {member.mention}')

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.id in self.user_timers:
            self.user_timers[member.id]['timer'].cancel()
            del self.user_timers[member.id]
            self.sessions["left"].append(member.id)
            self.save_sessions()

            rulepush_role = self.bot.pull_role(member.guild, get_config(member.guild.id, "rulepush", "rulepushrole"))
            if rulepush_role in member.roles:
                kick_time_str = self.sessions["kicks"].get(member.id)
                if kick_time_str:
                    kick_time = datetime.fromisoformat(kick_time_str)
                    if datetime.now(tz=timezone.utc) - kick_time < timedelta(hours=1):
                        return
                    
                await member.guild.ban(member, reason="Attempting to evade the rules by leaving the server.")
                self.sessions["left"].remove(member.id)
                self.save_sessions()

                notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "rulepush", "notificationchannel"))
                if not notify_channel:
                    notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "staff", "staffchannel"))
                modlog_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "logging", "modlog"))

                # Create and send embed messages
                if notify_channel:
                    embed = stock_embed(self.bot)
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                    embed.color = discord.Color.red()
                    embed.title = "🚫 RulePush Violation"
                    embed.description = f"{member.mention} has been banned for attempting to leave while rulepushed."
                    await notify_channel.send(embed=embed)

                if modlog_channel and modlog_channel != notify_channel:
                    embed = stock_embed(self.bot)
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                    embed.color = discord.Color.red()
                    embed.title = "🚫 RulePush Violation"
                    embed.description = f"{member.mention} has been banned for attempting to leave while rulepushed."
                    await modlog_channel.send(embed=embed)

        else:
            return

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if user.id in self.sessions["left"]:
            self.sessions["left"].remove(user.id)
            self.save_sessions()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.id in self.sessions["left"]:
            self.sessions["left"].remove(member.id)
            self.sessions["current"][member.id] = {"start_time": datetime.now(tz=timezone.utc).timestamp()}
            self.save_sessions()
            await self.start_rule_push(self.bot, member)

            notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "rulepush", "notificationchannel"))
            if not notify_channel:
                notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "staff", "staffchannel"))
            modlog_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "logging", "modlog"))

            if notify_channel:
                embed = stock_embed(self.bot)
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                embed.color = discord.Color.orange()
                embed.title = "⚠️ RulePush Rejoin"
                embed.description = f"{member.mention} has rejoined the server after being kicked while rulepushed."
                await notify_channel.send(embed=embed)

            if modlog_channel and modlog_channel != notify_channel:
                embed = stock_embed(self.bot)
                embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
                embed.color = discord.Color.orange()
                embed.title = "⚠️ RulePush Rejoin"
                embed.description = f"{member.mention} has rejoined the server after being kicked while rulepushed."
                await modlog_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RulePush(bot))