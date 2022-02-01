from typing import Optional

from disnake import Member, Permissions
from disnake.ext import commands
from disnake.ext.commands._types import Check

from starbot.configuration.config import GuildConfig
from starbot.constants import ACI


def require_permission(
    *, role_id: Optional[int | str], permissions: Optional[Permissions | str]
) -> Check:
    """
    Check that the user either has the role or the permissions provided.

    Passing in a string parameter will look up that field from the guild's configuration.
    """

    async def check(inter: ACI) -> bool:
        config: GuildConfig = await inter.bot.get_config(inter)
        _role_id = role_id
        _permissions = permissions

        if not isinstance(inter.author, Member):
            return False

        if _role_id is not None:
            if isinstance(_role_id, str):
                _role_id = config.get(_role_id)

            if _role_id in [role.id for role in inter.author.roles]:
                return True

        if permissions is not None:
            if isinstance(_permissions, str):
                _permissions = config.get(_permissions)

            if inter.channel.permissions_for(inter.author).is_superset(_permissions):
                return True
        return False

    return commands.check(check)


def is_guild_owner() -> Check:
    """Checks if the user is the guild owner."""

    async def check(inter: ACI) -> bool:
        return inter.author.id == inter.guild.owner_id

    return commands.check(check)
