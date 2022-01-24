import logging

from disnake import Embed
from disnake.ext.commands import Cog, CommandError, Context, errors

from starbot.bot import StarBot
from starbot.constants import ACI

logger = logging.getLogger(__name__)


async def error_embed(ctx_or_inter: Context | ACI, message: str) -> None:
    """Creates an error embed and send it to ctx_or_inter."""
    await ctx_or_inter.send(embed=Embed(title="Error", description=message))


class ErrorHandler(Cog):
    """A general catch-all for errors occuring inside commands."""

    def __init__(self, bot: StarBot) -> None:
        """Initialize the ErrorHandler cog."""
        self.bot = bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError) -> None:
        """Handle errors in commands."""
        match error:
            case errors.CommandNotFound():
                logger.debug(f"Command not found: {ctx.command.name}")
            case errors.CommandOnCooldown():
                await error_embed(ctx, "This command is on cooldown.")
            case errors.CheckFailure():
                await error_embed(
                    ctx, "You do not have permission to use this command."
                )
            case errors.CommandInvokeError():
                logger.error(
                    f"Error while invoking command {ctx.command.name} by {ctx.author}: {error}"
                )
                await error_embed(
                    ctx,
                    "An error occurred while executing this command. Please let us know.",
                )
            case errors.MissingRequiredArgument():
                await error_embed(ctx, f"You are missing a required argument: {error}")
            case errors.BadArgument():
                await error_embed(
                    ctx, f"You have provided an invalid argument: {error}"
                )
            case errors.BadUnionArgument():
                await error_embed(
                    ctx, f"You have provided an invalid argument: {error}"
                )
            case errors.TooManyArguments():
                await error_embed(ctx, f"You have provided too many arguments: {error}")
            case errors.UserInputError():
                await error_embed(ctx, f"Your input seems off: {error}")

    @Cog.listener()
    async def on_slash_command_error(self, inter: ACI, error: CommandError) -> None:
        """Handle errors in slash commands."""
        match error:
            case errors.CommandOnCooldown():
                await error_embed(inter, "This command is on cooldown.")
            case errors.CheckFailure():
                await error_embed(
                    inter, "You do not have permission to use this command."
                )
            case errors.CommandInvokeError():
                logger.error(
                    f"Error while invoking command {inter.data.name} by {inter.author}: {error}"
                )
                await error_embed(
                    inter,
                    "An error occurred while executing this command. Please let us know.",
                )
            case errors.BadArgument():
                await error_embed(
                    inter, f"You have provided an invalid argument: {error}"
                )
            case errors.BadUnionArgument():
                await error_embed(
                    inter, f"You have provided an invalid argument: {error}"
                )
            case errors.UserInputError():
                await error_embed(inter, f"Your input seems off: {error}")


def setup(bot: StarBot) -> None:
    """Loads the error handler cog."""
    bot.add_cog(ErrorHandler(bot))
