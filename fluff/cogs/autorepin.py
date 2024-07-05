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
    async def pinadd(self, ctx, message_link: str, position: int, channel_id: int = None):
        try:
            message_id = int(re.search(r'/(\d+)$', message_link).group(1))
        except AttributeError:
            return await ctx.send("Invalid message link format. Provide a valid message link.")

        if not channel_id:
            channel_id = ctx.channel.id

        if channel_id not in self.pinned_messages["channels"]:
            self.pinned_messages["channels"][channel_id] = {"pinned_messages": []}

        pinned_messages = self.pinned_messages["channels"][channel_id]["pinned_messages"]

        if any(msg['message_id'] == message_id for msg in pinned_messages):
            return await ctx.send("Message is already pinned.")

        if position < 1 or position > len(pinned_messages) + 1:
            return await ctx.send("Invalid position. Must be between 1 and the current number of pinned messages + 1.")

        pinned_messages.insert(position - 1, {"message_id": message_id, "position": position})
        self.save_pinned_messages()
        await ctx.send(f"Message {message_id} added to pinned list at position {position} in channel {channel_id}.")

    @commands.command()
    async def pinlist(self, ctx, channel_id: int = None):
        if not channel_id:
            channel_id = ctx.channel.id

        if channel_id not in self.pinned_messages["channels"]:
            return await ctx.send(f"No pinned messages for channel {channel_id}.")

        pinned_messages = self.pinned_messages["channels"][channel_id]["pinned_messages"]
        if not pinned_messages:
            return await ctx.send(f"No pinned messages for channel {channel_id}.")

        message_list = "\n".join([f"Position {msg['position']}: <https://discord.com/channels/{ctx.guild.id}/{channel_id}/{msg['message_id']}>" for msg in pinned_messages])
        await ctx.send(f"**Pinned Messages in channel {channel_id}:**\n{message_list}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.pinned:
            await self.repin_messages(message.channel.id)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel_id = int(payload.data['channel_id'])
        if channel_id not in self.pinned_messages["channels"]:
            return

        await self.repin_messages(channel_id)

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