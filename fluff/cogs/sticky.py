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
        self.startsticky(channel)
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

        self.stopsticky(channel)
        del self.sticky_messages[channel.id]
        await ctx.send(f"Sticky message removed from {channel.mention}.")

    def startsticky(self, channel):
        """Start the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            return

        async def repost_task():
            while channel.id in self.sticky_messages:
                # Wait for the interval (plus a 60-second delay after the last message)
                await asyncio.sleep(self.sticky_messages[channel.id]["interval"] * 60)

                # Check if the sticky message is still active
                if channel.id not in self.sticky_messages:
                    break

                # Fetch the latest message in the channel
                try:
                    latest_message = (await channel.history(limit=1).flatten())[0]
                except IndexError:
                    latest_message = None

                # If the latest message is the bot's sticky, do nothing
                last_message_id = self.sticky_messages[channel.id]["last_message_id"]
                if latest_message and latest_message.id == last_message_id:
                    continue

                # Delete the previous sticky message if it exists
                if last_message_id:
                    try:
                        last_message = await channel.fetch_message(last_message_id)
                        await last_message.delete()
                    except discord.NotFound:
                        pass  # Message was already deleted

                # Send the new sticky message
                new_message = await channel.send(self.sticky_messages[channel.id]["message"])
                self.sticky_messages[channel.id]["last_message_id"] = new_message.id

        # Notify when the reposting task starts
        self.repost_tasks[channel.id] = self.bot.loop.create_task(repost_task())
        asyncio.create_task(channel.send("Sticky message reposting has started."))

    def stopsticky(self, channel):
        """Stop the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            self.repost_tasks[channel.id].cancel()
            del self.repost_tasks[channel.id]
            asyncio.create_task(channel.send("Sticky message reposting has been stopped."))

    @commands.Cog.listener()
    async def on_message(self, message):
        """Reset the repost timer if a new message is sent in a sticky channel."""
        if message.channel.id in self.sticky_messages and not message.author.bot:
            # Reset the timer by canceling and restarting the task
            self.stopsticky(message.channel)
            self.startsticky(message.channel)

async def setup(bot):
    await bot.add_cog(StickyMessage(bot))