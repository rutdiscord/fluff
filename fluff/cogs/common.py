import asyncio
import discord
from discord.ext.commands import Cog


class Common(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.async_call_shell = self.async_call_shell
        self.bot.slice_message = self.slice_message
        self.bot.await_message = self.await_message
        self.bot.pull_role = self.pull_role
        self.bot.pull_channel = self.pull_channel
        self.bot.pull_category = self.pull_category
        self.bot.pacify_name = self.pacify_name

    def pull_role(self, guild: discord.Guild, role):
        if isinstance(role, str):
            role = discord.utils.get(guild.roles, name=role)
        else:
            role = guild.get_role(role)
        return role

    def pull_channel(self, guild, channel):
        if isinstance(channel, str):
            channel = discord.utils.get(
                list(guild.text_channels)
                + list(guild.voice_channels)
                + list(guild.threads),
                name=channel,
            )
        else:
            channel = guild.get_channel_or_thread(channel)
        return channel

    def pull_category(self, guild, category):
        if isinstance(category, str):
            category = discord.utils.get(guild.categories, name=category)
        else:
            category = guild.get_channel(category)
            if category and type(category) != discord.CategoryChannel:
                category = None
        return category

    def pacify_name(self, name):
        return discord.utils.escape_markdown(name.replace("@", "@ "))

    async def await_message(self, channel, author, timeout=60):
        """Nice wrapper for waiting for a message"""

        def check(m):
            return m.author.id == author.id and m.channel.id == channel.id

        try:
            message = await self.bot.wait_for("message", timeout=timeout, check=check)
        except asyncio.TimeoutError:
            return None
        return message

    # 2000 is maximum limit of discord
    def slice_message(self, text, size=2000, prefix="", suffix=""):
        """Slices a message into multiple messages"""
        fragment_list = []
        size_wo_fix = size - len(prefix) - len(suffix)
        while len(text) > size_wo_fix:
            fragment_list.append(f"{prefix}{text[:size_wo_fix]}{suffix}")
            text = text[size_wo_fix:]
        fragment_list.append(f"{prefix}{text}{suffix}")
        return fragment_list

    async def async_call_shell(
        self, shell_command: str, inc_stdout=True, inc_stderr=True
    ):
        pipe = asyncio.subprocess.PIPE
        proc = await asyncio.create_subprocess_shell(
            str(shell_command), stdout=pipe, stderr=pipe
        )

        if not (inc_stdout or inc_stderr):
            return "??? you set both stdout and stderr to False????"

        proc_result = await proc.communicate()
        stdout_str = proc_result[0].decode("utf-8").strip()
        stderr_str = proc_result[1].decode("utf-8").strip()

        if inc_stdout and not inc_stderr:
            return stdout_str
        elif inc_stderr and not inc_stdout:
            return stderr_str

        if stdout_str and stderr_str:
            return f"stdout:\n\n{stdout_str}\n\n" f"======\n\nstderr:\n\n{stderr_str}"
        elif stdout_str:
            return f"stdout:\n\n{stdout_str}"
        elif stderr_str:
            return f"stderr:\n\n{stderr_str}"

        return "No output."


async def setup(bot):
    await bot.add_cog(Common(bot))
