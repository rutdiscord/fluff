import discord
from discord.ext.commands import Cog
from discord.ext import commands
from helpers.sv_config import get_config
from helpers.checks import ismanager, isadmin
from datetime import datetime, timedelta, UTC
from config import logchannel


class Tenure(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nocfgmsg = "Tenure isn't configured for this server.."

    async def check_joindelta(self, member: discord.Member):
        return datetime.now(UTC) - member.joined_at

    def get_tenureconfig(self, guild: discord.Guild):
        return {
            "role_disabled": self.bot.pull_role(
                guild, get_config(guild.id, "tenure", "role_disabled")
            ),
            "role": self.bot.pull_role(guild, get_config(guild.id, "tenure", "role")),
            "threshold": get_config(guild.id, "tenure", "threshold"),
        }

    def enabled(self, guild: discord.Guild):
        try:
            return all(
                (
                    self.bot.pull_role(guild, get_config(guild.id, "tenure", "role")),
                    self.bot.pull_role(
                        guild, get_config(guild.id, "tenure", "role_disabled")
                    ),
                    get_config(guild.id, "tenure", "threshold"),
                )
            )
        except KeyError:
            return False

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.group(invoke_without_command=True)
    async def tenure(self, ctx, user: discord.Member = None):
        """This shows the user their tenure in the server. Or, for staff, queries the status of that user's tenure.

        Any guild channel that has Tenure configured.

        No arguments, unless querying a user, which is just the user you want to query.
        """
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)

        tenure_config = self.get_tenureconfig(ctx.guild)
        tenure_threshold = tenure_config["threshold"]
        tenure_role = tenure_config["role"]
        tenure_disabled_role = tenure_config["role_disabled"]

        if user and isadmin(ctx):
            tenure_dt = await self.check_joindelta(user)
            tenure_days = tenure_dt.days

            if tenure_role not in user.roles and tenure_disabled_role in user.roles:
                return await ctx.reply(
                    f"{user.mention} has been prohibited from receiving the {tenure_role.name} role.",
                    mention_author=False,
                )
            elif tenure_role not in user.roles:
                if tenure_days >= tenure_threshold:
                    return await ctx.reply(
                        f"{user.mention} has been here for {tenure_days} days, and is eligible for the {tenure_role.name} role. They just haven't received it yet!",
                        mention_author=False,
                    )
                else:
                    return await ctx.reply(
                        f"{user.mention} has been here for {tenure_days} days, and is not eligible for the {tenure_role.name} role. They need to wait {tenure_threshold - tenure_days} days.",
                        mention_author=False,
                    )
            elif tenure_role in user.roles:
                return await ctx.reply(
                    f"{user.mention} has been here for {tenure_days} days, and has already received the {tenure_role.name} role.",
                    mention_author=False,
                )

        tenure_dt = await self.check_joindelta(ctx.author)
        tenure_days = tenure_dt.days

        if tenure_disabled_role in ctx.author.roles:
            return await ctx.reply(
                f"You have been prohibited from receiving the {tenure_role.name} role. Please contact staff if this is in error.",
                mention_author=False,
            )

        if tenure_days >= tenure_threshold:
            if tenure_role not in ctx.author.roles:
                await ctx.author.add_roles(tenure_role, reason="Fluff Tenure")
                return await ctx.reply(
                    f"You joined around {tenure_days} (to be more exact, `{tenure_dt} hours:minutes (hours:minutes:ss.mmmmmm, UTC)`) days ago! You've been here long enough to be assigned the {tenure_role.name} role!",
                    mention_author=False,
                )
            else:
                await ctx.reply(
                    f"You joined around {tenure_days} (to be more exact, `{tenure_dt} (hours:minutes:ss.mmmmmm, UTC)`) days ago, and you've already been assigned the {tenure_role.name} role!",
                    mention_author=False,
                )
        else:
            await ctx.reply(
                f"You joined around {tenure_days} (to be more exact, `{tenure_dt} (hours:minutes:ss.mmmmmm, UTC)`) days ago! Not long enough, though.. try again in {(timedelta(days=tenure_threshold)-tenure_dt).days} days!",
                mention_author=False,
            )

    @commands.check(ismanager)
    @tenure.command()
    async def force_sync(self, ctx):
        """THIS WILL FORCEFULLY SYNCHRONIZE THE SERVER MEMBERS WITH THE TENURE ROLE.

        THIS IS VERY TIME CONSUMING.

        RUN ONCE, NEVER AGAIN.
        """
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)
        tenure_config = self.get_tenureconfig(ctx.guild)
        tenure_threshold = tenure_config["threshold"]
        tenure_role = tenure_config["role"]

        await ctx.reply("Oh boy..", mention_author=False)

        for member in ctx.guild.members:
            tenure_dt = await self.check_joindelta(member)
            tenure_days = tenure_dt.days
            print(f"{member.global_name} ({member.id}) joined {tenure_days} days ago")
            if tenure_threshold < tenure_days:
                if tenure_role not in member.roles:
                    print(
                        f"Assigning {tenure_role.name} to {member.global_name}, as they have enough tenure"
                    )
                    await member.add_roles(tenure_role, reason="Fluff Tenure")
                else:
                    return

    @commands.check(isadmin)
    @tenure.command(aliases=["blacklist", "bl"])
    async def disable(self, ctx: commands.Context, user: discord.Member):
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)

        tenure_config = self.get_tenureconfig(ctx.guild)
        tenure_role = tenure_config["role"]
        tenure_disabled_role = tenure_config["role_disabled"]

        if tenure_disabled_role in user.roles:
            return await ctx.reply(
                "This user is already prohibited from receiving the tenure role.",
                mention_author=False,
            )
        else:
            await user.remove_roles(
                tenure_role, reason=f"Fluff Tenure (Prohibition enforcement)"
            )
            await user.add_roles(
                tenure_disabled_role, reason=f"Fluff Tenure (Prohibition enforcement)"
            )
            return await ctx.reply(
                f"{user.mention} has been prohibited from receiving the tenure role.",
                mention_author=False,
            )

    @commands.check(isadmin)
    @tenure.command(aliases=["whitelist", "wl"])
    async def enable(self, ctx: commands.Context, user: discord.Member):
        if not self.enabled(ctx.guild):
            return await ctx.reply(self.nocfgmsg, mention_author=False)

        tenure_config = self.get_tenureconfig(ctx.guild)
        tenure_role = tenure_config["role"]
        tenure_disabled_role = tenure_config["role_disabled"]
        status_msg = await ctx.reply("Processing..", mention_author=False)

        if tenure_disabled_role in user.roles:
            await user.add_roles(
                tenure_role, reason="Fluff Tenure (Prohibition enforcement: Enablement)"
            )
            return await status_msg.edit(
                content=f"{user.mention} has been allowed to receive the {tenure_role.mention} role. They will have to run `pls tenure` to receive the role again."
            )
        else:
            return await status_msg.edit(
                content=f"{user.mention} is not prohibited from receiving the {tenure_role.mention} role. No operations have been performed.",
            )

    @Cog.listener()
    async def on_message(self, msg):
        await self.bot.wait_until_ready()
        if msg.author.bot or msg.is_system() or not msg.guild:
            return

        if not self.enabled(msg.guild):
            return

        tenureconfig = self.get_tenureconfig(msg.guild)
        tenure_dt = await self.check_joindelta(msg.author)
        tenure_days = tenure_dt.days

        # Probably should not be automatically assigning the disable role like this.
        # if tenureconfig["role_disabled"] in msg.author.roles and tenureconfig["role"] in msg.author.roles:
        #     if msg.author.id not in tenureconfig["disabled_users"]:
        #         tenureconfig["disabled_users"][msg.author.id] = "Automatic prohibition enforcement"
        #         set_guildfile(msg.guild.id, "tenure_disabled", json.dumps(tenureconfig["disabled_users"]))
        #     return await msg.author.remove_roles(tenureconfig["role"], reason="Fluff Tenure (Prohibition enforcement)")

        if tenureconfig["role_disabled"] in msg.author.roles:
            return
        elif (
            tenureconfig["role"] not in msg.author.roles
            and tenureconfig["threshold"] < tenure_days
        ):
            return await msg.author.add_roles(
                tenureconfig["role"], reason="Fluff Tenure (Automatic assignment)"
            )


async def setup(bot: discord.Client):
    await bot.add_cog(Tenure(bot))
