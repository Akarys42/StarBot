from string import Template

from disnake import Embed
from disnake.ext.commands import Cog, slash_command

from starbot.bot import StarBot
from starbot.constants import ACI, GIT_SHA
from starbot.utils.time import TimestampFormats, discord_timestamp

REPO_URL = "https://git.akarys.me/StarBot"


class Info(Cog):
    """General informations about the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @slash_command()
    async def info(self, inter: ACI) -> None:
        """Get general information about the bot."""
        config = await self.bot.get_config(inter)

        description = Template(config.bot.description).safe_substitute(
            display_name=inter.me.display_name
        )

        embed = Embed(
            title=inter.me.display_name, description=description, color=config.colors.info
        )

        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f}ms")
        embed.add_field(
            name="Uptime",
            value=f"Started {discord_timestamp(self.bot.start_time, TimestampFormats.RELATIVE)}",
        )
        embed.add_field(name="Running", value=f"[StarBot]({REPO_URL}), *build `{GIT_SHA[:6]}`*")
        embed.set_thumbnail(self.bot.user.display_avatar.url)

        await inter.send(embed=embed)


def setup(bot: StarBot) -> None:
    """Load the module."""
    bot.add_cog(Info(bot))
