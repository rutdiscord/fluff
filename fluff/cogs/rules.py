import sqlite3

import discord
import io

import yaml
from discord.ext import commands
from discord.ext.commands import Cog

from database.model.Rule import Rule
from database.repository.rule_repository import RuleRepository
from helpers.checks import isadmin
from helpers.embeds import stock_embed


class Rules(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rule_repo: RuleRepository = RuleRepository(self.bot.db)

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(aliases=["r", "rules"], invoke_without_command=True)
    async def rule(self, ctx: commands.Context, *, number=None):
        """This displays server defined rules.

        Available commands:
        pls rule
        pls rule rule_number
        pls rule create/add example (this shows you the example file format expected to create a rule)
        pls rule create/add rule_attachment.yml
        pls rule update/edit rule_number rule_attachment.yml
        pls rule delete/remove rule_number

        - `number`
        The rule associated with this rule number to post. Optional."""
        summary_embed = stock_embed(self.bot)
        summary_embed.title = "Rules"
        summary_embed.color = discord.Color.red()
        summary_embed.set_author(
            name=ctx.author, icon_url=ctx.author.display_avatar.url
        )

        if not number:
            server_rules: list[Rule] = []
            try:
                server_rules = await self.rule_repo.get_rules(ctx.guild.id)
            except sqlite3.Error as err:
                self.bot.log.error(f"Error getting rule list for server {ctx.guild.id}: {err}")
                return await ctx.reply("Error getting rule list", mention_author=False)

            if not server_rules:
                summary_embed.add_field(
                    name="No Rules",
                    value="There are no rules available in this server.",
                    inline=False,
                )
            else:
                for rule in server_rules:
                    summary_embed.add_field(
                        name=f"**{rule.rule_number}**",
                        value=f"> **{io.StringIO(rule.title).readline()}.**",
                        inline=False,
                    )

            return await ctx.reply(embed=summary_embed, mention_author=False)

        try:
            number = int(number)
        except ValueError:
            return await ctx.reply("Please provide a valid number", mention_author=False)

        rule: Rule | None = None
        try:
            rule = await self.rule_repo.get_rule_by_number(ctx.guild.id, number)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error getting rule for server {ctx.guild.id}: {err}")
            return await ctx.reply("Error getting rule with that rule number", mention_author=False)

        if rule:
            return await ctx.reply(
                content=f"**Rule {rule.rule_number}. {rule.title}.**\n{rule.content.replace("{{", "").replace("}}", "")}",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            return await ctx.reply(
                content=f"Rule `{number}` not found.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @commands.check(isadmin)
    @rule.command(aliases=["add"])
    async def create(self, ctx: commands.Context, arg: str = None):
        if arg == "example":
            return await ctx.send(content="Example rule creation. Use `pls rule create` and upload the attachment in the same message to create the rule.",
                file=discord.File("assets/rule_example.yml"), mention_author=False)

        if not ctx.message.attachments:
            return await ctx.send("Please provide a `.yml` file or use `pls rule create example` to get an example.")

        attachment = ctx.message.attachments[0]

        if attachment is None:
            return await ctx.send("Please provide a `.yml` file or use `pls rule create example` to get an example.")

        parsed_rules = await self.validate_attachment(ctx, attachment)
        if parsed_rules is None:
            return

        title = parsed_rules["title"]
        content = parsed_rules["content"]

        try:
            await self.rule_repo.add_rule(ctx.guild.id, title, content)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error attempting to add new rule to rules table for server {ctx.guild.id}: {err}")
            return await ctx.reply(f"Error trying to add rule.", mention_author=False)

        return await ctx.reply(f"Rule `{title}` successfully added.", mention_author=False)

    @commands.check(isadmin)
    @rule.command(aliases=["edit"])
    async def update(self, ctx: commands.Context, rule_number_to_update: int, attachment: discord.Attachment):
        parsed_rules = await self.validate_attachment(ctx, attachment)
        if parsed_rules is None:
            return

        try:
            number = int(rule_number_to_update)
        except ValueError:
            return await ctx.reply("Please provide a valid number", mention_author=False)

        title = parsed_rules["title"]
        content = parsed_rules["content"]

        updated_row_count: int = 0
        try:
            updated_row_count = await self.rule_repo.update_rule(ctx.guild.id, rule_number_to_update, title, content)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error attempting to update an existing rule for server {ctx.guild.id}: {err}")
            return await ctx.reply(f"Error trying to update rule.", mention_author=False)

        if updated_row_count > 0:
            return await ctx.reply(f"Rule {rule_number_to_update} successfully updated.", mention_author=False)

        return await ctx.reply(f"Rule {rule_number_to_update} not found.", mention_author=False)

    @rule.command(aliases=["remove"])
    @commands.guild_only()
    @commands.check(isadmin)
    async def delete(self, ctx: commands.Context, rule_number: int):
        try:
            number = int(rule_number)
        except ValueError:
            return await ctx.reply("Please provide a valid number", mention_author=False)

        deleted_count: int = 0
        try:
            deleted_count = await self.rule_repo.delete_rule(ctx.guild.id, rule_number)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error attempting to delete rule number {rule_number}: {err}")
            return await ctx.reply("Error attempting to delete that rule", mention_author=False)


        if deleted_count > 0:
            return await ctx.reply(f"Rule {rule_number} successfully deleted.", mention_author=False)

        return await ctx.reply(f"Rule {rule_number} not found.", mention_author=False)

    async def validate_attachment(self, ctx: commands.Context, attachment: discord.Attachment) -> dict | None:
        """Validates the attachment, ensuring the file and its contents are as expected
        Returns: dict if the validation passed, otherwise None"""
        if not attachment.filename.endswith(".yml"):
            await ctx.send("Please provide a `.yml` file.")
            return None

        try:
            raw_bytes = await attachment.read()
            parsed_rules = yaml.safe_load(raw_bytes.decode("utf-8"))
        except yaml.YAMLError:
            await ctx.reply("Failed to parse YAML file. Make sure your `content` block is indented",
                                   mention_author=False)
            return None
        except (discord.HTTPException, discord.Forbidden, discord.NotFound) as err:
            await ctx.reply("Unable to access the attachment", mention_author=False)
            return None

        if not isinstance(parsed_rules, dict):
            await ctx.reply("Invalid YAML format.", mention_author=False)
            return None

        if "title" not in parsed_rules or "content" not in parsed_rules:
            await ctx.reply("Rule file must contain both `title` and `content`.", mention_author=False)
            return None

        if not isinstance(parsed_rules["title"], str) or not isinstance(parsed_rules["content"], str):
            await ctx.reply("`title` and `content` must both be strings.", mention_author=False)
            return None

        if len(parsed_rules["title"]) + len(parsed_rules["content"]) > 2000:
            await ctx.reply("Combined `title` and `content` must be 2000 characters or less.", mention_author=False)
            return None

        return parsed_rules


async def setup(bot):
    await bot.add_cog(Rules(bot))
