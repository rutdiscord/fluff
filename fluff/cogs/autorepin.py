import discord
from discord.ext import commands
import json
import os
import re

class PinHandler(commands.Cog):
    def __init__(self, bot, json_file):
        self.bot = bot
        self.json_file = json_file
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

    @commands.command(name="pinadd")
    async def pin_add_message(self, ctx, message_link: str, position: int):
        try:
            message_id = int(re.search(r'/(\d+)$', message_link).group(1))
        except AttributeError:
            return await ctx.send("Invalid message link format. Provide a valid message link.")

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
        await ctx.send(f"Message {message_id} added to pinned list at position {position}.")

    @commands.command(name="pinlist")
    async def pin_list_messages(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            channel = ctx.channel

        channel_id = channel.id
        if channel_id not in self.pinned_messages["channels"]:
            return await ctx.send(f"No pinned messages for #{channel.name}.")

        pinned_messages = self.pinned_messages["channels"][channel_id]["pinned_messages"]
        if not pinned_messages:
            return await ctx.send(f"No pinned messages for #{channel.name}.")

        message_list = "\n".join([f"Position {msg['position']}: <https://discord.com/channels/{ctx.guild.id}/{channel_id}/{msg['message_id']}>" for msg in pinned_messages])
        await ctx.send(f"**Pinned Messages in #{channel.name}:**\n{message_list}")

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel_id = int(payload.data['channel_id'])
        if channel_id not in self.pinned_messages["channels"]:
            return

        message_id = int(payload.message_id)
        channel_pinned_messages = self.pinned_messages["channels"][channel_id]["pinned_messages"]

        for msg in channel_pinned_messages:
            if msg['message_id'] == message_id:
                channel = self.bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)

                if not message.pinned:
                    return

                for pinned_msg in channel_pinned_messages:
                    pinned_message = await channel.fetch_message(pinned_msg['message_id'])
                    await pinned_message.unpin()
                    await pinned_message.pin()
                return

    def cog_unload(self):
        self.save_pinned_messages()

def setup(bot):
    bot.add_cog(PinHandler(bot, "pinned_messages.json"))