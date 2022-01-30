from disnake.ext import commands
from disnake.ext.commands._types import Check

from starbot.constants import ACI


def is_guild_owner() -> Check:
    """Checks if the user is the guild owner."""

    async def check(inter: ACI) -> bool:
        return inter.author.id == inter.guild.owner_id

    return commands.check(check)
