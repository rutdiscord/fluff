import discord
from discord.ext import commands
from discord.ext.commands import Cog
import traceback
import asyncio
import shutil
import os
import base64

from helpers import datafiles
from helpers.embeds import stock_embed
from helpers.checks import ismanager
from helpers.placeholders import random_msg


class Admin(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_exception = ()

    @commands.check(ismanager)
    @commands.command(name="exit", aliases=["quit", "kill", "die"])
    async def _exit(self, ctx):
        """This shuts down the bot.

        They need a lunch break sometimes.

        No arguments."""
        await ctx.message.reply(content=random_msg("quit_deaths"), mention_author=False)
        await self.bot.close()

    @commands.bot_has_permissions(embed_links=True)
    @commands.check(ismanager)
    @commands.command(name="errors")
    async def _errors(self, ctx):
        """Shows logged command errors.

        It's paginated.

        No arguments."""
        if not self.bot.errors:
            return await ctx.reply(
                content=random_msg("errors_noerrors"), mention_author=False
            )

        allowed_mentions = discord.AllowedMentions(replied_user=False)
        errlist = list(reversed(self.bot.errors))
        idx = 0
        navigation_reactions = ["⬅️", "➡", "⏺️"]
        embed = stock_embed(self.bot)
        embed.color = discord.Color.green()
        holder = await ctx.reply(embed=embed, mention_author=False)
        for e in navigation_reactions:
            await holder.add_reaction(e)

        def reactioncheck(r, u):
            return u.id == ctx.author.id and str(r.emoji) in navigation_reactions

        while True:
            page = errlist[idx]
            err = page[0]
            errctx = page[1]
            embed.title = f"⚠️ Error {len(self.bot.errors) - idx}"

            if embed.fields:
                embed.clear_fields()

            if errctx:
                embed.description = (
                    f"**Command:** `{errctx.message.content}`\n"
                    f"**User:** {errctx.message.author} ({errctx.message.author.id})\n"
                )
                if errctx.guild:
                    embed.description += (
                        f"**Guild:** {errctx.guild.name}\n**Channel:** {errctx.channel.name}\n**Link:** {errctx.message.jump_url}\n"
                        if errctx.guild
                        else ""
                    )
                embed.set_author(
                    name=errctx.author, icon_url=errctx.author.display_avatar.url
                )
            else:
                embed.set_author(
                    name=self.bot.user, icon_url=self.bot.user.display_avatar.url
                )

            err_tb = "\n".join(traceback.format_exception(*err))
            if len(err_tb) > 1024:
                split_msg = self.bot.slice_message(
                    err_tb, size=1024, prefix="```", suffix="```"
                )

                ctr = 1
                for f in split_msg:
                    embed.add_field(
                        name=f"🧩 Traceback Fragment {ctr}",
                        value=f,
                        inline=False,
                    )
                    ctr += 1
            else:
                embed.add_field(
                    name=f"🔍 Traceback:",
                    value=f"```{err_tb}```",
                    inline=False,
                )

            await holder.edit(embed=embed, allowed_mentions=allowed_mentions)

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=reactioncheck
                )
            except asyncio.TimeoutError:
                embed.color = discord.Color.default()
                try:
                    await holder.clear_reactions()
                except:
                    pass
                return await holder.edit(
                    embed=embed,
                    allowed_mentions=allowed_mentions,
                )
            if str(reaction) == "⬅️":
                if idx != 0:
                    idx -= 1
                try:
                    await holder.remove_reaction("⬅️", ctx.author)
                except:
                    pass
            elif str(reaction) == "➡":
                if idx != len(errlist):
                    idx += 1
                try:
                    await holder.remove_reaction("➡", ctx.author)
                except:
                    pass
            elif str(reaction) == "⏺️":
                if self.loaded_exception:
                    self.loaded_exception = ()
                    await ctx.reply(content="Unloaded.", mention_author=False)
                else:
                    self.loaded_exception = tuple([errctx] + list(page[2]))
                    await ctx.reply(content="Loaded.", mention_author=False)
                try:
                    await holder.clear_reactions()
                except:
                    pass
                finally:
                    embed.color = discord.Color.default()
                    return await holder.edit(
                        embed=embed,
                        allowed_mentions=allowed_mentions,
                    )

    @commands.bot_has_permissions(attach_files=True)
    @commands.check(ismanager)
    @commands.command()
    async def getdata(self, ctx):
        """This returns the bot's data files.

        Better do it out of sight, where it won't
        be a massive security risk.

        No arguments."""
        # make backup of database first.
        await self.bot.db.perform_backup()
        zip_name = "data_export"
        datafiles.make_backup(zip_name)
        try:
            await ctx.author.send(
                content=f"Current bot data...",
                file=discord.File(f"{zip_name}.zip"),
            )
        except:
            await ctx.reply(content=random_msg("err_dmfail"), mention_author=False)
        os.remove(f"{zip_name}.zip")

    @commands.bot_has_permissions(attach_files=True)
    @commands.check(ismanager)
    @commands.command(aliases=["getserverdata"])
    async def getsdata(self, ctx, server: discord.Guild | None):
        """This returns the server files.

        Useful for debugging things.

        - `server`
        The server you want the data files of. Optional."""
        if not server:
            server = ctx.guild
        try:
            shutil.make_archive(f"data/{server.id}", "zip", f"data/servers/{server.id}")
            sdata = discord.File(f"data/{server.id}.zip")
            await ctx.message.reply(
                content=f"{server.name}'s data...",
                file=sdata,
                mention_author=False,
            )
            os.remove(f"data/{server.id}.zip")
        except FileNotFoundError:
            await ctx.message.reply(
                content="That server doesn't have any data yet.",
                mention_author=False,
            )

    @commands.bot_has_permissions(attach_files=True)
    @commands.check(ismanager)
    @commands.command()
    async def getlogs(self, ctx):
        """This gets the bot's log file.

        Useful for trying to figure out problems within Discord.

        No arguments."""
        shutil.copy("logs/fluff.log", "logs/upload.log")
        await ctx.message.reply(
            content="The current log file...",
            file=discord.File("logs/upload.log", filename="fluff.log"),
            mention_author=False,
        )
        os.remove("logs/upload.log")

    @commands.check(ismanager)
    @commands.command()
    async def taillogs(self, ctx):
        """This gets the last 10 lines of the log file.

        Useful for trying to figure out problems within Discord.

        No arguments."""
        shutil.copy("logs/fluff.log", "logs/upload.log")
        with open("logs/upload.log", "r+") as f:
            tail = "\n".join(f.read().split("\n")[-10:])
        os.remove("logs/upload.log")
        await ctx.message.reply(
            content=f"The current tailed log file...\n```{tail.replace('```', '')}```",
            mention_author=False,
        )

    @commands.check(ismanager)
    @commands.command()
    async def guilds(self, ctx):
        """This shows the current guilds that the bot is in.

        Not sure why this is needed.

        No arguments."""
        guildmsg = "**I am in the following guilds:**"
        for g in self.bot.guilds:
            guildmsg += f"\n- {g.name} with `{g.member_count}` members."
        await ctx.reply(content=guildmsg, mention_author=False)

    @commands.check(ismanager)
    @commands.guild_only()
    @commands.command()
    async def permcheck(
        self,
        ctx,
        target: discord.Member = None,
        channel: discord.abc.GuildChannel = None,
    ):
        """This shows the permissions for a user in a channel.

        Though its a debugging command, I should probably make this
        usable for server staff as well...
        Defaults to the bot in the current channel.

        - `target`
        The user to view the permissions for. Optional.
        - `channel`
        The channel to view the user's permissions in. Optional."""
        if not target:
            target = ctx.guild.me
        if not channel:
            channel = ctx.channel
        await ctx.reply(
            content=f"{target}'s permissions for {channel.name}...\n```diff\n"
            + "\n".join(
                [
                    f"{'-' if not y else '+'} " + x
                    for x, y in iter(channel.permissions_for(target))
                ]
            )
            + "```",
            mention_author=False,
        )

    @commands.bot_has_permissions(manage_threads=True)
    @commands.check(ismanager)
    @commands.command()
    async def threadlock(self, ctx, channel: discord.TextChannel):
        """This locks every thread in a channel.

        I've only used this once for one specific use case.
        But it's here anyway!

        - `channel`
        The channel to lock all threads in."""
        msg = await ctx.reply(content="Locking threads...", mention_author=False)
        # Pull old archvied threads from the grave.
        async for t in channel.archived_threads():
            await t.edit(archived=False)
        async for t in channel.archived_threads(private=True, joined=True):
            await t.edit(archived=False)
        # Unsure if needed, but here anyway.
        channel = await ctx.guild.fetch_channel(channel.id)
        # Lock all threads.
        for t in channel.threads:
            await t.edit(locked=True)
            await t.edit(archived=True)
        await msg.edit(content="Done.")

    @commands.check(ismanager)
    @commands.command()
    async def setavy(self, ctx, avy: discord.Attachment):
        """This sets the avy for a bot.

        If it's a gif, will patch it in so it's animated.

        - `avy`
        The avy to set."""
        avydata = await avy.read()
        await self.bot.user.edit(avatar=avydata)
        return await ctx.reply(content="Done.", mention_author=False)

    @commands.check(ismanager)
    @commands.command()
    async def setbanner(self, ctx, banner: discord.Attachment):
        """This sets the banner for a bot.

        Not much else to it.

        - `banner`
        The banner to set."""
        bannerdata = await banner.read()
        headers = {
            "authorization": "Bot " + self.bot.config.token,
            "Content-Type": "application/json",
        }
        data = {
            "banner": f"data:{banner.content_type};base64,{base64.b64encode(bannerdata).decode('utf-8')}"
        }
        async with self.bot.session.patch(
            "https://discord.com/api/v10/users/@me", json=data, headers=headers
        ) as response:
            return await ctx.reply(content=f"Done. {response}", mention_author=False)

    @Cog.listener()
    async def on_guild_join(self, guild):
        msgs = []
        for m in self.bot.config.managers:
            msg = await self.bot.get_user(m).send(
                content=f"{self.bot.user.name} joined `{guild}` with `{len(guild.members)}` members.\nCheck the checkmark within an hour to leave."
            )
            await msg.add_reaction("✅")
            msgs.append(msg)

        def check(r, u):
            return (
                u.id in self.bot.config.managers
                and str(r.emoji) == "✅"
                and type(r.message.channel) == discord.channel.DMChannel
            )

        try:
            r, u = await self.bot.wait_for("reaction_add", timeout=600.0, check=check)
        except asyncio.TimeoutError:
            pass
        else:
            await guild.leave()
            for m in msgs:
                await m.edit(content=f"{m.content}\n\nI have left this guild.")


async def setup(bot):
    await bot.add_cog(Admin(bot))
