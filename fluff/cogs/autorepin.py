import discord
from discord.ext import commands, tasks
import json
import os
import re

class Autorepin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file = "pinned_messages.json"
        self.pinned_messages = self.load_pinned_messages()

    def load_pinned_messages(self):
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w') as file:
                json.dump({"channels": {}}, file, indent=4)
            return {"channels": {}}

        with open(self.json_file, 'r') as file:
            return json.load(file)

    def save_pinned_messages(self):
        with open(self.json_file, 'w') as file:
            json.dump(self.pinned_messages, file, indent=4)

    @commands.command()
    async def pinadd(self, ctx, channel_id: int, message_link: str, position: int):
        # Validate position to be positive integer
        if position <= 0:
            return await ctx.send("Position must be a positive integer.")

        pinned_messages = self.load_pinned_messages()

        # Ensure channel_id exists in the pinned messages data structure
        if str(channel_id) not in pinned_messages["channels"]:
            pinned_messages["channels"][str(channel_id)] = []

        # Add the new pinned message
        new_message = {
            "message_link": message_link,
            "position": position
        }
        pinned_messages["channels"][str(channel_id)].append(new_message)

        # Save the updated pinned messages back to the JSON file
        with open(self.json_file, 'w') as file:
            json.dump(pinned_messages, file, indent=4)

        await ctx.send(f"Message successfully added to pinned list for channel {channel_id} at position {position}.")

    @commands.command()
    async def pinlist(self, ctx, channel_id: int):
        pinned_messages = self.load_pinned_messages()

        if str(channel_id) in pinned_messages["channels"]:
            pinned_messages_list = pinned_messages["channels"][str(channel_id)]
            if pinned_messages_list:
                await ctx.send(f"Pinned messages in channel {channel_id}:")
                for index, message in enumerate(pinned_messages_list, start=1):
                    await ctx.send(f"{index}. {message['message_link']} (Position: {message['position']})")
            else:
                await ctx.send(f"No pinned messages found in channel {channel_id}.")
        else:
            await ctx.send(f"No pinned messages found for channel ID {channel_id}.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.pinned:
            await self.repin_messages(message.channel.id)

    async def repin_messages(self, channel_id):
        if channel_id not in self.pinned_messages["channels"]:
            return

        channel_pinned_messages = self.pinned_messages["channels"][channel_id]["pinned_messages"]

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        pinned_message_ids = [msg['message_id'] for msg in channel_pinned_messages]

        async for pinned_message in channel.pins():
            if pinned_message.id not in pinned_message_ids:
                await pinned_message.unpin()

        for index, pinned_msg in enumerate(channel_pinned_messages, start=1):
            message_id = pinned_msg['message_id']
            try:
                message = await channel.fetch_message(message_id)
                if message:
                    await message.unpin()
                    await message.pin(reason=f"Pinning at position {index}")
            except discord.NotFound:
                pass  # Handle if message is not found

    def cog_unload(self):
        self.save_pinned_messages()

def setup(bot):
    bot.add_cog(Autorepin(bot))