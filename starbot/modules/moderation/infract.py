import logging
from datetime import datetime, timedelta
from typing import Optional

import arrow
from dateutil.relativedelta import relativedelta
from disnake import Forbidden, User
from disnake.ext.commands import Cog, slash_command
from sqlalchemy import and_, select, update

from starbot.bot import StarBot
from starbot.checks import require_permission
from starbot.constants import ACI
from starbot.converters import autocomplete_relativedelta, convert_relativedelta
from starbot.models.infraction import InfractionModel, InfractionTypes
from starbot.utils.time import discord_timestamp

INFRACTIONS_WITH_DURATIONS = {InfractionTypes.MUTE}
HIDDEN_INFRACTIONS = {InfractionTypes.NOTE}
UNIQUE_INFRACTIONS = {InfractionTypes.MUTE, InfractionTypes.BAN}

ACTION_MESSAGE = {
    InfractionTypes.NOTE: "note",
    InfractionTypes.WARNING: "warned",
    InfractionTypes.MUTE: "muted",
    InfractionTypes.KICK: "kicked",
    InfractionTypes.BAN: "banned",
}

# Limitation due to the Discord API
MAX_TIMEOUT_DURATION = timedelta(days=28)

logger = logging.getLogger(__name__)


class InfractCog(Cog):
    """Module providing commands to infract users."""

    def __init__(self, bot: StarBot):
        self.bot = bot

    async def infract(
        self,
        inter: ACI,
        type_: InfractionTypes,
        user: User,
        moderator: User,
        reason: Optional[str],
        duration: Optional[relativedelta] = None,
    ) -> None:
        """Infract a user."""
        async with self.bot.Session() as session:
            # Make sure the duration is set appropriately
            if duration is not None and type_ not in INFRACTIONS_WITH_DURATIONS:
                raise ValueError(f"Infraction type {type_} does not support a duration")
            if duration is None and type_ in INFRACTIONS_WITH_DURATIONS:
                raise ValueError(f"Infraction type {type_} requires a duration")

            # Make sure we don't have an already active infraction
            if type_ in UNIQUE_INFRACTIONS:
                infractions = await session.execute(
                    select(InfractionModel).where(
                        and_(
                            InfractionModel.guild_id == inter.guild.id,
                            InfractionModel.user_id == user.id,
                            InfractionModel.type == type_,
                        )
                    )
                )

                active_infraction = None
                for infr in infractions:
                    if infr[0].active:
                        active_infraction = infr[0]
                        break

                if active_infraction is not None:
                    await inter.send(
                        f":x: That user already has an active infraction. "
                        f"See #{active_infraction.id}.",
                        ephemeral=True,
                    )
                    return

            # Convert duration to timedelta
            if duration is not None:
                now = arrow.utcnow()
                duration = now + duration - now

            # Apply the infraction
            try:
                match type_:
                    case InfractionTypes.NOTE:
                        pass
                    case InfractionTypes.WARNING:
                        pass
                    case InfractionTypes.KICK:
                        await inter.guild.kick(user, reason=reason)
                    case InfractionTypes.MUTE:
                        if duration > MAX_TIMEOUT_DURATION:
                            await inter.send(
                                f":x: Mute duration cannot exceed {MAX_TIMEOUT_DURATION.days} days "
                                "due to Discord API limitations.",
                                ephemeral=True,
                            )
                            return

                        await inter.guild.timeout(user, duration=duration, reason=reason)
                    case InfractionTypes.BAN:
                        await inter.guild.ban(user, reason=reason)
                    case _:
                        raise ValueError(f"Unknown infraction type {type_}")
            except Forbidden:
                await inter.send(
                    "The bot doesn't have the permission to apply this infraction.", ephemeral=True
                )
                return

            # Create the infraction
            infraction = InfractionModel(
                guild_id=inter.guild.id,
                user_id=user.id,
                moderator_id=moderator.id,
                type=type_,
                reason=reason,
                duration=duration,
                created_at=inter.created_at.replace(tzinfo=None),
            )
            session.add(infraction)
            await session.commit()

            # Send the infraction message
            duration_text = (
                f" until {discord_timestamp(datetime.now() + duration)}" if duration else ""
            )
            reason_text = f": {reason}" if reason else ""
            action_text = (
                f"{user.mention} has been {ACTION_MESSAGE[type_]}"
                if type_ not in HIDDEN_INFRACTIONS
                else f"{ACTION_MESSAGE[type_]} given to {user.mention}"
            )

            await inter.send(
                f":hammer: {action_text}" f"{duration_text}{reason_text} (#{infraction.id}).",
                ephemeral=type_ in HIDDEN_INFRACTIONS,
            )

    async def cancel_infraction(
        self, inter: ACI, user: User, moderator: User, type_: InfractionTypes
    ) -> None:
        """Cancel an infraction."""
        async with self.bot.Session() as session:
            # Make sure the infraction exists
            infractions = await session.execute(
                select(InfractionModel).where(
                    and_(
                        InfractionModel.guild_id == inter.guild.id,
                        InfractionModel.user_id == user.id,
                        InfractionModel.type == type_,
                    )
                )
            )

            active_infraction = None
            for infr in infractions:
                if infr[0].active:
                    active_infraction = infr[0]
                    break

            if active_infraction is None:
                await inter.send(
                    ":x: That user does not have an active infraction.",
                    ephemeral=True,
                )
                return
            logger.debug(f"Cancelling infraction {active_infraction.id}")

            # Cancel the infraction
            try:
                match type_:
                    case InfractionTypes.MUTE:
                        await inter.guild.timeout(user, duration=None)
                    case InfractionTypes.BAN:
                        await inter.guild.unban(user)
                    case _:
                        raise ValueError(f"Infraction type {type_} cannot be cancelled")
            except Forbidden:
                await inter.send(
                    "The bot doesn't have the permission to cancel this infraction.",
                    ephemeral=True,
                )
                return

            # Cancel the infraction
            await session.execute(
                update(InfractionModel)
                .where(InfractionModel.id == active_infraction.id)
                .values(cancelled=True)
            )
            await session.commit()

            # Send the cancellation message
            await inter.send(
                f":hammer: Un{ACTION_MESSAGE[type_]} {user.mention} (#{active_infraction.id}).",
                ephemeral=type_ in HIDDEN_INFRACTIONS,
            )

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def note(self, inter: ACI, user: User, message: str) -> None:
        """Put a moderator-only note on a user."""
        await self.infract(inter, InfractionTypes.NOTE, user, inter.author, message)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def warn(self, inter: ACI, user: User, reason: str) -> None:
        """Warn a user."""
        await self.infract(inter, InfractionTypes.WARNING, user, inter.author, reason)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def mute(
        self, inter: ACI, user: User, duration: str, reason: Optional[str] = None
    ) -> None:
        """Mute a user."""
        duration = convert_relativedelta(duration)
        await self.infract(inter, InfractionTypes.MUTE, user, inter.author, reason, duration)

    mute.autocomplete("duration")(autocomplete_relativedelta)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def kick(self, inter: ACI, user: User, reason: Optional[str] = None) -> None:
        """Kick a user."""
        await self.infract(inter, InfractionTypes.KICK, user, inter.author, reason)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def ban(self, inter: ACI, user: User, reason: Optional[str] = None) -> None:
        """Ban a user."""
        await self.infract(inter, InfractionTypes.BAN, user, inter.author, reason)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def unmute(self, inter: ACI, user: User) -> None:
        """Unmute a user."""
        await self.cancel_infraction(inter, user, inter.author, InfractionTypes.MUTE)

    @require_permission(role_id="moderation.perms.role", permissions="moderation.perms.discord")
    @slash_command()
    async def unban(self, inter: ACI, user: User) -> None:
        """Unban a user."""
        await self.cancel_infraction(inter, user, inter.author, InfractionTypes.BAN)


def setup(bot: StarBot) -> None:
    """Load the infract module."""
    bot.add_cog(InfractCog(bot))
