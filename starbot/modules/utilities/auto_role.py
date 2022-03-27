from contextlib import suppress

from disnake import HTTPException, Member, Object
from disnake.ext.commands import Cog

from starbot.bot import StarBot


class AutoRole(Cog):
    """Automatically assign a role to new users."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @Cog.listener("on_member_update")
    async def assign_role(self, before: Member, after: Member) -> None:
        """Assign the role if a member passes verification."""
        if before.pending is False or after.pending is True:
            return

        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.utilities.auto_role:
            with suppress(HTTPException):
                await after.add_roles(Object(config.utilities.auto_role))


def setup(bot: StarBot) -> None:
    """Load the module."""
    bot.add_cog(AutoRole(bot))
