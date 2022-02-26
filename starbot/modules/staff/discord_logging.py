import logging
from datetime import datetime
from typing import Optional

from disnake import (
    CategoryChannel,
    Embed,
    Emoji,
    Guild,
    GuildScheduledEvent,
    HTTPException,
    Member,
    PermissionOverwrite,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    Role,
    StageChannel,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
)
from disnake.abc import GuildChannel
from disnake.ext.commands import Cog
from disnake.utils import snowflake_time

from starbot.bot import StarBot
from starbot.utils.text import truncate
from starbot.utils.time import TimestampFormats, discord_timestamp

logger = logging.getLogger(__name__)

TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
GUILD_FIELDS = (
    "afk_channel",
    "afk_timeout",
    "banner",
    "description",
    "discovery_splash",
    "icon",
    "name",
    "mfa_level",
    "nsfw_level",
    "owner",
    "system_channel",
    "premium_subscription_count",
    "premium_tier",
    "verification_level",
)

MAX_EDIT_LENGTH = 2000
MESSAGE_LINK = "https://discordapp.com/channels/%d/%d/%d"
ARROW = "\N{HEAVY ROUND-TIPPED RIGHTWARDS ARROW}"

CHANNEL_TO_HUMAN_READABLE = {
    TextChannel: "text",
    VoiceChannel: "voice",
    CategoryChannel: None,  # Do not log new categories
    StageChannel: "stage",
}
PERM_EMOJIS = {
    True: "\N{LARGE GREEN SQUARE}",
    False: "\N{LARGE RED SQUARE}",
    None: "\N{WHITE LARGE SQUARE}",
}

EMPTY_PERM_OVERWRITE = PermissionOverwrite()


def _format_timestamp(timestamp: datetime) -> str:
    return (
        f"{discord_timestamp(timestamp, TimestampFormats.RELATIVE)} "
        f"({timestamp.strftime(TIMESTAMP_FORMAT)})"
    )


def _get_human_readable_channel_type(channel: GuildChannel) -> Optional[str]:
    for key, value in CHANNEL_TO_HUMAN_READABLE.items():
        if isinstance(channel, key):
            return value


