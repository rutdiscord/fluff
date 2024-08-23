import discord
import json
import os
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.checks import isadmin, ismanager
from helpers.embeds import stock_embed
from helpers.datafiles import get_guildfile, set_guildfile

class Snippets(Cog):
    """
    Commands for easily explaining things.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(aliases=["snippet", "rule"], invoke_without_command=True)
    async def snippets(self, ctx, *, name=None):
        """This displays staff defined tags.

        Using this command by itself will show a list of tags.
        Giving a name will post that rule snippet in the chat.

        - `name`
        The name of the rule snippet to post. Optional."""
        guild_snippets = get_guildfile(ctx.guild.id, "snippets_v2")
        if not name:
            embed = stock_embed(self.bot)
            embed.title = "Available Snippets"
            embed.color = discord.Color.red()
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
            if not guild_snippets:
                embed.add_field(
                    name = "No Snippets",
                    value = "There are no snippets available in this server.",
                    inline=True,
                )
            else:
                for snippet in guild_snippets:
                        embed.add_field(
                            name = f"**{snippet}**",
                            value = ("> " + guild_snippets[snippet]["content"][:60] + "_..._"
                                        + f'\nAliases: {", ".join(guild_snippets[snippet]["aliases"]) if len(guild_snippets[snippet]["aliases"]) > 0 else "None"}'
                            ),
                            inline=True,
                        )

            try:
                await ctx.reply(embed=embed, mention_author=False)
            except discord.errors.HTTPException as exception: # almost always too many embed fields
                if exception.code == 50035:
                    file_content = "" # GITHUB COPILOT CODE LOL
                    for snippet in guild_snippets:
                        file_content += (
                            "**{snippet}** \n" +
                            ("> " + guild_snippets[snippet]["content"][:100] + "..."
                             + f'\nAliases: {", ".join(guild_snippets[snippet]["aliases"]) if len(guild_snippets[snippet]["aliases"]) > 0 else "None"}'
                            )
                        )

                    with open(f"temp/snippets-{ctx.guild.id}.txt", "w") as file:
                        file.write(file_content)

                    file_sent = await ctx.send(file=discord.File(f"temp/snippets-{ctx.guild.id}.txt"))
                    if file_sent:
                        os.remove(f"temp/snippets-{ctx.guild.id}.txt")
                    
        else:
            if name in guild_snippets:
                return await ctx.reply(guild_snippets[name]["content"], mention_author=False)
            else:
                for snippet in guild_snippets:
                    if name in guild_snippets[snippet]["aliases"]:
                        return await ctx.reply(guild_snippets[snippet]["content"], mention_author=False)
            return await ctx.reply(f"Snippet `{name}` not found.", mention_author=False)
                
        
    @snippets.command(aliases=["add"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def create(self, ctx, new_snippet, *, content):
        guild_snippets = get_guildfile(ctx.guild.id, "snippets_v2")
        dict_new_snippet = guild_snippets.get(new_snippet,{})
        if dict_new_snippet == {}:
            guild_snippets[new_snippet] = {
            "content": content,
            "aliases": [],
        }
            set_guildfile(ctx.guild.id, "snippets_v2", json.dumps(guild_snippets))
            return await ctx.reply(f"Snippet `{new_snippet}` added successfully.")
        else:
            return await ctx.reply(f"Snippet `{new_snippet}` already exists.")

    
    @snippets.command(aliases=["amend"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def edit(self, ctx, snippet, * , new_content):
        guild_snippets = get_guildfile(ctx.guild.id, "snippets_v2")

        try:
            guild_snippets[snippet]["content"] = new_content
            set_guildfile(ctx.guild.id, "snippets_v2", json.dumps(guild_snippets))
            return await ctx.reply(f"Snippet `{snippet}` edited successfully.")
        except KeyError:
            return await ctx.reply(f"Snippet `{snippet}` not found.")
        
    @snippets.command(aliases=["alias"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def link(self, ctx, snippet, new_alias):
        guild_snippets = get_guildfile(ctx.guild.id, "snippets_v2")

        try:
            if new_alias in guild_snippets[snippet]["aliases"]:
                return await ctx.reply(f"Alias `{new_alias}` already exists for snippet `{snippet}`.")
            else:
                guild_snippets[snippet]["aliases"].append(new_alias)
                set_guildfile(ctx.guild.id, "snippets_v2", json.dumps(guild_snippets))
                return await ctx.reply(f"Alias `{new_alias}` added successfully for snippet `{snippet}`.")
        except KeyError:
            return await ctx.reply(f"Snippet `{snippet}` not found.")
    
    @snippets.command(aliases=["remove"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def delete(self, ctx, snippet):
        guild_snippets = get_guildfile(ctx.guild.id, "snippets_v2")

        if snippet in guild_snippets:
                del guild_snippets[snippet]
                set_guildfile(ctx.guild.id, "snippets_v2", json.dumps(guild_snippets))
                return await ctx.reply(f"Snippet `{snippet}` deleted successfully.")
        else:
            return await ctx.reply(f"Snippet `{snippet}` not found.")
        

async def setup(bot):
    await bot.add_cog(Snippets(bot))
