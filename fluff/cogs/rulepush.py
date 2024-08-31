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
        self.load_sessions()

    def load_sessions(self):
        if os.path.exists("rule_sessions.json"):
            with open("rule_sessions.json", "r") as f:
                self.sessions = json.load(f)
        else:
            self.sessions = {"current": {}, "left": [], "kicks": {}}

    def save_sessions(self):
        with open("rule_sessions.json", "w") as f:
            json.dump(self.sessions, f, indent=4)

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
                    f"\n- {us.display_name}\n  This user is already rulepushed."
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
            rulepush_channel = self.bot.pull_channel(
                ctx.guild.id, get_config(ctx.guild.id, "rulepush", "rulepushchannels")
                )

        for us in users:
            try:
                failed_roles, previous_roles = await self.start_rule_push(
                    us, ctx.author, rulepush_channel
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

    async def start_rule_push(self, member):
        guild = member.guild
        role = discord.utils.get(guild.roles, name="RulePushRole")
        category = discord.utils.get(guild.categories, name="RulePushCategory")
        
        if not role or not category:
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(f"rule-push-{member.name}", overwrites=overwrites, category=category)
        intro_message = get_config(guild.id, "rulepush", "intro_message")
        await channel.send(intro_message)

        self.user_timers[member.id] = {
            'channel': channel,
            'timer': self.bot.loop.call_later(43200, self.kick_user, member),
            'kick': True
        }

        self.sessions["current"][member.id] = {"channel": channel.id, "start_time": datetime.utcnow().isoformat()}
        self.save_sessions()

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
        return self.sessions["current"].get(str(member.id))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        member = message.author
        if member.id in self.user_timers:
            channel = self.user_timers[member.id]['channel']
            if message.channel == channel:
                keywords = {"pineapple", "pancake", "coconut"}
                if not any(keyword in message.content.lower() for keyword in keywords):
                    await message.delete()
                else:
                    self.user_timers[member.id]['kick'] = False
                    await channel.send("Congratulations! Please be mindful of the rules.\nYou may be pushed to read the rules again at a later date if you participate in further suspicious activity.\n**You will be free to participate in the server in 60 seconds...**")
                    await asyncio.sleep(60)
                    await channel.delete()
                    del self.user_timers[member.id]
                    del self.sessions["current"][member.id]
                    self.save_sessions()

                    ctx = await self.bot.get_context(message)
                    us = member

                    notify_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "rulepush", "notificationchannel"))
                    if not notify_channel:
                        notify_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "staff", "staffchannel"))
                    modlog_channel = self.bot.pull_channel(ctx.guild, get_config(ctx.guild.id, "logging", "modlog"))

                    if notify_channel:
                        embed = stock_embed(self.bot)
                        embed.set_author(name=us.display_name, icon_url=us.avatar_url)
                        embed.color = discord.Color.green()
                        embed.title = "🎉 RulePush Completed"
                        embed.description = f"{us.mention} has successfully completed the rulepush puzzle and has been released."
                        await notify_channel.send(embed=embed)

                    if modlog_channel and modlog_channel != notify_channel:
                        embed = stock_embed(self.bot)
                        embed.set_author(name=us.display_name, icon_url=us.avatar_url)
                        embed.color = discord.Color.green()
                        embed.title = "🎉 RulePush Completed"
                        embed.description = f"{us.mention} has successfully completed the rulepush puzzle and has been released."
                        await modlog_channel.send(embed=embed)

    async def kick(self, ctx, member: discord.Member, *, reason= None):
        await member.kick(reason="Could not read the rules in time.")
        self.sessions["kicks"][member.id] = datetime.utcnow().isoformat()
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
                    if datetime.utcnow() - kick_time < timedelta(hours=1):
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
                    embed.set_author(name=member.display_name, icon_url=member.avatar_url)
                    embed.color = discord.Color.red()
                    embed.title = "🚫 RulePush Violation"
                    embed.description = f"{member.mention} has been banned for attempting to leave while rulepushed."
                    await notify_channel.send(embed=embed)

                if modlog_channel and modlog_channel != notify_channel:
                    embed = stock_embed(self.bot)
                    embed.set_author(name=member.display_name, icon_url=member.avatar_url)
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
            self.sessions["current"][member.id] = {"start_time": datetime.utcnow().isoformat()}
            self.save_sessions()
            await self.start_rule_push(member)

            notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "rulepush", "notificationchannel"))
            if not notify_channel:
                notify_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "staff", "staffchannel"))
            modlog_channel = self.bot.pull_channel(member.guild, get_config(member.guild.id, "logging", "modlog"))

            if notify_channel:
                embed = stock_embed(self.bot)
                embed.set_author(name=member.display_name, icon_url=member.avatar_url)
                embed.color = discord.Color.orange()
                embed.title = "⚠️ RulePush Rejoin"
                embed.description = f"{member.mention} has rejoined the server after being kicked while rulepushed."
                await notify_channel.send(embed=embed)

            if modlog_channel and modlog_channel != notify_channel:
                embed = stock_embed(self.bot)
                embed.set_author(name=member.display_name, icon_url=member.avatar_url)
                embed.color = discord.Color.orange()
                embed.title = "⚠️ RulePush Rejoin"
                embed.description = f"{member.mention} has rejoined the server after being kicked while rulepushed."
                await modlog_channel.send(embed=embed)

    async def start_rule_push(self, member):
        guild = member.guild
        rulepush_role = self.bot.pull_role(guild, get_config(guild.id, "rulepush", "rulepushrole"))
        if not rulepush_role:
            return

        await member.add_roles(rulepush_role)
        self.sessions["current"][member.id] = {"start_time": datetime.utcnow().isoformat()}
        self.save_sessions()

async def setup(bot):
    await bot.add_cog(RulePush(bot))