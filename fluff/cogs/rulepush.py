import discord
import json
import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord.ext.commands import Cog
from io import BytesIO
from helpers.checks import ismod
from helpers.datafiles import add_userlog, rule_userlog, get_rulefile, set_rulefile
from helpers.placeholders import random_msg
from helpers.embeds import (
    stock_embed,
    mod_embed,
    author_embed,
    createdat_embed,
    joinedat_embed,
)
from helpers.sv_config import get_config
from helpers.google import upload

class RulePush(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False
        self.kick_timers = dict()
        self.nocfgmsg = "Rulepushing isn't enabled for this server."

    def enabled(self, g):
        return all(
            (
                self.bot.pull_role(g, get_config(g.id, "rulepush", "rulepushrole")),
                self.bot.pull_category(g, get_config(g.id, "rulepush", "rulepushcategory")),
                get_config(g.id, "rulepush", "rulepushchannels"),
            )
        )
    
    def principal_period(self, s):
        i = (s + s).find(s, 1, -1)
        return None if i == -1 else s[:1]
    
    def is_rulepushed(self, member, hard=True):
        rulepush = [
            r
            for r in member.guild.roles
            if r
            == self.bot.pull_role(
                member.guild, get_config(member.guild.id, "rulepush", "rulepushrole")
            )
        ]
        if rulepush:
            if (
                self.bot.pull_role(
                    member.guild, get_config(member.guild.id, "rulepush", "rulepushrole")
                )
                in member.roles
            ):
                if hard:
                    return len([r for r in member.roles if not (r.managed)]) == 2
                return True
            
    def get_session(self, member):
        rulepushes = get_rulefile(member.guild.id, "rulepushes")
        if not rulepushes:
            return None
        session = None
        if "LEFTGUILD" in rulepushes and str(member.id) in rulepushes["LEFTGUILD"]:
            session = False
            for channel in rulepushes:
                if channel == "LEFTGUILD":
                    continue
                if str(member.id) in rulepushes[channel]["rulepushed"]:
                    session = channel
                    break
                return session
            
    async def new_session(self, guild):
        staff_roles = [
            self.bot.pull_role(guild, get_config(guild.id, "staff", "modrole"))
            self.bot.pull_role(guild, get_config(guild.id, "staff", "adminrole"))
        ]
        bot_role = self.bot.pull_role(guild, get_config(guild.id, "staff", "botrole"))
        rulepushes = get_rulefile(guild.id, "rulepushes")

        for c in get_config(guild.id, "rulepush", "rulepushchannels"):
            if c not in [g.name for g in guild.channels]:
                if c not in rulepushes:
                    rulepushes[c] = {"rulepushed": {}, "unrulepushed": [], "left": []}
                    set_rulefile(guild.id, "rulepushes", json.dumps(rulepushes))  

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
            rulepushchannel = await guild.create_text_channel(
                c,
                reason="Fluff Rule Push",
                category=self.bot.pull_category(
                    guild, get_config(guild.id, "rulepush", "rulepushcategory")
                )
                overwrites=overwrites,
                topic=get_config(guild.id, "rulepush", "rulepushtopic"),
            )

            return rulepushchannel
        
    async def perform_rulepush(self, user, staff, rulepushchannel):
        rulepushrole = self.bot.pull_role(
            user.guild, get_config(user.guild.id, "rulepush", "rulepushrole"),
        )

        if rulepushrole in user.roles:
            return False
        
        roles = []
        for rx in user.roles:
            if rx != user.guild.default_role and rx != rulepushrole:
                roles.append(rx)

        rulepushes = get_rulefile(user.guild.id, "rulepushes")
        rulepushes[rulepushchannel.name]["rulepushed"][str(user.id)] = [role.id for role in roles]
        set_rulefile(user.guild.id, "rulepushes", json.dumps(rulepushes))

        await user.add_roles(rulepushrole, reason = "User Rule Pushed.")
        fail_roles = []
        if roles:
            for rr in roles:
                if not rr.is_assignable():
                    fail_roles.append(rr)
                    roles.remove(rr)
                await user.remove_roles(
                    *roles,
                    reason=f"User Rule Pushed by {staff} ({staff.id})",
                    atomic=False,
                )
            
            return fail_roles, roles
        
    @commands.bot_has_permissions(embed_links=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["rulepushed", "rulespushed"])
    async def pushed(self, ctx):
        """This shows open rulepush sessions.
        
        Use this in a rule push channel to show who's in it.
        
        No arguments."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        embed = stock_embed(self.bot)
        embed.title = "Rule Push Sessions..."
        embed.color = ctx.author.color
        rulepushes = get_rulefile(ctx.guild.id, "rulepushes")

        if ctx.channel.name in get_config(ctx.guild.id, "rulepush", "rulepushchannels"):
            channels = [ctx.channel.name]
        else:
            channels = get_config(ctx.guild.id, "rulepush", "rulepushchannels")

        for c in channels:
            if c in [g.name for g in ctx.guild.channels]:
                if c not in rulepushes or not rulepushes[c]["rulepushed"]:
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
                                for u in rulepushes[c]["rulepushed"].keys()
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
        await ctx.reply(embed=embed,mention_author=False)

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.bot_has_permissions(
        manage_roles=True, manage_channels=True, add_reactions=True
    )
    
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["pushrule"])
    async def rulepush(self, ctx, users: commands.Greedy[discord.Member]):
        """This pushes a user to read the rules.
        
        - `users` 
        The users to rulepush."""
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        
        staff_roles = [
            self.bot.pull_role(ctx.guild, get_config(ctx.guild.id, "staff", "modrole")),
            self.bot.pull_role(
                ctx.guild, get_config(ctx.guild.id, "staff", "adminrole")
            ),
        ]
        rulepushrole = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "rulepush", "rulepushrole")
        )
        if not any (staff_roles) or not rulepushrole:
            return await ctx.reply(
                content="PLACEHOLDER no staff or rule push role configured.",
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
                errors += f"\n- {self.username_system(us)}\n You cannot push yourself to read the rules!\nYou should know them by now..."
            elif us.id == self.bot.application_id:
                errors += f"\n- {self.username_system(us)}\n You can't make me read the rules!\nI can't even read..."
            elif self.get_session(us) and rulepushrole in us.roles:
                errors += (
                    f"\n- {self.username_system(us)}\n This user is currently reading the rules."
                )
            else:
                continue
            users.remove(us)
        if not users:
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention} ... nobody was pushed to read the rules. \n```diff"
                + errors
                + "\n```\n"
            )
        
        if ctx.channel.name in get_config(ctx.guild.id, "rulepush", "rulepushchannels"):
            addition = True
            rulepushchannel = ctx.channel
        elif all(
            [   
                c in [g.name for g in ctx.guild.channels]
                for c in get_config(ctx.guild.id, "rulepush", "rulepushchannels")
            ]
        ):
            await ctx.message.add_reaction("🚫")
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention}...\n- No channels for rulepushing available.\n```diff"
                + errors
                + "\n```\n"
            )
        else:
            addition = False
            rulepushchannel = await self.new_session (ctx.guild)

        for us in users:
            try:
                failed_roles, previous_roles = await self.perform_rulepush(
                    us, ctx.author, rulepushchannel
                )
                await rulepushchannel.set_permissions(us, read_messages = True)
            except commands.MissingPermissions:
                errors += f"\n- {self.username_system(us)}\n Missing permissions to rulepush this user."
                continue

            rule_userlog(
                ctx.guild.id,
                us.id,
                ctx.author,
                ctx.message.jump_url,
                rulepushchannel.id,
            )

            if notify_channel:
                embed = stock_embed(self.bot)
                author_embed(embed,us, True)
                embed.color = ctx.author.color
                embed.title = "📖 Rule Push"
                embed.description = f"{us.mention} was rulepushed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]\n> This is taking place in {rulepushchannel.mention}..."
                createdat_embed (embed, us)
                joinedat_embed(embed, us)
                prevlist = []
                if len (previous_roles) > 0:
                    for role in previous_roles:
                        prevlist.append("<@&" + str(role.id) + ">")
                    prevlist = ",".join(reversed(prevlist))
                else:
                    prevlist = "None"
                    embed.add_field(
                        name="🎨 Previous Roles"
                        value=prevlist
                        inline=False
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
                embed.title = "📖 Rule Push"
                embed.description = f"{us.mention} was rulepushed by {ctx.author.mention} [`#{ctx.channel.name}`] [[Jump]({ctx.message.jump_url})]\n> This is taking place in {rulepushchannel.mention}..."
                mod_embed(embed, us, ctx.author)
                await modlog_channel.send(embed=embed)
                
        await ctx.message.add_reaction("📖")

        if errors and notify_channel:
            return await notify_channel.send(
                f"Error in rulepush command from {ctx.author.mention}...\n- Some users could not be rulepushed. \n```diff"
                + errors
                + "\n```\n"
            )
        
        if not addition:
            rulepush_pings = ", ".join([us.mention for users])
            await rulepushchannel.send(
                f"{rulepush_pings}\nYou have been pushed to read the rules due to suspicious activity indicating you have not read them.\n{get_config(ctx.guild.id, 'rulepush', 'rulepushmsg')}"
            )

            async def check_user_compliance(self, user, channel):
                keywords = {"pineapple", "pancake", "coconut"}
                found_keywords = set()

                async for message in channel.history(limit=100):
                    for keyword in keywords:
                        if keyword in message.content.lower():
                            found_keywords.add(keyword)

                    if found_keywords == keywords:
                        notify_message = await channel.send(
                            f"{user.mention} You have read the rules! Please be mindful of them. You may be pushed to read the rules again at a later date with further suspicious activity. You will be free to participate in the server in 60 seconds..."
                        )

                        await asyncio.sleep(60)

                        rulepushes = get_rulefile(ctx.guild.id "rulepushes")
                        if not users:
                            users = [
                                ctx.guild.get_member(int(u))
                                for u in rulepushes[ctx.channel.name]["rulepushed"].keys()
                            ]

                        set_rulefile(ctx.guild.id, "rulepushes", json.dumps("rulepushes"))
                        self.busy = False   

                        self.bot.pull_role(g, get_config(g.id, "rulepush", "rulepushrole"))
                        if rulepushrole:
                            await user.remove_roles(rulepushrole, reason = "Rules read.")

                    


                


