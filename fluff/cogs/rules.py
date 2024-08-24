import discord
import json
import io
import asyncio
from discord.ext import commands
from discord.ext.commands import Cog
from helpers.checks import isadmin
from helpers.embeds import stock_embed
from helpers.datafiles import get_guildfile, set_guildfile

class Rules(Cog):
    def __init__(self, bot):
        self.bot = bot

    

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} cog has been loaded')

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(aliases=["r", "rules"], invoke_without_command=True)
    async def rule(self, ctx: commands.Context, *, name=None):
        guild_rules = get_guildfile(ctx.guild.id, "rules")
        summary_embed = stock_embed(self.bot)
        summary_embed.title = "Rules"
        summary_embed.color = discord.Color.red()
        summary_embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)

        if not name:
            if not guild_rules:
                summary_embed.add_field(
                    name = "No Rules",
                    value = "There are no rules available in this server.",
                    inline=False,
                )
            else:
                for guild_rule in guild_rules.items():
                    summary_embed.add_field(
                        name=f"**{guild_rule[0]}**",
                        value=f"> {io.StringIO(guild_rule[1]).readline()}",
                        inline=False,
                    )
        elif name in guild_rules:
            return await ctx.reply(content=f"{guild_rules[name]}", mention_author=False)

        return await ctx.reply(embed=summary_embed, mention_author=False)
        
    @commands.check(isadmin)
    @rule.command(aliases=["add"])
    async def create(self, ctx: commands.Context, rule: str, *, content:str):
        guild_rules = get_guildfile(ctx.guild.id, "rules")
        if not guild_rules:
            guild_rules = {}
        if rule in guild_rules:
            react_msg = await ctx.reply(f"Rule `{rule}` already exists. Do you wish to overwrite it instead?", mention_author=False)
            await react_msg.add_reaction("✅")

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=60,
                    check=lambda reaction, user: user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == react_msg.id,
                )
            except asyncio.TimeoutError:
                return await react_msg.edit(content="No reaction received. Rule not overwritten.")

            guild_rules[rule] = content
            set_guildfile(ctx.guild.id, "rules", json.dumps(guild_rules))
            await react_msg.edit(content="Rule overwritten.", allowed_mentions=discord.AllowedMentions.none())
        else:
            guild_rules[rule] = content
            set_guildfile(ctx.guild.id, "rules", json.dumps(guild_rules))
            return await ctx.reply(f"Rule `{rule}` created.", mention_author=False)
    
async def setup(bot):
    await bot.add_cog(Rules(bot))