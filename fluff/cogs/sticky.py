import discord
from discord.ext import commands, tasks
import asyncio

class StickyMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_messages = {}  # Stores sticky message data per channel
        self.repost_tasks = {}  # Stores running tasks for each sticky message

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def setsticky(self, ctx, channel: discord.TextChannel, interval: int, *, message: str):
        """
        Set a sticky message in a channel.
        Args:
        - channel: The channel to set the sticky message in.
        - interval: Time in minutes to repost the message.
        - message: The content of the sticky message.
        """
        if channel.id in self.sticky_messages:
            await ctx.send("There is already a sticky message in this channel. Use `removesticky` to remove it first.")
            return

        self.sticky_messages[channel.id] = {
            "message": message,
            "interval": interval,
            "last_message_id": None
        }
        self.start_reposting(channel)
        await ctx.send(f"Sticky message set in {channel.mention} with an interval of {interval} minutes.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def removesticky(self, ctx, channel: discord.TextChannel):
        """
        Remove the sticky message from a channel.
        Args:
        - channel: The channel to remove the sticky message from.
        """
        if channel.id not in self.sticky_messages:
            await ctx.send("There is no sticky message in this channel.")
            return

        self.stop_reposting(channel)
        del self.sticky_messages[channel.id]
        await ctx.send(f"Sticky message removed from {channel.mention}.")

    def start_reposting(self, channel):
        """Start the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            return

        async def repost_task():
            while channel.id in self.sticky_messages:
                await asyncio.sleep(self.sticky_messages[channel.id]["interval"] * 60)
                if channel.id not in self.sticky_messages:
                    break

                # Delete the last sticky message if it exists
                last_message_id = self.sticky_messages[channel.id]["last_message_id"]
                if last_message_id:
                    try:
                        last_message = await channel.fetch_message(last_message_id)
                        await last_message.delete()
                    except discord.NotFound:
                        pass  # Message was already deleted

                # Send the new sticky message
                new_message = await channel.send(self.sticky_messages[channel.id]["message"])
                self.sticky_messages[channel.id]["last_message_id"] = new_message.id

        self.repost_tasks[channel.id] = self.bot.loop.create_task(repost_task())

    def stop_reposting(self, channel):
        """Stop the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            self.repost_tasks[channel.id].cancel()
            del self.repost_tasks[channel.id]

    @commands.Cog.listener()
    async def on_message(self, message):
        """Reset the repost timer if a new message is sent in a sticky channel."""
        if message.channel.id in self.sticky_messages and not message.author.bot:
            self.sticky_messages[message.channel.id]["last_message_id"] = None

async def setup(bot):
    await bot.add_cog(StickyMessage(bot))