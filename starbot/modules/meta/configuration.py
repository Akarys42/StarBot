from disnake.ext.commands import Cog, slash_command
from sqlalchemy import and_, select

from starbot.bot import StarBot
from starbot.checks import is_guild_owner
from starbot.configuration.definition import DEFINITION
from starbot.configuration.utils import get_dotted_path
from starbot.constants import ACI
from starbot.decorators import bypass_guild_configured_check
from starbot.models import ConfigEntryModel, GuildModel


class Configuration(Cog):
    """A cog for managing the per guild configuration of the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @bypass_guild_configured_check
    @slash_command()
    async def config(self, ctx: ACI) -> None:
        """Configure the bot for your guild."""
        pass

    @config.sub_command()
    async def set(self, inter: ACI, key: str, value: str) -> None:
        """Set a configuration key to a value."""
        # Check if the key is valid
        if not (definition := get_dotted_path(DEFINITION, key)):
            await inter.send(":x: Invalid configuration key.", ephemeral=True)
            return

        # Check if the value is valid
        config = await self.bot.get_config(inter)
        try:
            config.convert_entry(value, definition)
        except ValueError:
            await inter.send(":x: Invalid value.", ephemeral=True)
            return

        async with self.bot.Session() as session:
            # See if this config key exists.
            query = select(ConfigEntryModel).where(
                and_(ConfigEntryModel.key == key, ConfigEntryModel.guild_id == inter.guild.id)
            )
            entry = (await session.execute(query)).first()

            if entry is None:
                # If it doesn't, create it.
                entry = ConfigEntryModel(key=key, value=value, guild_id=inter.guild.id)
                session.add(entry)
            else:
                # If it does, update it.
                entry[0].value = value
            await session.commit()
        await inter.send(f":white_check_mark: Configuration updated: `{key}` set to `{value}`.")

    @bypass_guild_configured_check
    @is_guild_owner()
    @config.sub_command()
    async def setup(self, inter: ACI) -> None:
        """Bootstrap the bot."""
        async with self.bot.Session() as session:
            # Check if the guild isn't already configured
            if (
                await session.execute(
                    select(GuildModel).where(GuildModel.guild_id == inter.guild.id)
                )
            ).first() is not None:
                await inter.send(":x: This guild is already configured.", ephemeral=True)
                return

            guild = GuildModel(guild_id=inter.guild.id)

            session.add(guild)
            await session.commit()

        await inter.send(
            ":white_check_mark: This server has been configured! "
            "You can now use the `/config` command to adjust the configuration."
        )


def setup(bot: StarBot) -> None:
    """Load the Configuration cog."""
    bot.add_cog(Configuration(bot))
