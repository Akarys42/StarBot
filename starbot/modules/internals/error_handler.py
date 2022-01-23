import logging

from disnake import Embed
from disnake.ext.commands import Cog, CommandError, Context, errors

from starbot.bot import StarBot

logger = logging.getLogger(__name__)


async def error_embed(ctx: Context, message: str) -> None:
    await ctx.send(embed=Embed(title="Error", description=message))


class ErrorHandler(Cog):
    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError) -> None:
        error_class = type(error)
        match error_class:
            case errors.CommandNotFound:
                pass
            case errors.CommandOnCooldown:
                await error_embed(ctx, "This command is on cooldown.")
            case
