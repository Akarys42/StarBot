import logging

from disnake import Embed
from disnake.ext.commands import Cog, CommandError, errors

from starbot.bot import StarBot
from starbot.constants import ACI
from starbot.exceptions import GuildNotConfiguredError, InDmsError

logger = logging.getLogger(__name__)


class ErrorHandler(Cog):
    """A general catch-all for errors occurring inside commands."""

    def __init__(self, bot: StarBot) -> None:
        """Initialize the ErrorHandler cog."""
        self.bot = bot

    async def error_embed(self, inter: ACI, message: str, ephemeral: bool = False) -> None:
        """Creates an error embed and send it to ctx_or_inter."""
        try:
            config = await self.bot.get_config(inter)
            color = config.colors.danger
        except GuildNotConfiguredError:
            color = 0xED4245

        await inter.send(
            embed=Embed(title="Error", description=message, color=color), ephemeral=ephemeral
        )

    @Cog.listener()
    async def on_slash_command_error(self, inter: ACI, error: CommandError) -> None:
        """Handle errors in slash commands."""
        match error:
            # Starbot errors
            case GuildNotConfiguredError():
                if not inter.guild.owner_id == inter.author.id:
                    await inter.send(
                        ":x: This guild is not configured yet. Please contact the server owner.",
                        ephemeral=True,
                    )
                else:
                    await inter.send(
                        ":x: This guild is not configured yet. Please run `/config setup`.",
                        ephemeral=True,
                    )
            case InDmsError():
                await inter.send(":x: This bot can only be used in a server.", ephemeral=True)
            # Disnake errors
            case errors.CommandOnCooldown():
                await self.error_embed(inter, "This command is on cooldown.", ephemeral=True)
            case errors.CheckFailure():
                await self.error_embed(
                    inter, "You do not have permission to use this command.", ephemeral=True
                )
            case errors.CommandInvokeError():
                logger.error(
                    f"Error while invoking command {inter.data.name} by {inter.author}: {error}",
                    exc_info=error.original,
                )
                await self.error_embed(
                    inter,
                    "An error occurred while executing this command. Please let us know.",
                )
            case errors.BadArgument():
                await self.error_embed(
                    inter, f"You have provided an invalid argument: {error}", ephemeral=True
                )
            case errors.BadUnionArgument():
                await self.error_embed(
                    inter, f"You have provided an invalid argument: {error}", ephemeral=True
                )
            case errors.UserInputError():
                await self.error_embed(inter, f"Your input seems off: {error}", ephemeral=True)


def setup(bot: StarBot) -> None:
    """Loads the error handler cog."""
    bot.add_cog(ErrorHandler(bot))
