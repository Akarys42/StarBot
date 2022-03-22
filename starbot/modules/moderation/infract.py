import logging
from datetime import datetime, timedelta
from http.client import HTTPException
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
from starbot.modules.moderation._constants import (
    HIDDEN_INFRACTIONS,
    INFRACTION_NAME,
    INFRACTIONS_WITH_DURATIONS,
    UNIQUE_INFRACTIONS,
)
from starbot.modules.moderation.discord_logging import Logging, format_timestamp
from starbot.utils.lock import argument_lock
from starbot.utils.time import TimestampFormats, discord_timestamp, humanized_delta

EMOJI_APPLIED = "\N{HAMMER}"
EMOJI_CANCELLED = "\N{HAMMER AND WRENCH}"
EMOJI_DM_SUCCESS = "\N{ENVELOPE WITH DOWNWARDS ARROW ABOVE}"

# Limitation due to the Discord API
MAX_TIMEOUT_DURATION = timedelta(days=28)

logger = logging.getLogger(__name__)


class Infract(Cog):
    """Module providing commands to infract users."""

    def __init__(self, bot: StarBot):
        self.bot = bot

    @argument_lock(3)  # user
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
        config = await self.bot.get_config(inter)

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
            dateutil_duration = duration
            if duration is not None:
                now = arrow.utcnow()
                duration = now + duration - now

            if type_ not in HIDDEN_INFRACTIONS:
                # We try to check early if the bot should be able to apply the infraction or not
                # so we don't send a DM if it can't be applied
                can_continue = True

                match type_:
                    case InfractionTypes.MUTE:
                        can_continue = inter.guild.me.guild_permissions.moderate_members
                    case InfractionTypes.KICK:
                        can_continue = inter.guild.me.guild_permissions.kick_members
                    case InfractionTypes.BAN:
                        can_continue = inter.guild.me.guild_permissions.ban_members

                if not can_continue:
                    await inter.send(
                        ":x: The bot doesn't have the permission to apply this infraction.",
                        ephemeral=True,
                    )
                    return

                # Send a DM to the user
                message = f"**You have received a {INFRACTION_NAME[type_]} in {inter.guild.name}**"
                if reason:
                    message += f" for the following reason: {reason}"

                if duration:
                    message += "\n\nThis infraction expires " + discord_timestamp(
                        datetime.utcnow() + duration, TimestampFormats.RELATIVE
                    )

                if config.moderation.messages.dm_description:
                    message += "\n\n" + config.moderation.messages.dm_description
                else:
                    message += "."

                dm_sent = True
                try:
                    await user.send(message)
                except (HTTPException, Forbidden):
                    dm_sent = False

            logging_module: Optional[Logging] = self.bot.get_cog("Logging")

            # Apply the infraction
            try:
                match type_:
                    case InfractionTypes.NOTE:
                        pass
                    case InfractionTypes.WARNING:
                        pass
                    case InfractionTypes.KICK:
                        await inter.guild.kick(user, reason=reason)

                        if logging_module:
                            logging_module.ignore_event("user_left", user.id)
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

                        if logging_module:
                            logging_module.ignore_event("user_left", user.id)
                    case _:
                        raise ValueError(f"Unknown infraction type {type_}")
            except Forbidden:
                await inter.send(
                    ":x: The bot doesn't have the permission to apply this infraction.",
                    ephemeral=True,
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
                dm_sent=dm_sent,
            )
            session.add(infraction)
            await session.commit()

            # Send the infraction message
            emoji_text = EMOJI_DM_SUCCESS if type_ not in HIDDEN_INFRACTIONS and dm_sent else ""
            action_text = f"Applied {INFRACTION_NAME[type_]} to {user.mention}"
            duration_text = (
                f" until {discord_timestamp(infraction.created_at + duration)}" if duration else ""
            )
            reason_text = f": {reason}" if reason else ""

            await inter.send(
                (
                    f"{emoji_text} {EMOJI_APPLIED} {action_text}"
                    f"{duration_text}{reason_text} (#{infraction.id})."
                ),
                ephemeral=type_ in HIDDEN_INFRACTIONS,
            )

            # Send a message to the log channel
            if config.logging.channels.moderation is not None and logging_module:
                extras = (
                    {
                        "duration": f"{humanized_delta(dateutil_duration)}",
                        "expires": format_timestamp(infraction.created_at + duration),
                    }
                    if duration
                    else {}
                )

                await logging_module.send_log_message(
                    inter.guild.id,
                    config.logging.channels.moderation,
                    f"{INFRACTION_NAME[type_].capitalize()} applied",
                    config.colors.warning,
                    user,
                    moderator=f"{moderator.mention} (`{moderator}`, `{moderator.id}`)",
                    reason=reason,
                    **extras,
                )

    @argument_lock(3)  # user
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
                    f":x: The user {user.mention} does not have an active infraction.",
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
                    ":x: The bot doesn't have the permission to cancel this infraction.",
                    ephemeral=True,
                )
                return

            # Send a DM to the user
            if active_infraction.type not in HIDDEN_INFRACTIONS:
                dm_sent = True

                try:
                    await user.send(
                        f"Your {INFRACTION_NAME[type_]} in {inter.guild.name} has been cancelled."
                    )
                except (HTTPException, Forbidden):
                    dm_sent = False

            # Cancel the infraction
            await session.execute(
                update(InfractionModel)
                .where(InfractionModel.id == active_infraction.id)
                .values(cancelled=True)
            )
            await session.commit()

            # Send the cancellation message
            emoji_text = EMOJI_DM_SUCCESS if type_ not in HIDDEN_INFRACTIONS and dm_sent else ""
            await inter.send(
                f"{emoji_text} {EMOJI_CANCELLED} {INFRACTION_NAME[type_].capitalize()} cancelled "
                f"for {user.mention} (#{active_infraction.id}).",
                ephemeral=type_ in HIDDEN_INFRACTIONS,
            )

            # Send a message to the log channel
            config = await self.bot.get_config(inter)
            if config.logging.channels.moderation is not None and (
                logging_module := self.bot.get_cog("Logging")
            ):
                await logging_module.send_log_message(
                    inter.guild.id,
                    config.logging.channels.moderation,
                    f"{INFRACTION_NAME[type_].capitalize()} cancelled",
                    config.colors.success,
                    user,
                    moderator=f"{moderator.mention} (`{moderator}`, `{moderator.id}`)",
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
    bot.add_cog(Infract(bot))
