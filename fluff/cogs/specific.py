from discord.ext import commands
from discord.ext.commands import Cog
from helpers.sv_config import get_config
from helpers.embeds import stock_embed


class specific(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.command()
    async def staff(self, ctx):
        """This shows the currently active staff.

        It merges admins and mods together, sorry!

        No arguments."""
        adminrole = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "staff", "adminrole")
        )
        modrole = self.bot.pull_role(
            ctx.guild, get_config(ctx.guild.id, "staff", "modrole")
        )

        if not adminrole and not modrole:
            return await ctx.reply(
                content="Neither an `adminrole` or a `modrole` are configured.",
                mention_author=False,
            )
        elif not adminrole:
            members = modrole.members
            color = modrole.color
        elif not modrole:
            members = adminrole.members
            color = adminrole.color
        else:
            members = list(dict.fromkeys(adminrole.members + modrole.members))
            color = modrole.color

        if ctx.guild.owner not in members:
            members.append(ctx.guild.owner)
        members = sorted(members, key=lambda v: v.joined_at)

        embed = stock_embed(self.bot)
        embed.color = color
        embed.title = "Staff List"
        embed.description = f"Voting requirement is `{int(len(members)/2//1+1)}`."

        online = []
        away = []
        dnd = []
        offline = []
        for m in members:
            u = f"{m.mention}"
            if m.raw_status == "online":
                online.append(u)
            elif m.raw_status == "offline":
                offline.append(u)
            elif m.raw_status == "dnd":
                dnd.append(u)
            elif m.raw_status == "idle":
                away.append(u)
        if online:
            embed.add_field(
                name=f"🟢 Online [`{len(online)}`/`{len(members)}`]",
                value=f"{', '.join(online)}",
                inline=False,
            )
        if away:
            embed.add_field(
                name=f"🟡 Idle [`{len(away)}`/`{len(members)}`]",
                value=f"{', '.join(away)}",
                inline=False,
            )
        if dnd:
            embed.add_field(
                name=f"🔴 Do Not Disturb [`{len(dnd)}`/`{len(members)}`]",
                value=f"{', '.join(dnd)}",
                inline=False,
            )
        if offline:
            embed.add_field(
                name=f"⚫ Offline [`{len(offline)}`/`{len(members)}`]",
                value=f"{', '.join(offline)}",
                inline=False,
            )
        await ctx.reply(embed=embed, mention_author=False)



    @Cog.listener()
    async def on_message(self, message):
        await self.bot.wait_until_ready()

        # announcement handling
        if (
            message.guild
            and message.guild.id == 120330239996854274
            and message.channel.id == 120664346421493760
        ):
            general = await message.guild.fetch_channel(120330239996854274)
            return await general.send(
                f"*binkies in* AN ANNOUNCEMENT HAS BEEN POSTED IN <#120664346421493760> *binkies away*"
            )


async def setup(bot):
    await bot.add_cog(specific(bot))