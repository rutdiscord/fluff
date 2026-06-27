import discord
from discord.ext import commands

class NotificationService:
    """A service that is responsible for sending messages in the notification channels"""
    def __init__(self, bot):
        self.bot = bot
        self.config_service = self.bot.config_service

    async def send_notification(self, guild: discord.Guild, embed: discord.Embed):
        """Sends an embed to the notification channel.
        Returns: the channel used, or None"""
        channel = self.bot.pull_channel(guild, self.config_service.get_server_config(guild.id, "toss", "notificationchannel"))
        if channel:
            try:
                await channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException) as err:
                self.bot.log.error(f"Failed to send message in notification channel for server {guild.id}: {err}")
        return