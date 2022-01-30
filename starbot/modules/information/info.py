from disnake import Embed
from disnake.ext.commands import Cog, slash_command

from starbot.bot import StarBot
from starbot.constants import ACI
from starbot.utils.time import TimestampFormats, discord_timestamp


class Info(Cog):
    """General informations about the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @slash_command()
    async def info(self, inter: ACI) -> None:
        """Get general information about the bot."""
        config = await self.bot.get_config(inter)

        embed = Embed(title="Status", color=config.color.info)

        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f}ms")
        embed.add_field(
            name="Uptime",
            value=f"Started {discord_timestamp(self.bot.start_time, TimestampFormats.RELATIVE)}",
        )
        await inter.send(embed=embed)


def setup(bot: StarBot) -> None:
    """Load the module."""
    bot.add_cog(Info(bot))
