from disnake.ext.commands import Cog, slash_command

from starbot.bot import StarBot
from starbot.constants import ACI
from starbot.decorators import bypass_guild_configured_check
from starbot.models import GuildModel


class Configuration(Cog):
    """A cog for managing the per guild configuration of the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @bypass_guild_configured_check
    @slash_command()
    async def configure(self, inter: ACI) -> None:
        """Configure the bot."""
        guild = GuildModel(discord_id=inter.guild.id)

        async with self.bot.Session() as session:
            session.add(guild)
            await session.commit()

        await inter.send(
            ":white_check_mark: This server has been configured! "
            "You can now use the `/config` command to adjust the configuration."
        )


def setup(bot: StarBot) -> None:
    """Load the Configuration cog."""
    bot.add_cog(Configuration(bot))
