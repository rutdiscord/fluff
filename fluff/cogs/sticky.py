import discord
from discord.ext import commands, tasks
import asyncio
import json
import os

STICKY_DATA_FILE = "sticky_messages.json"

class StickyMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_messages = {}
        self.repost_tasks = {}
        self.load_sticky_data()

    def save_sticky_data(self):
        """Save sticky message data to a JSON file."""
        with open(STICKY_DATA_FILE, "w") as f:
            json.dump(self.sticky_messages, f)

    def load_sticky_data(self):
        """Load sticky message data from a JSON file."""
        if os.path.exists(STICKY_DATA_FILE):
            with open(STICKY_DATA_FILE, "r") as f:
                self.sticky_messages = json.load(f)
        else:
            self.sticky_messages = {}

    def startsticky(self, channel):
        """Start the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            return

        async def repost_task():
            # Post the sticky message immediately when the task starts
            if channel.id in self.sticky_messages:
                last_message_id = self.sticky_messages[channel.id]["last_message_id"]

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
                self.save_sticky_data()  # Save updated last_message_id

            while channel.id in self.sticky_messages:
                # Wait for the interval
                await asyncio.sleep(self.sticky_messages[channel.id]["interval"] * 60)

                # Check if the sticky message is still active
                if channel.id not in self.sticky_messages:
                    break

                # Fetch the latest message in the channel
                try:
                    latest_message = (await channel.history(limit=1).flatten())[0]
                except IndexError:
                    latest_message = None

                # Get the last sticky message ID
                last_message_id = self.sticky_messages[channel.id]["last_message_id"]

                # If the latest message is the bot's sticky, skip reposting
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
                self.save_sticky_data()  # Save updated last_message_id

        # Start the reposting task
        self.repost_tasks[channel.id] = self.bot.loop.create_task(repost_task())

    def stopsticky(self, channel):
        """Stop the reposting task for a sticky message."""
        if channel.id in self.repost_tasks:
            self.repost_tasks[channel.id].cancel()
            del self.repost_tasks[channel.id]

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def setsticky(self, ctx, channel: discord.TextChannel, interval: int, *, message: str):
        """Set a sticky message in a channel."""
        if channel.id in self.sticky_messages:
            await ctx.send("There is already a sticky message in this channel. Use `removesticky` to remove it first.")
            return

        self.sticky_messages[channel.id] = {
            "message": message,
            "interval": interval,
            "last_message_id": None
        }
        self.save_sticky_data()
        self.startsticky(channel)
        await ctx.send(f"Sticky message set in {channel.mention} with an interval of {interval} minutes.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def removesticky(self, ctx, channel: discord.TextChannel):
        """Remove the sticky message from a channel."""
        if channel.id in self.sticky_messages:
            self.stopsticky(channel)
            del self.sticky_messages[channel.id]
            self.save_sticky_data()
            await ctx.send(f"Sticky message removed from {channel.mention}.")
        else:
            await ctx.send(f"There is no sticky message set in {channel.mention}.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearstickies(self, ctx):
        """
        Stop all sticky messages and clear all data.
        This will stop all running sticky tasks and clear the sticky message data.
        """
        # Stop all running sticky tasks
        for channel_id, task in list(self.repost_tasks.items()):
            task.cancel()  # Cancel the task
            del self.repost_tasks[channel_id]  # Remove it from the task dictionary

        # Clear sticky message data
        self.sticky_messages.clear()
        self.save_sticky_data()  # Save the cleared state to JSON

        await ctx.send("All sticky messages have been stopped and cleared.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def liststickies(self, ctx):
        """
        List all active sticky messages.
        This will display all channels with active sticky messages and their details.
        """
        if not self.sticky_messages:
            await ctx.send("There are no active sticky messages.")
            return

        description = []
        for channel_id, data in self.sticky_messages.items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                description.append(
                    f"**Channel:** {channel.mention}\n"
                    f"**Message:** {data['message']}\n"
                    f"**Interval:** {data['interval']} minutes\n"
                )

        embed = discord.Embed(
            title="Active Sticky Messages",
            description="\n\n".join(description),
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Reset the repost timer if a new message is sent in a sticky channel."""
        if message.channel.id in self.sticky_messages and not message.author.bot:
            self.stopsticky(message.channel)
            self.startsticky(message.channel)

async def setup(bot):
    cog = StickyMessage(bot)
    cog.load_sticky_data()

    for channel_id in cog.sticky_messages.keys():
        channel = bot.get_channel(int(channel_id))
        if channel:
            cog.startsticky(channel)

    await bot.add_cog(cog)