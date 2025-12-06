import discord
from discord.ext.commands import Cog
from discord.ext import commands
from unidecode import unidecode
from helpers.checks import ismod
from helpers.sv_config import get_config


class ModNamecheck(Cog):
    """
    Keeping names readable.
    """

    def __init__(self, bot):
        self.bot = bot
        self.readablereq = 1

    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command(aliases=["namefix"])
    async def fixname(self, ctx, target: discord.Member):
        """This cleans unicode from a username.

        There's not much more to it.

        - `target`
        The target to clean unicode from."""
        oldname = target.display_name
        newname = unidecode(target.display_name)[:31]
        if not newname:
            newname = "Unreadable Name"
        await target.edit(nick=newname, reason="Namecheck")
        return await ctx.reply(
            content=f"""Successfully fixed **{oldname}**, changing it to `{newname}`. 
Please review rule 6! Your nickname must be at least partially typable using a standard QWERTY keyboard.""",
            mention_author=False,
        )

    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.check(ismod)
    @commands.guild_only()
    @commands.command()
    async def dehoist(self, ctx, targets: commands.Greedy[discord.Member]):
        """This dehoists users from the member list.

        It uses a specific unicode character to do so.

        - `target`
        The target to dehoist."""
        affected_users = []
        for target in targets:
            old_display_name = target.display_name
            await target.edit(nick="᲼" + target.display_name, reason="Namecheck")
            affected_users.append(old_display_name)

        return await ctx.reply(
            content=f"Successfully dehoisted **{', '.join(affected_users)}**.",
            mention_author=False,
        )

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.bot.wait_until_ready()
        if not get_config(member.guild.id, "reaction", "autoreadableenable"):
            return

        await self.namefix(member)

    @Cog.listener()
    async def on_member_update(self, _, member_after: discord.Member):
        await self.bot.wait_until_ready()
        if not get_config(member_after.guild.id, "reaction", "autoreadableenable"):
            return

        await self.namefix(member_after)
    
    async def namefix(self, member: discord.Member):
        # Non-Alphanumeric
        new_name = member.display_name
        readable = len([b for b in new_name if b.isascii()])
        if readable < self.readablereq:
            new_name = unidecode(new_name) if unidecode(new_name) else "Unreadable Name"

        # Dehoist
        if new_name[:1] in ("!", "-", ".", "(", ")", ":"):
            new_name = "᲼" + new_name

        # Validate
        if len(new_name) > 32:
            new_name = new_name[:29] + "..."
        if new_name != member.display_name:
            try:
                await member.edit(nick=new_name, reason="Automatic Namecheck")
            except discord.errors.HTTPException:
                #User likely had a name that turns into a naughty word
                await member.edit(nick="NAUGHTY_NICKNAME", reason="Automatic Namecheck")


async def setup(bot):
    await bot.add_cog(ModNamecheck(bot))
