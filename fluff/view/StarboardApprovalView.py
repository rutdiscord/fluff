import sqlite3

import discord
from discord import TextChannel
from discord.ui import Button, View

from database.model.StarboardQueue import StarboardQueue
from database.repository.starboard_queue_repository import StarboardQueueRepository
from helpers.message_link_embed import build_message_embed
from model.StarboardQueueStatus import StarboardQueueStatus


class StarboardApprovalView(View):
    """View responsible for approving and denying starboard entries."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.starboard_queue_repo: StarboardQueueRepository = StarboardQueueRepository(self.bot.db)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="starboard_approve")
    async def approve(self, interaction: discord.Interaction, button: Button):
        await self.handle(interaction, approved=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="starboard_deny")
    async def deny(self, interaction: discord.Interaction, button: Button):
        await self.handle(interaction, approved=False)

    async def handle(self, interaction: discord.Interaction, approved: bool):
        starboard_channel_id: int = self.bot.config_service.get_server_config(interaction.guild_id, "starboard", "starboard_channel")
        if not starboard_channel_id:
            return await interaction.response.send_message("No starboard channel is configured.", ephemeral=True)

        queue_message_id = interaction.message.id

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.get_starboard_queue_entry_by_queue_message_id(queue_message_id)
            if not starboard_queue_entry:
                return await interaction.response.send_message("Unknown starboard queue entry.", ephemeral=True)

            status_updated = await self.starboard_queue_repo.update_status(int(starboard_queue_entry.message_id), StarboardQueueStatus.ACCEPTED if approved else StarboardQueueStatus.REJECTED)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error fetching starboard queue entry for {queue_message_id}: {err}")
            return await interaction.response.send_message("Something went wrong.", ephemeral=True)

        if not status_updated:
            return await interaction.response.send_message("This entry has already been handled.", ephemeral=True)

        if approved:
            starboard_channel = await self.get_channel(starboard_channel_id)
            if starboard_channel is None:
                await self.rollback_status(starboard_queue_entry)
                return await interaction.response.send_message("Something went wrong.", ephemeral=True)

            message = await self.get_original_message(starboard_queue_entry)
            if message is None:
                await self.rollback_status(starboard_queue_entry)
                return await interaction.response.send_message("Something went wrong.", ephemeral=True)

            embeds: list[discord.Embed] = await build_message_embed(message)
            try:
                sent_message = await starboard_channel.send(embeds=embeds)
                await self.starboard_queue_repo.update_starboard_message_id(starboard_queue_entry.message_id, sent_message.id)
            except Exception as e:
                await self.rollback_status(starboard_queue_entry)
                self.bot.log.error(f"Error sending starboard queue entry message: {e}")
                return await interaction.response.send_message("Something went wrong.", ephemeral=True)
            except sqlite3.Error as err:
                self.bot.log.error(f"Error updating starboard queue entry message ID: {err}")

        disabled_view = View(timeout=None)
        for item in self.children:
            new_item = Button(
                label=item.label,
                style=item.style,
                custom_id=item.custom_id,
                disabled=True
            )
            disabled_view.add_item(new_item)

        label = "Approved" if approved else "Denied"
        embed = interaction.message.embeds[0]
        embed.set_footer(text=f"{label} by {interaction.user.display_name}")
        await interaction.response.edit_message(
            content=interaction.message.content,
            embeds=interaction.message.embeds,
            view=disabled_view
        )

    async def get_original_message(self, starboard_queue_entry: StarboardQueue) -> discord.Message | None:
        channel = self.bot.get_channel(starboard_queue_entry.channel_id)
        if channel is None:
            return None

        try:
            return await channel.fetch_message(starboard_queue_entry.message_id)
        except discord.HTTPException as e:
            self.bot.log.error(f"Failed to fetch message {starboard_queue_entry.message_id}: {e}")

        return None

    async def get_channel(self, channel_id: int) -> TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException as e:
                self.bot.log.error(f"Failed to fetch channel {channel_id}: {e}")
                return None

        return channel

    async def rollback_status(self, starboard_queue_entry: StarboardQueue):
        try:
            await self.starboard_queue_repo.update_status(int(starboard_queue_entry.message_id), StarboardQueueStatus.SUBMITTED)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error rolling back starboard queue entry status: {err}")
