from typing import Literal, Optional

from dateutil.relativedelta import relativedelta
from disnake import Embed, User
from disnake.ext.commands import Cog, slash_command
from sqlalchemy import and_, select

from starbot.bot import StarBot
from starbot.checks import require_permission
from starbot.constants import ACI
from starbot.models.infraction import InfractionModel, InfractionTypes
from starbot.modules.moderation._constants import INFRACTION_NAME
from starbot.utils.time import format_timestamp, humanized_delta

CANCELLABLE_INFRACTIONS = {InfractionTypes.MUTE, InfractionTypes.BAN}

RED_CIRCLE = "\N{LARGE RED CIRCLE}"
GREEN_CIRCLE = "\N{LARGE GREEN CIRCLE}"
YELLOW_CIRCLE = "\N{LARGE YELLOW CIRCLE}"

INFRACTION_LITERAL = Literal["note", "warn", "mute", "kick", "ban", "all"]


class Infractions(Cog):
    """Module used to manage infractions."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    def try_format_user(self, user_id: int) -> str:
        """Try to format a user ID by resolving it, if possible."""
        if user := self.bot.get_user(user_id):
            return f"{user.mention} (`{user}`, `{user.id}`)"
        return f"<@{user_id}> (`{user_id}`)"

    def format_infraction(self, infr: InfractionModel, include_id: bool = True) -> str:
        """Format an infraction into a nice human readable string."""
        if infr.type in CANCELLABLE_INFRACTIONS:
            emoji = GREEN_CIRCLE if infr.active else RED_CIRCLE
        else:
            emoji = YELLOW_CIRCLE

        id_text = f" (`{infr.id}`)" if include_id else ""

        if infr.duration:
            delta = humanized_delta(relativedelta(infr.created_at + infr.duration, infr.created_at))
            duration_text = f"**Duration**: {delta}\n"
        else:
            duration_text = ""

        cancelled_text = "\n*Cancelled early*" if infr.cancelled else ""

        return (
            f"{emoji} **{INFRACTION_NAME[infr.type].capitalize()}**{id_text}\n"
            f"**Reason**: {infr.reason}\n"
            f"**User**: {self.try_format_user(infr.user_id)}\n"
            f"**Moderator**: {self.try_format_user(infr.moderator_id)}\n"
            f"**Created at**: {format_timestamp(infr.created_at)}\n"
            f"{duration_text}"
            f"**DM sent**: {infr.dm_sent}"
            f"{cancelled_text}"
        )

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def infraction(self, inter: ACI) -> None:
        """Group of commands used to manage infractions."""
        pass

    @infraction.sub_command()
    async def get(self, inter: ACI, id: int) -> None:
        """Get an infraction by its ID."""
        config = await self.bot.get_config(inter)

        async with self.bot.Session() as session:
            infraction = await session.execute(
                select(InfractionModel).where(InfractionModel.id == id)
            )

            infraction = infraction.first()

            if not infraction:
                await inter.send(f":x: No infraction found with that ID ({id}).", ephemeral=True)
                return

            infraction = infraction[0]

            if infraction.guild_id != inter.guild.id:
                await inter.send(
                    ":x: That infraction doesn't belong to this guild.", ephemeral=True
                )
                return

            await inter.send(
                embed=Embed(
                    title=f"Infraction {id}",
                    description=self.format_infraction(infraction, False),
                    color=config.colors.info,
                )
            )

    @infraction.sub_command()
    async def search(
        self,
        inter: ACI,
        user: Optional[User] = None,
        reason: Optional[str] = None,
        type: INFRACTION_LITERAL = "all",
    ) -> None:
        """Search for infractions by user, type, or reason."""
        if user is None and reason is None:
            await inter.send(":x: You must specify either a user or a reason.", ephemeral=True)
            return

        await inter.response.defer()

        predicates = [InfractionModel.guild_id == inter.guild.id]

        if user:
            predicates.append(InfractionModel.user_id == user.id)
        if reason:
            predicates.append(InfractionModel.reason.contains(reason))
        if type != "all":
            predicates.append(InfractionModel.type == InfractionTypes[type.upper()])

        async with self.bot.Session() as session:
            query = await session.execute(select(InfractionModel).where(and_(*predicates)))

            infractions = query.fetchall()

        if not infractions:
            await inter.send(":x: No infractions found.", ephemeral=True)
            return

        description = "\n\n".join(self.format_infraction(infr[0]) for infr in infractions)
        config = await self.bot.get_config(inter)

        await inter.send(
            embed=Embed(
                title="Search results",
                description=description,
                color=config.colors.info,
            )
        )


def setup(bot: StarBot) -> None:
    """Loads the infractions module."""
    bot.add_cog(Infractions(bot))
