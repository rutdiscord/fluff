import asyncio
import sqlite3

import discord
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog

from database.model.Snippet import Snippet
from database.repository.snippets_repository import SnippetsRepository
from helpers.checks import isadmin
from helpers.embeds import stock_embed

class Snippets(Cog):
    """
    Commands for easily explaining things.
    """

    def __init__(self, bot):
        self.bot = bot
        self.snippets_repo: SnippetsRepository = SnippetsRepository(self.bot.db)

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(aliases=["snippet", "s"], invoke_without_command=True)
    async def snippets(self, ctx: commands.Context, *, name=None):
        """This displays staff defined tags.

        Using this command by itself will show a list of tags.
        Giving a name will post that rule snippet in the chat.

        - `name`
        The name of the snippet to post. Optional."""
        if not name:
            snippets: list[Snippet] = []
            try:
                snippets: list[Snippet] = await self.snippets_repo.get_snippets(ctx.guild.id)
            except sqlite3.Error as err:
                self.bot.log.error(f"Failed to fetch snippets for guild {ctx.guild.id}: {err}")
                return await ctx.reply(content="Error fetching snippets", mention_author=False)

            embed_list: list[Embed] = self.create_embed_list(ctx, snippets)
            for embed in embed_list:
                try:
                    await ctx.reply(embed=embed, mention_author=False)
                    await asyncio.sleep(0.5)
                except Exception as err:
                    self.bot.log.error(f"Failed to send snippets for guild {ctx.guild.id}: {str(err)}")
            return
        else:
            name = name.lower()
            snippet_content: str | None = await self.snippets_repo.get_snippet_content_by_name(ctx.guild.id, name)
            if snippet_content:
                if ctx.message.reference != None and isinstance(
                    ctx.message.reference.resolved, discord.Message
                ):
                    referenced_message = ctx.message.reference.resolved
                    await ctx.message.delete(delay=1)
                    return await referenced_message.reply(
                        snippet_content,
                        mention_author=True,
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False, roles=False, replied_user=True
                        ),
                    )
                else:
                    return await ctx.reply(
                        snippet_content,
                        mention_author=False,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )

            return await ctx.reply(
                f"Snippet `{name}` not found.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @snippets.command(aliases=["add"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def create(self, ctx: commands.Context, new_snippet: str, *, content: str):
        """Creates a new snippet with the given name and content.

        - `new_snippet`
        The name of the snippet to create.
        - `content`
        Content of the snippet."""
        new_snippet = new_snippet.lower()
        snippet_added: bool = False
        try:
            snippet_added: bool = await self.snippets_repo.add_snippet(ctx.guild.id, new_snippet, content)
        except sqlite3.Error as err:
            self.bot.log.error(f"error adding snippet to snippets table for server: {ctx.guild.id}: {err}")
            return await ctx.reply(content="Error adding snippet. This snippet name or alias may already exist", mention_author=False)

        if snippet_added:
            return await ctx.reply(
                f"Snippet `{new_snippet}` added successfully.",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        return await ctx.reply(
            f"Snippet `{new_snippet}` already exists.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @snippets.command(aliases=["alias"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def link(self, ctx: commands.Context, snippet: str, new_alias: str):
        snippet = snippet.lower()
        new_alias = new_alias.lower()
        snippet_alias_result: str = ''
        try:
            snippet_alias_result = await self.snippets_repo.add_snippet_alias(ctx.guild.id, snippet, new_alias)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error linking snippet for server {ctx.guild.id} and snippet name {snippet}: {err}")
            return await ctx.reply(f"Error linking `{new_alias}` to `{snippet}`. That alias may already exist.", mention_author=False)

        return await ctx.reply(snippet_alias_result, mention_author=False)

    @snippets.command(aliases=["unalias"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def unlink(self, ctx: commands.Context, unaliased: str):
        unaliased = unaliased.lower()

        rows_deleted: int = 0
        try:
            rows_deleted = await self.snippets_repo.remove_snippet_alias(ctx.guild.id, unaliased)
        except sqlite3.Error as err:
            self.bot.log.error(f"error deleting snippet alias {unaliased}: {err}")
            return await ctx.reply(f"error trying to delete snippet alias `{unaliased}`", mention_author=False)

        if rows_deleted > 0:
            return await ctx.reply(f"Alias `{unaliased}` removed successfully.", mention_author=False)

        return await ctx.reply(f"Alias `{unaliased}` not found.", mention_author=False)

    @snippets.command(aliases=["amend"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def edit(self, ctx: commands.Context, snippet: str, *, new_content: str):
        snippet = snippet.lower()
        rows_updated: int = 0
        try:
            rows_updated = await self.snippets_repo.update_snippet(ctx.guild.id, snippet, new_content)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error updating snippet {snippet}: {err}")
            return await ctx.reply(f"Error updating snippet `{snippet}`", mention_author=False)

        if rows_updated > 0:
            return await ctx.reply(f"Snippet `{snippet}` edited successfully.", mention_author=False)

        return await ctx.reply(f"Snippet `{snippet}` not found.", mention_author=False)

    @snippets.command(aliases=["remove"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def delete(self, ctx: commands.Context, snippet: str):
        snippet = snippet.lower()
        rows_deleted: int = 0
        try:
            rows_deleted = await self.snippets_repo.delete_snippet(ctx.guild.id, snippet)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error deleting snippet {snippet}: {err}")
            return await ctx.reply(f"Error deleting snippet `{snippet}`", mention_author=False)

        if rows_deleted > 0:
            return await ctx.reply(f"Snippet `{snippet}` deleted successfully.", mention_author=False)

        return await ctx.reply(f"Snippet `{snippet}` not found.", mention_author=False)

    def create_embed_list(self, ctx: commands.Context, snippets: list[Snippet]) -> list[Embed]:
        """Creates a list of discord embeds. Each embed should be returned as an individual message"""
        embeds: list[Embed] = []

        embed = self.create_embed_frame(ctx)
        if not snippets:
            embed.add_field(name="No Snippets", value="There are no snippets available in this server.", inline=True)
            embeds.append(embed)
            return embeds

        current_embed_count: int = 0
        for snippet in snippets:
            self.add_embed_field(embed, snippet)
            current_embed_count = current_embed_count + 1

            if current_embed_count > 25 or len(embed) > 6000:
                embed.remove_field(-1)
                embeds.append(embed)
                embed = self.create_embed_frame(ctx)
                self.add_embed_field(embed, snippet)
                current_embed_count = 1

        embeds.append(embed)

        page_number = 1
        number_of_pages = len(embeds)
        for embed in embeds:
            embed.title = f"Available Snippets ({page_number}/{number_of_pages})"
            page_number = page_number + 1

        return embeds

    def create_embed_frame(self, ctx: commands.Context) -> Embed:
        """Creates a basic discord embed with title, color, and author information"""
        embed = stock_embed(self.bot)
        embed.title = "Available Snippets"
        embed.color = discord.Color.red()
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

        return embed

    def add_embed_field(self, embed: discord.Embed, snippet: Snippet) -> None:
        """Adds the snippet data to this embed"""
        embed.add_field(
            name=f"**{snippet.name}**",
            value=(
                    "> "
                    + discord.utils.remove_markdown(
                snippet.content[:60]
            )
                    + "_..._"
                    + f'\n**Aliases**: _{", ".join(snippet.aliases) if snippet.aliases else "None"}_'
            ),
            inline=True,
        )


async def setup(bot):
    await bot.add_cog(Snippets(bot))
