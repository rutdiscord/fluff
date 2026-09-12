from datetime import datetime, timezone, timedelta

import discord

from discord import BanEntry
from discord.ext import commands
from discord.ext.commands import Cog

from database.model.RolebanSession import RolebanSession
from helpers.checks import ismod, check_if_target_is_staff
from helpers.embeds import (
    stock_embed
)
from model.RolebanStatus import RolebanStatus
from model.RolebanType import RolebanType

class ModToss(Cog):
    """Commands for tossing users into muted channels to talk with staff"""
    def __init__(self, bot):
        self.bot = bot

    def username_system(self, user):
        return (
            "**"
            + self.bot.pacify_name(user.global_name)
            + f"** [{self.bot.pacify_name(str(user))}]"
            if user.global_name
            else f"**{self.bot.pacify_name(str(user))}**"
        )

    @commands.bot_has_permissions(embed_links=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["tossed", "session"])
    async def sessions(self, ctx):
        """This shows the open toss sessions.

        Use this in a toss channel to show who's in it.

        No arguments."""
        sessions: list[RolebanSession] | None = await self.bot.roleban_service.get_open_sessions(ctx.guild.id)

        sessions = [session for session in sessions if session.type == RolebanType.TOSS]

        if not sessions:
            return await ctx.reply("No sessions found.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = "Toss Sessions"
        embed.color = ctx.author.color

        tossed_users: list[str] = []
        for session in sessions:
            for rolebanSessionUser in session.users:
                user = await self.bot.fetch_user(rolebanSessionUser.user_id)
                if user:
                    tossed_users.append(self.username_system(user))

            embed.add_field(name=f"<#{session.channel_id}>", value=", ".join(tossed_users), inline=False)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.bot_has_permissions(
        manage_roles=True, manage_channels=True, add_reactions=True
    )
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["roleban", "mute"])
    async def toss(self, ctx, users: commands.Greedy[discord.Member]):
        """This tosses a user.

        - `users`
        The users to toss."""
        members_to_roleban: list[discord.Member] = []

        for us in list(users):
            if us.id == ctx.author.id:
                return await ctx.reply("You cannot toss yourself.", mention_author=False)
            elif us.bot:
                return await ctx.reply("You cannot toss a bot.", mention_author=False)
            elif check_if_target_is_staff(self.bot, us, self.bot.config_service):
                return await ctx.reply("You cannot toss a staff member.", mention_author=False)

            user_session: RolebanSession | None = await self.bot.roleban_service.get_roleban_session_by_user(ctx.guild.id, us.id)
            if user_session is not None:
                return await ctx.reply(f"{us.mention} is already apart of a roleban session in <#{user_session.channel_id}>", mention_author=False)

            members_to_roleban.append(us)

        if not members_to_roleban:
            return await ctx.reply("No members to toss.", mention_author=False)

        # if we are running this command from inside a toss channel, then we want to add users to the existing session
        session: RolebanSession | None = await self.bot.roleban_service.get_roleban_session_by_channel(ctx.guild.id, ctx.channel.id)
        session_id_to_use: int | None = None
        if session:
            if session.type != RolebanType.TOSS:
                return await ctx.reply("Cannot toss user. This is not a valid toss channel.", mention_author=False)

            session_id_to_use = session.id

        session = await self.bot.roleban_service.roleban_users(ctx=ctx, members=members_to_roleban, roleban_type=RolebanType.TOSS, remove_roles=True ,session_to_use=session)
        if not session:
            return await ctx.reply("An error occurred trying to toss the user.", mention_author=False)

        await ctx.message.add_reaction("🚷")

        toss_channel: discord.TextChannel | None = self.bot.get_channel(session.channel_id)
        if toss_channel is None:
            return

        toss_pings = ", ".join([member.mention for member in members_to_roleban])
        toss_message = self.bot.config_service.get_server_config(ctx.guild.id, "toss", "tossmsg")
        await toss_channel.send(
            f"{toss_pings}\nYou were tossed by {self.bot.pacify_name(ctx.author.display_name)}.\n{toss_message}"
        )

        #only ping the user who performed the toss if the channel is newly created
        if not session_id_to_use:
            await toss_channel.send(ctx.author.mention)

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["unroleban", "unmute"])
    async def untoss(self, ctx, users: commands.Greedy[discord.Member] = None):
        """This untosses a user.

        - `users`
        The users to untoss. Optional."""

        if not users:
            return await ctx.reply("No users to untoss.", mention_author=False)

        members_to_untoss: list[discord.Member] = []
        for member in list(users):
            members_to_untoss.append(member)

        if members_to_untoss is None:
            session = await self.bot.roleban_service.get_roleban_session_by_channel(ctx.guild.id, ctx.channel.id)
            if session is None:
                return await ctx.reply("No session found. Either run this inside a toss channel, or specify a member, e.g.: `pls untoss @user`.", mention_author=False)
        else:
            session = await self.bot.roleban_service.get_roleban_session_by_user(ctx.guild.id, members_to_untoss[0].id)
            if session is None:
                return await ctx.reply(f"{members_to_untoss[0].name} is not tossed.", mention_author=False)

        if session.users is None or len(session.users) <= 0:
            return await ctx.reply("There are no members to untoss", mention_author=False)

        if session.type != RolebanType.TOSS:
            return await ctx.reply("This user is not muted.", mention_author=False)

        channel = ctx.guild.get_channel(session.channel_id)

        released = True
        for member in members_to_untoss:
            unrolebanned = await self.bot.roleban_service.unroleban_user(ctx, session, member.id, channel)
            if not unrolebanned:
                released = False

        deleted_channel = False
        if released:
            deleted_channel = await self.bot.roleban_service.delete_roleban_channel(channel=channel, reason="User was untossed", session_id=session.id, delete_session=True)

        if ctx.channel.id != session.channel_id:
            if released and deleted_channel:
                return await ctx.reply("Toss channel removed.", mention_author=False)
            else:
                return await ctx.reply("Toss channel was not removed. Either an error occurred, some users are still rolebanned, or the toss channel no longer exists.", mention_author=False)

    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def close(self, ctx: commands.Context):
        """This closes a mute session.

        - No arguments.
        """
        session: RolebanSession | None = await self.bot.roleban_service.get_roleban_session_by_channel(ctx.guild.id, ctx.channel.id)
        if session is None:
            return await ctx.reply("No roleban session found for this channel.", mention_author=False)

        deleted_channel: bool = await self.bot.roleban_service.delete_roleban_channel(channel=ctx.channel, reason="Channel closed by staff", session_id=session.id, delete_session=False)
        if not deleted_channel:
            return await ctx.reply(f"{session.type.value.capitalize()} channel was not removed. Either an error occurred, some users are still rolebanned, or the channel no longer exists.", mention_author=False)

        embed = stock_embed(self.bot)
        embed.title = f"{session.type.value.capitalize()} Session Closed (Fluff)"
        embed.description = f"`#{ctx.channel.name}`'s session was closed by {ctx.author.mention} ({ctx.author.id})."
        embed.color = ctx.author.color
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        await self.bot.notification_service.send_notification(ctx.channel.guild, embed)

    @Cog.listener()
    async def on_member_join(self, member):
        await self.bot.wait_until_ready()
        guild = member.guild

        reactivated_session_info: tuple[discord.TextChannel, int, bool] | None = await self.bot.roleban_service.reactivate_user_session(guild, member, RolebanType.TOSS)
        if reactivated_session_info is None:
            return

        channel, session_id, channel_recreated = reactivated_session_info
        toss_msg_rejoin: str = self.bot.config_service.get_server_config(member.guild.id, 'toss', 'tossmsg_rejoin')
        await channel.send(f"🔁 {member.mention}, you left while a toss was in progress, so it has been resumed.\n{toss_msg_rejoin}", allowed_mentions=discord.AllowedMentions(users=True))

    @Cog.listener()
    async def on_member_remove(self, member):
        """If a user left a toss session, and wasnt kicked/banned, then ban the user for toss evasion"""
        await self.bot.wait_until_ready()
        guild: discord.Guild = member.guild

        session: RolebanSession | None = await self.bot.roleban_service.get_roleban_session_by_user(guild.id, member.id)
        if session is None or session.type != RolebanType.TOSS or session.users is None or len(session.users) <= 0:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)

        #check for kick
        async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, after=cutoff, limit=100):
            if entry.target.id == member.id:
                return

        banEntry: BanEntry | None = None
        try:
            banEntry = await guild.fetch_ban(member)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

        if banEntry:
            return

        #user was not kicked or banned, and left on their own
        try:
            await guild.ban(
                member,
                reason=f"[Ban performed by Fluff] Automated ban for toss evasion",
                delete_message_days=0,
            )
        except Exception as err:
            self.bot.log.error(f"Error banning member for leaving during toss session: {err}")

        toss_channel: discord.TextChannel = self.bot.get_channel(session.channel_id)
        if toss_channel is None:
            return

        await self.bot.roleban_service.update_user_session_status(session.id, member.id, RolebanStatus.LEFT)
        await self.bot.roleban_service.delete_roleban_channel(channel=toss_channel, reason="Channel closed because of toss evasion", session_id=session.id, delete_session=False)

    @Cog.listener()
    async def on_autotoss_blocked(self, message: discord.Message, msgauthor: discord.Member):
        await self.bot.wait_until_ready()

        is_target_staff: bool = check_if_target_is_staff(self.bot, msgauthor, self.bot.config_service)
        if is_target_staff:
            return

        session: RolebanSession | None = await self.bot.roleban_service.get_roleban_session_by_user(message.guild.id, msgauthor.id)
        if session is not None:
            return

        ctx: commands.Context = await self.bot.get_context(message)
        if ctx is None or ctx.author is None or ctx.guild is None:
            return

        session = await self.bot.roleban_service.roleban_users(ctx=ctx, members=[msgauthor], roleban_type=RolebanType.TOSS, remove_roles=True, session_to_use=None)
        if not session:
            return await ctx.reply("An error occurred trying to toss the user.", mention_author=False)

        await message.reply(f"{self.username_system(message.author)} has been automatically muted for blocking Fluff.")

        toss_channel: discord.TextChannel = self.bot.get_channel(session.channel_id)
        if toss_channel is None:
            return

        tossmsg_blocked: str | None = self.bot.config_service.get_server_config(message.guild.id, 'toss', 'tossmsg_noreply_blocked')
        if tossmsg_blocked is None:
            return

        await toss_channel.send(f"{msgauthor.mention}, {tossmsg_blocked}",file=discord.File("assets/noreply.png"))

async def setup(bot):
    await bot.add_cog(ModToss(bot))
