import discord
import traceback
import random
import os
from discord.ext import tasks
from discord.ext.commands import Cog

from helpers import datafiles
from helpers.placeholders import game_type, game_names

class Timer(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hourly.start()
        self.daily.start()

    def cog_unload(self):
        self.hourly.cancel()
        self.daily.cancel()

    @tasks.loop(hours=1)
    async def hourly(self):
        await self.bot.wait_until_ready()
        log_channel = self.bot.get_channel(self.bot.config.logchannel)
        try:
            # Change playing status.
            activity = discord.Activity(name=random.choice(game_names), type=game_type)
            await self.bot.change_presence(activity=activity)
        except:
            # Don't kill cronjobs if something goes wrong.
            await log_channel.send(
                f"Cron-hourly has errored: ```{traceback.format_exc()}```"
            )

    @tasks.loop(hours=24)
    async def daily(self):
        await self.bot.wait_until_ready()
        log_channel = self.bot.get_channel(self.bot.config.logchannel)
        try:
            #make backup of database first.
            await self.bot.db.perform_backup()
            zip_name = "data_backup"
            datafiles.make_backup(zip_name)
            for m in self.bot.config.managers:
                try:
                    await self.bot.get_user(m).send(
                        content="Daily backups:",
                        file=discord.File(f"{zip_name}.zip"),
                    )
                except Exception as e:
                    self.bot.log.error(f"Error attempting to send daily backups to {m}: {str(e)}")
            os.remove(f"{zip_name}.zip")
        except Exception as e:
            # Don't kill cronjobs if something goes wrong.
            self.bot.log.error(f"Error in daily backup task: {str(e)}")
            try:
                await log_channel.send(
                    f"Cron-daily has errored: ```{traceback.format_exc()}```"
                )
            except Exception as e2:
                self.bot.log.error(f"Error trying to send log message after cron-daily failed: {str(e2)}")


async def setup(bot):
    await bot.add_cog(Timer(bot))
