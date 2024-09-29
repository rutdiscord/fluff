import discord
from discord.ext.commands import Cog
from discord.ext import commands
from helpers.embeds import stock_embed
from helpers.sv_config import get_config


class ReactionLogging(Cog):
    def __init__(self, bot):
        self.bot = bot

    def enabled(self, guild: discord.Guild):

        possible_log_channel = get_config(guild.id, "logging", "modlog")

        return all(
            [
                self.bot.get_channel(possible_log_channel) != None,
                isinstance(
                    self.bot.get_channel(possible_log_channel),
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

        log_channel = get_config(user.guild.id, "logging", "modlog")

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
                url=f"https://cdn.discordapp.com/emojis/{reaction.emoji.id}.png?size=1024"
            )
        # {f'(https://cdn.discordapp.com/emojis/{reaction.emoji.id}.png?size=1024)' if isinstance(reaction.emoji, discord.PartialEmoji) or isinstance(reaction.emoji, discord.Emoji) else ""}

        return await log_channel.send(embed=log_embed)


async def setup(bot: discord.Client):
    await bot.add_cog(ReactionLogging(bot))
