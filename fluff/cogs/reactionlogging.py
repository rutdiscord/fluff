import discord
from discord.ext.commands import Cog
from discord.ext import commands
from helpers.embeds import stock_embed
from helpers.sv_config import get_config


class ReactionLogging(Cog):
    def __init__(self, bot):
        self.bot = bot

    def enabled(self, guild: discord.Guild):
        try:
            possible_log_channel = self.bot.pull_channel(guild, get_config(guild.id, "logging", "reactlog"))
        except KeyError:
            return False # Don't Even Bother!
        
        return all(
            [
                possible_log_channel != None,
                isinstance(
                    possible_log_channel,
                    discord.abc.Messageable,
                ),
            ]
        )

    def username_system(self, user):
        return (
            ""
            + self.bot.pacify_name(user.global_name)
            + f" [{self.bot.pacify_name(str(user))}]"
            if user.global_name
            else f"{self.bot.pacify_name(str(user))}"
        )

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if not self.enabled(user.guild):
            return
        
        if user == self.bot.user or user.bot:
            return

        log_channel = self.bot.get_channel(
            get_config(user.guild.id, "logging", "reactlog")
        )

        log_embed = stock_embed(self.bot)
        log_embed.title = f"{self.username_system(user)}"
        log_embed.set_author(
            name=f"Fluff Reaction Logging",
        )

        if isinstance(reaction.emoji, discord.PartialEmoji) or isinstance(
            reaction.emoji, discord.Emoji
        ):
            log_embed.description = (
                f"**Emoji:** {reaction.emoji.name} ({reaction.emoji.id})"
                + "\n"
                + f"**Message**: {reaction.message.jump_url}"
            )

            log_embed.set_image(
                url=f"https://cdn.discordapp.com/emojis/{reaction.emoji.id}.{"png" if reaction.emoji.animated != True else "gif"}?size=1024"
            )

        elif isinstance(reaction.emoji, str):
            log_embed.description = (
                f"**Emoji:** {reaction.emoji}"
                + "\n"
                + f"**Message**: {reaction.message.jump_url}"
            )

        return await log_channel.send(embed=log_embed)


async def setup(bot: discord.Client):
    await bot.add_cog(ReactionLogging(bot))
