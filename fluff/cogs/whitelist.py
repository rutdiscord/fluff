import sqlite3
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from database.repository.whitelist_ping_repository import WhitelistPingRepository
from helpers.embeds import stock_embed
from converter.mention_or_id_converter import MentionOrIDUser, MentionOrIDMember
import io

MAX_CHARACTERS_PER_EMBED = 980

"""Whitelist Cog which allows users to add other users to their ping whitelist. This prevents any whitelisted users
from receiving ping violations."""
class Whitelist(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist_ping_repo: WhitelistPingRepository = WhitelistPingRepository(self.bot.db)

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def whitelist(self, ctx: commands.Context, user: Optional[MentionOrIDUser] = None):
        """Display whitelisted users.

        Please note that whitelisting only applies if you have the whitelist ping role.
        Available commands:
        pls whitelist\npls whitelist add user1, user2, etc\npls whitelist remove user1, user2, etc
        pls whitelist user\n pls whitelist check

        - `user`
        The user whose whitelist you would like to check. Optional. returns your own whitelist if no user is passed
        """
        whitelisted_users = list()
        user_id = user.id if user else ctx.author.id
        try:
            whitelisted_users = await self.whitelist_ping_repo.get_whitelisted_users(user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get whitelisted users for user ID {user_id}: {err}")
            return await ctx.reply(content="Unable to get whitelisted users", mention_author=False)

        if not whitelisted_users:
            if user_id == ctx.author.id:
                return await ctx.reply(
                    content="You have not whitelisted any users yet. Use `pls whitelist add` to add users to your whitelist.",
                    mention_author=False)
            else:
                return await ctx.reply(
                    content="This user has not whitelisted any users yet.",
                    mention_author=False)

        user_name = user.display_name if user else ctx.author.display_name
        return await self.create_and_send_whitelist_embed(f"Whitelisted users for {user_name}", f"whitelisted-users-{user_id}", ctx, whitelisted_users)

    @whitelist.command()
    @commands.guild_only()
    async def check(self, ctx: commands.Context):
        """Returns all users who have the author in their whitelist"""
        users_who_have_whitelisted_author = list()
        try:
            users_who_have_whitelisted_author = await self.whitelist_ping_repo.get_users_who_whitelisted_user(ctx.author.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get users who have whitelisted user ID {ctx.author.id}: {err}")
            return await ctx.reply(content="Unable to get users who have whitelisted you", mention_author=False)

        if not users_who_have_whitelisted_author:
            return await ctx.reply(
                content="No one has whitelisted you yet.",
                mention_author=False)

        return await self.create_and_send_whitelist_embed(f"Users who have whitelisted {ctx.author.display_name}", f"users-who-whitelisted-{ctx.author.id}", ctx, users_who_have_whitelisted_author)

    @whitelist.command()
    @commands.guild_only()
    async def add(self, ctx: commands.Context, members: commands.Greedy[MentionOrIDMember]):
        """Adds a list of members to the users whitelist."""
        if not members:
            return await ctx.reply(content="Please include at least one valid user ID or user mention",
                                   mention_author=False)

        user_ids_to_whitelist = list()
        for member in members:
            if member.id == ctx.author.id:
                return await ctx.reply(content="Cannot add yourself to your whitelist", mention_author=False)
            if member.bot:
                return await ctx.reply(content="Bots cannot be added to your whitelist", mention_author=False)
            user_ids_to_whitelist.append(member.id)
        inserted = 0
        try:
            inserted = await self.whitelist_ping_repo.add_whitelisted_users(ctx.author.id, user_ids_to_whitelist)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to add whitelisted users for {ctx.author.id}: {err}")
            return await ctx.reply(
                content="Unable to add users to your whitelist. Make sure you aren't trying to whitelist someone who you have already whitelisted.",
                mention_author=False)

        return await ctx.reply(content=f"Successfully added {inserted} users to your whitelist",
                               mention_author=False)

    @whitelist.command()
    @commands.guild_only()
    async def remove(self, ctx: commands.Context, members: commands.Greedy[MentionOrIDUser]):
        """Removes a list of members from the users whitelist."""
        if not members:
            return await ctx.reply(content="Please include at least one valid user ID or user mention",
                                   mention_author=False)

        user_ids_to_remove = [member.id for member in members]
        user_ids_deleted: int = 0
        try:
            user_ids_deleted = await self.whitelist_ping_repo.remove_whitelisted_users(ctx.author.id, user_ids_to_remove)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to remove whitelisted users for {ctx.author.id}: {err}")
            return await ctx.reply(
                content="Unable to remove users from your whitelist.",
                mention_author=False)

        if user_ids_deleted == len(user_ids_to_remove):
            return await ctx.reply(content=f"Successfully removed {user_ids_deleted} users from your whitelist",
                                   mention_author=False)
        else:
            return await ctx.reply(content=f"Removed {user_ids_deleted}/{len(user_ids_to_remove)} mentioned users. Some users were not in your whitelist",
                                   mention_author=False)

    async def create_and_send_whitelist_embed(self, embed_title: str, file_title: str, ctx: commands.Context, user_ids: list[int]):
        """Constructs the embed consisting of the users that are whitelisted, and sends the response"""
        embed = stock_embed(self.bot)
        embed.color = discord.Color.light_embed()
        embed.title = embed_title

        partitioned_user_mentions = self.partition_user_mentions(user_ids)
        for user_mention in partitioned_user_mentions:
            embed.add_field(
                name="",
                value=user_mention,
                inline=False,
            )

        # length of embed can have no more than 6000 characters in it. That is somewhere above 200 people in a users whitelist.
        # length of partitioned_user_mentions would require the user to have over 1000 people in their whitelist,
        # so that is very unlikely.
        if len(embed) > 6000 or len(partitioned_user_mentions) > 25:
            file_content = ""
            for user_mention in partitioned_user_mentions:
                file_content += user_mention + "\n"
            await ctx.send(
                file=discord.File(
                    io.StringIO(file_content),  # type:ignore
                    filename=f"{file_title}.txt",
                )
            )
        else:
            await ctx.reply(embed=embed, mention_author=False)

    def partition_user_mentions(self, user_ids: list[int]) -> list[str]:
        """Partitions user ID's into a list of user mentions. A discord embed only allows up to 1024 characters.
        Any more than that, and we get an error. This method splits up user mentions into a list so that we can create
        multiple embeds, if necessary.

        Returns: a list of user mentions, where each string in the list is made up of multiple comma separated user
        mentions"""
        partitions = []
        current = []
        current_len = 0

        for user_id in user_ids:
            mention = f"<@{user_id}>"
            # + 3 for " | "
            characters_added = len(mention) + 3
            if current_len + characters_added > MAX_CHARACTERS_PER_EMBED:
                partitions.append(' | '.join(current))
                current = [mention]
                current_len = characters_added
            else:
                current.append(mention)
                current_len += characters_added

        if current:
            partitions.append(' | '.join(current))

        return partitions

async def setup(bot):
    await bot.add_cog(Whitelist(bot))