class Logging(Cog):
    """Log various discord events related to the server."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    async def send_log_message(
        self,
        guild_id: int,
        channel_id: int,
        title: str,
        color: int,
        user: Optional[User | Member] = None,
        description: Optional[str] = None,
        extra_inline: bool = False,
        **extras: str,
    ) -> None:
        """Send a message to the logging channel."""
        # Fetch the log channel from the server
        if not (guild := self.bot.get_guild(guild_id)):
            logger.debug(f"Could not find guild {guild_id}. Dropping logging event.")
            return

        if not (channel := guild.get_channel(channel_id)):
            logger.debug(f"Could not find channel {channel_id}. Dropping logging event.")
            return

        # Do not log if the user in question is the bot
        if user and user == self.bot.user:
            logger.debug("Ignoring logging event because it originates from the bot.")
            return

        embed = Embed(title=title, color=color, timestamp=datetime.now())

        # Add the description if provided
        if description:
            embed.description = description

        # Add user name and profile picture if provided
        if user:
            embed.add_field(
                name="User", value=f"{user.mention} (`{user}`, `{user.id}`)", inline=False
            )
            embed.set_thumbnail(url=user.display_avatar.url)

        # Add any extra fields
        for key, value in extras.items():
            embed.add_field(
                name=key.replace("_", " ").capitalize(), value=value, inline=extra_inline
            )

        try:
            await channel.send(embed=embed)
        except HTTPException as e:
            logger.debug(f"Couldn't send logging message: {e}")

    @Cog.listener("on_member_join")
    async def log_member_joins(self, member: Member) -> None:
        """Log new members of the server."""
        config = await self.bot.get_config(guild_id=member.guild.id)

        if config.logging.channels.joins:
            await self.send_log_message(
                guild_id=member.guild.id,
                channel_id=config.logging.channels.joins,
                title="User joined",
                color=config.colors.success,
                user=member,
                created=_format_timestamp(member.created_at),
            )

    @Cog.listener("on_member_remove")
    async def log_member_removals(self, member: Member) -> None:
        """Log members leaving the server."""
        config = await self.bot.get_config(guild_id=member.guild.id)

        if config.logging.channels.joins:
            await self.send_log_message(
                guild_id=member.guild.id,
                channel_id=config.logging.channels.joins,
                title="User left",
                color=config.colors.warning,
                user=member,
                created=_format_timestamp(member.created_at),
                roles=", ".join(
                    role.mention
                    for role in member.roles
                    if role.id != member.guild.id  # Filter out the everyone role
                )
                or "None",  # If no roles, set to None
                joined=_format_timestamp(member.joined_at),
            )

    @Cog.listener("on_raw_message_delete")
    async def log_deleted_messages(self, payload: RawMessageDeleteEvent) -> None:
        """Log deleted messages."""
        config = await self.bot.get_config(guild_id=payload.guild_id)

        if not config.logging.channels.messages:
            return

        if payload.channel_id == config.logging.channels.messages:
            return

        # The message was cached
        if payload.cached_message:
            await self.send_log_message(
                guild_id=payload.guild_id,
                channel_id=config.logging.channels.messages,
                title="Message deleted",
                color=config.colors.warning,
                user=payload.cached_message.author,
                description=payload.cached_message.content,
                channel=(
                    f"{payload.cached_message.channel.mention} "
                    f"(`{payload.cached_message.channel}`, "
                    f"`{payload.cached_message.channel.id}`)"
                ),
                sent=_format_timestamp(payload.cached_message.created_at),
                message_id=(
                    f"[`{payload.message_id}`]"
                    f"({MESSAGE_LINK % (payload.guild_id, payload.channel_id, payload.message_id)})"
                ),
            )
        else:
            logger.debug("Message wasn't cached")

            if channel := self.bot.get_guild(payload.guild_id).get_channel(payload.channel_id):
                channel_text = f"{channel.mention} (`{channel}`, `{channel.id}`)"
            else:
                channel_text = f"<#{payload.channel_id}> (`unknown`, `{payload.channel_id}`)"

            await self.send_log_message(
                guild_id=payload.guild_id,
                channel_id=config.logging.channels.messages,
                title="Message deleted",
                color=config.colors.warning,
                user=None,  # We don't know who deleted the message
                description="Message content cannot be displayed",
                channel=channel_text,
                sent=_format_timestamp(snowflake_time(payload.message_id)),
                message_id=(
                    f"[`{payload.message_id}`]"
                    f"({MESSAGE_LINK % (payload.guild_id, payload.channel_id, payload.message_id)})"
                ),
            )

    @Cog.listener("on_raw_message_edit")
    async def log_edited_messages(self, payload: RawMessageUpdateEvent) -> None:
        """Log edited messages."""
        logger.debug(f"Message edit received: {payload.data}")

        if "content" not in payload.data:
            return

        config = await self.bot.get_config(guild_id=payload.guild_id)

        if not config.logging.channels.messages or not config.logging.log.messages:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if channel := guild.get_channel(payload.channel_id):
            channel_text = f"{channel.mention} (`{channel}`, `{channel.id}`)"
        else:
            channel_text = f"<#{payload.channel_id}> (`unknown`, `{payload.channel_id}`)"

        if "author" in payload.data and "id" in payload.data["author"]:
            user = guild.get_member(int(payload.data["author"]["id"]))
        else:
            user = None

        if payload.cached_message:
            before = payload.cached_message.content

            if before == payload.data["content"]:
                return
        else:
            before = "Cannot display previous content"

        if "edited_timestamp" not in payload.data:
            return

        edited_timestamp = datetime.fromisoformat(payload.data["edited_timestamp"])

        await self.send_log_message(
            guild_id=payload.guild_id,
            channel_id=config.logging.channels.messages,
            title="Message edited",
            color=config.colors.info,
            user=user,
            description=(
                f"**Before:**\n{truncate(before, MAX_EDIT_LENGTH)}"
                f"\n\n**After:**\n{truncate(payload.data['content'], MAX_EDIT_LENGTH)}"
            ),
            channel=channel_text,
            sent=_format_timestamp(snowflake_time(payload.message_id)),
            edited=_format_timestamp(edited_timestamp),
            message_id=(
                f"[`{payload.message_id}`]"
                f"({MESSAGE_LINK % (payload.guild_id, payload.channel_id, payload.message_id)})"
            ),
        )

    @Cog.listener("on_member_update")
    async def log_nickname_changes(self, before: Member, after: Member) -> None:
        """Log the nickname changes of a member."""
        if before.nick == after.nick:
            return

        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.members:
            await self.send_log_message(
                guild_id=before.guild.id,
                channel_id=config.logging.channels.members,
                title="Nickname changed",
                color=config.colors.info,
                user=before,
                before=f"`{before.nick}`",
                after=f"`{after.nick}`",
            )

    @Cog.listener("on_member_update")
    async def log_verified_members(self, before: Member, after: Member) -> None:
        """Log whenever a member passes verification."""
        if before.pending is False or after.pending is True:
            return

        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.joins:
            await self.send_log_message(
                guild_id=before.guild.id,
                channel_id=config.logging.channels.joins,
                title="Member passed verification",
                color=config.colors.info,
                user=before,
                joined=_format_timestamp(before.joined_at),
            )

    @Cog.listener("on_member_update")
    async def log_member_roles(self, before: Member, after: Member) -> None:
        """Log updated roles for a member."""
        if set(before.roles) == set(after.roles):
            return

        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.members:
            fields = {}

            removed_roles = set(before.roles) - set(after.roles)
            added_roles = set(after.roles) - set(before.roles)

            if removed_roles:
                fields["roles_removed"] = ", ".join(role.mention for role in removed_roles)

            if added_roles:
                fields["roles_added"] = ", ".join(role.mention for role in added_roles)

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.guild.id,
                    channel_id=config.logging.channels.members,
                    title="Member roles updated",
                    color=config.colors.info,
                    user=before,
                    **fields,
                )

    @Cog.listener("on_member_ban")
    async def log_banned_member(self, guild: Guild, user: User) -> None:
        """Log users getting banned."""
        config = await self.bot.get_config(guild_id=guild.id)

        if config.logging.channels.members:
            await self.send_log_message(
                guild_id=guild.id,
                channel_id=config.logging.channels.members,
                title="User banned",
                color=config.colors.danger,
                user=user,
            )

    @Cog.listener("on_member_unban")
    async def log_unbanned_member(self, guild: Guild, user: User) -> None:
        """Log users getting unbanned."""
        config = await self.bot.get_config(guild_id=guild.id)

        if config.logging.channels.members:
            await self.send_log_message(
                guild_id=guild.id,
                channel_id=config.logging.channels.members,
                title="User unbanned",
                color=config.colors.success,
                user=user,
            )

    @Cog.listener("on_guild_channel_create")
    async def log_new_channels(self, channel: GuildChannel) -> None:
        """Log the creation of a new channel."""
        config = await self.bot.get_config(guild_id=channel.guild.id)

        if config.logging.channels.server:
            if human_readable_name := _get_human_readable_channel_type(channel):
                title = f"{human_readable_name.title()} Channel Created"
            else:
                return

            await self.send_log_message(
                guild_id=channel.guild.id,
                channel_id=config.logging.channels.server,
                title=title,
                color=config.colors.success,
                user=None,
                description=f"{channel.mention} (`{channel}`, `{channel.id}`)",
            )

    @Cog.listener("on_guild_channel_delete")
    async def log_deleted_channels(self, channel: GuildChannel) -> None:
        """Log the deletion of a channel."""
        config = await self.bot.get_config(guild_id=channel.guild.id)

        if config.logging.channels.server:
            if human_readable_name := _get_human_readable_channel_type(channel):
                title = f"{human_readable_name.title()} Channel Deleted"
            else:
                return

            await self.send_log_message(
                guild_id=channel.guild.id,
                channel_id=config.logging.channels.server,
                title=title,
                color=config.colors.danger,
                user=None,
                description=f"`#{channel}` (`{channel.id}`)",
            )

    @Cog.listener("on_guild_channel_update")
    async def log_updated_channels(self, before: GuildChannel, after: GuildChannel) -> None:
        """
        Log the updates of a channel.

        The following fields are checked:
        - name
        - topic
        - position
        - nsfw
        - category
        - slowmode_delay (if TextChannel)
        - overwrites
        """
        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.server:
            if human_readable_name := _get_human_readable_channel_type(before):
                title = f"{human_readable_name.title()} channel updated"
            else:
                return

            fields = {}
            field_names = ["name", "topic", "position", "nsfw", "category"]

            if isinstance(before, TextChannel):
                field_names.append("slowmode_delay")

            for field_name in field_names:
                if getattr(before, field_name) != getattr(after, field_name):
                    fields[field_name] = (
                        f"`{getattr(before, field_name)}` "
                        f"{ARROW} "
                        f"`{getattr(after, field_name)}`"
                    )

            # Check if the overwrites changed
            all_subjects = set(before.overwrites.keys()).union(set(after.overwrites.keys()))
            for subject in all_subjects:
                perms_before = dict(before.overwrites.get(subject, EMPTY_PERM_OVERWRITE))
                perms_after = dict(after.overwrites.get(subject, EMPTY_PERM_OVERWRITE))

                if perms_before != perms_after:
                    changes = []

                    for perm, perm_before, perm_after in zip(
                        perms_before.keys(), perms_before.values(), perms_after.values()
                    ):
                        if perm_before != perm_after:
                            changes.append(
                                f"{perm.replace('_', ' ').capitalize()}: "
                                f"{PERM_EMOJIS[perm_before]} "
                                f"{ARROW} "
                                f"{PERM_EMOJIS[perm_after]}"
                            )

                    subject_type = "role" if isinstance(subject, Role) else "member"
                    fields[f"overwrites_for_{subject_type}_{subject}"] = "\n".join(changes)

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.guild.id,
                    channel_id=config.logging.channels.server,
                    title=title,
                    color=config.colors.info,
                    user=None,
                    channel=f"{after.mention} (`{after}`, `{after.id}`)",
                    **fields,
                )

    @Cog.listener("on_thread_join")
    async def log_created_threads(self, thread: Thread) -> None:
        """Log the creation of a new thread."""
        # There is no way at the API level to distinguish between a thread
        # creation and the bot joining the thread, so we have to check if the
        # bot already joined the thread, in which case we assume it isn't
        # a thread creation.
        if thread.me:
            logger.debug("Assuming thread join because the bot is in the thread")
            return

        config = await self.bot.get_config(guild_id=thread.guild.id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=thread.guild.id,
                channel_id=config.logging.channels.server,
                title="Thread created",
                color=config.colors.success,
                user=None,
                description=f"{thread.mention} (`{thread}`, `{thread.id}`)",
                parent_channel=f"{thread.parent.mention} (`{thread.parent}`, `{thread.parent.id}`)",
            )

    @Cog.listener("on_thread_delete")
    async def log_deleted_threads(self, thread: Thread) -> None:
        """Log the deletion of threads."""
        config = await self.bot.get_config(guild_id=thread.guild.id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=thread.guild.id,
                channel_id=config.logging.channels.server,
                title="Thread deleted",
                color=config.colors.danger,
                user=None,
                description=f"`#{thread}` (`{thread.id}`)",
                parent_channel=f"{thread.parent.mention} (`{thread.parent}`, `{thread.parent.id}`)",
            )

    @Cog.listener("on_thread_update")
    async def log_updated_threads(self, before: Thread, after: Thread) -> None:
        """
        Log the updates of a thread.

        The following fields are being checked:
        - name
        - slowmode_delay
        - archived
        - locked
        """
        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.server:
            fields = {}
            field_names = ["name", "slowmode_delay", "archived", "locked"]

            for field_name in field_names:
                if getattr(before, field_name) != getattr(after, field_name):
                    fields[field_name] = (
                        f"`{getattr(before, field_name)}` "
                        f"{ARROW} "
                        f"`{getattr(after, field_name)}`"
                    )

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.guild.id,
                    channel_id=config.logging.channels.server,
                    title="Thread updated",
                    color=config.colors.info,
                    user=None,
                    description=f"{after.mention} (`{after}`, `{after.id}`)",
                    parent_channel=(
                        f"{after.parent.mention} " f"(`{after.parent}`, `{after.parent.id}`)"
                    ),
                    **fields,
                )

    @Cog.listener("on_guild_update")
    async def log_updated_guild(self, before: Guild, after: Guild) -> None:
        """
        Log when the guild is being updated.

        The following fields are being checked:
        - afk_channel
        - afk_timeout
        - banner
        - description
        - discovery_splash
        - icon
        - name
        - mfa_level
        - nsfw_level
        - owner
        - system_channel
        - premium_subscription_count
        - premium_tier
        - verification_level
        """
        config = await self.bot.get_config(guild_id=before.id)

        if config.logging.channels.server:
            fields = {}

            for field in GUILD_FIELDS:
                if getattr(before, field) != getattr(after, field):
                    fields[field] = (
                        f"`{getattr(before, field)}` " f"{ARROW} " f"`{getattr(after, field)}`"
                    )

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.id,
                    channel_id=config.logging.channels.server,
                    title="Guild updated",
                    color=config.colors.info,
                    user=None,
                    **fields,
                )

    @Cog.listener("on_guild_role_create")
    async def log_created_roles(self, role: Role) -> None:
        """Log the creation of a new role."""
        config = await self.bot.get_config(guild_id=role.guild.id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=role.guild.id,
                channel_id=config.logging.channels.server,
                title="Role created",
                color=config.colors.success,
                user=None,
                description=f"{role.mention} (`{role}`, `{role.id}`)",
            )

    @Cog.listener("on_guild_role_delete")
    async def log_deleted_roles(self, role: Role) -> None:
        """Log the deletion of roles."""
        config = await self.bot.get_config(guild_id=role.guild.id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=role.guild.id,
                channel_id=config.logging.channels.server,
                title="Role deleted",
                color=config.colors.danger,
                user=None,
                description=f"`{role}` (`{role.id}`)",
            )

    @Cog.listener("on_guild_role_update")
    async def log_updated_roles(self, before: Role, after: Role) -> None:
        """
        Log the updates of roles.

        The following fields are checked:
        - mentionable
        - name
        - color
        - hoist
        - position
        - permissions
        """
        config = await self.bot.get_config(guild_id=before.guild.id)

        if config.logging.channels.server:
            fields = {}

            for field_name in ("name", "hoist", "mentionable", "position"):
                if getattr(before, field_name) != getattr(after, field_name):
                    fields[field_name] = (
                        f"`{getattr(before, field_name)}` "
                        f"{ARROW} "
                        f"`{getattr(after, field_name)}`"
                    )

            # Manually add the color so we can convert it to hex
            if before.color != after.color:
                if before.color.value != after.color.value:
                    fields["role_color"] = (
                        f"`{hex(before.color.value) if before.color.value != 0 else None}` "
                        f"{ARROW} "
                        f"`{hex(after.color.value) if after.color.value != 0 else None}`"
                    )

            # Check if the permission changed
            if before.permissions != after.permissions:
                changes = []

                perms_before = dict(before.permissions)
                perms_after = dict(after.permissions)

                for perm, perm_before, perm_after in zip(
                    perms_before.keys(), perms_before.values(), perms_after.values()
                ):
                    if perm_before != perm_after:
                        changes.append(
                            f"{perm.replace('_', ' ').capitalize()}: "
                            f"{PERM_EMOJIS[perm_before]} "
                            f"{ARROW} "
                            f"{PERM_EMOJIS[perm_after]}"
                        )

                fields["permissions"] = "\n".join(changes)

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.guild.id,
                    channel_id=config.logging.channels.server,
                    title="Role updated",
                    color=config.colors.info,
                    user=None,
                    role=f"{after.mention} (`{after}`, `{after.id}`)",
                    **fields,
                )

    @Cog.listener("on_guild_emojis_update")
    async def log_updated_emojis(
        self, guild: Guild, before: list[Emoji], after: list[Emoji]
    ) -> None:
        """
        Log the updates of emojis.

        Addition and deletion of emojis are logged, along with renames.
        """
        config = await self.bot.get_config(guild_id=guild.id)

        if config.logging.channels.server:
            fields = {}

            added_emojis = set(after) - set(before)
            removed_emojis = set(before) - set(after)

            renamed_emojis = []

            for old_emoji in before:
                for new_emoji in after:
                    if old_emoji.id == new_emoji.id:
                        if old_emoji.name != new_emoji.name:
                            renamed_emojis.append((old_emoji, new_emoji))
                        break

            if added_emojis:
                fields["created"] = "\n".join(
                    f"{emoji} (`{emoji.name}`, `{emoji.id}`)" for emoji in added_emojis
                )

            if removed_emojis:
                fields["deleted"] = "\n".join(
                    f"`{emoji.name}` (`{emoji.id}`)" for emoji in removed_emojis
                )

            if renamed_emojis:
                fields["renamed"] = "\n".join(
                    f"{new_emoji} `{old_emoji.name}` {ARROW} `{new_emoji.name}` (`{old_emoji.id}`)"
                    for old_emoji, new_emoji in renamed_emojis
                )

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=guild.id,
                    channel_id=config.logging.channels.server,
                    title="Emojis updated",
                    color=config.colors.info,
                    user=None,
                    **fields,
                )

    @Cog.listener("on_guild_scheduled_event_create")
    async def log_created_scheduled_event(self, event: GuildScheduledEvent) -> None:
        """Log the creation of scheduled events."""
        config = await self.bot.get_config(guild_id=event.guild_id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=event.guild_id,
                channel_id=config.logging.channels.server,
                title="Scheduled event created",
                color=config.colors.success,
                user=None,
                name=event.name,
                event_description=event.description,
                start_time=_format_timestamp(event.scheduled_start_time),
                end_time=_format_timestamp(event.scheduled_end_time)
                if event.scheduled_end_time
                else None,
                channel=f"{event.channel.mention} (`{event.channel}`, `{event.channel.id}`)",
                id=str(event.id),
            )

    @Cog.listener("on_guild_scheduled_event_delete")
    async def log_deleted_scheduled_event(self, event: GuildScheduledEvent) -> None:
        """Log the deletion of scheduled events."""
        config = await self.bot.get_config(guild_id=event.guild_id)

        if config.logging.channels.server:
            await self.send_log_message(
                guild_id=event.guild_id,
                channel_id=config.logging.channels.server,
                title="Scheduled event deleted",
                color=config.colors.danger,
                user=None,
                name=event.name,
                event_description=event.description,
                start_time=_format_timestamp(event.scheduled_start_time),
                end_time=_format_timestamp(event.scheduled_end_time)
                if event.scheduled_end_time
                else None,
                channel=f"{event.channel.mention} (`{event.channel}`, `{event.channel.id}`)",
                id=str(event.id),
            )

    @Cog.listener("on_guild_scheduled_event_update")
    async def log_updated_scheduled_event(
        self, before: GuildScheduledEvent, after: GuildScheduledEvent
    ) -> None:
        """Log the updates of scheduled events."""
        config = await self.bot.get_config(guild_id=before.guild_id)

        if config.logging.channels.server:
            fields = {}

            for field in ("name", "description", "channel"):
                if getattr(before, field) != getattr(after, field):
                    fields[field] = f"{getattr(after, field)} {ARROW} {getattr(before, field)}"

            if before.scheduled_start_time != after.scheduled_start_time:
                fields["start_time"] = (
                    f"{_format_timestamp(before.scheduled_start_time)} "
                    f"{ARROW} "
                    f"{_format_timestamp(after.scheduled_start_time)}"
                )

            if before.scheduled_end_time != after.scheduled_end_time:
                fields["end_time"] = (
                    f"{_format_timestamp(before.scheduled_end_time)} "
                    f"{ARROW} "
                    f"{_format_timestamp(after.scheduled_end_time)}"
                )

            if len(fields) > 0:
                await self.send_log_message(
                    guild_id=before.guild_id,
                    channel_id=config.logging.channels.server,
                    title="Scheduled event updated",
                    color=config.colors.info,
                    user=None,
                    event=after.name,
                    **fields,
                    id=str(after.id),
                )


def setup(bot: StarBot) -> None:
    """Load the logging cog."""
    bot.add_cog(Logging(bot))
