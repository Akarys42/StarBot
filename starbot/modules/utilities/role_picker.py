import logging
from typing import Optional

from disnake import (
    ButtonStyle,
    HTTPException,
    Member,
    MessageInteraction,
    Object,
    Role,
    SelectOption,
    TextChannel,
)
from disnake.ext.commands import Cog, slash_command
from disnake.ui import Button, Select, View
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from starbot.bot import StarBot
from starbot.checks import require_permission
from starbot.constants import ACI
from starbot.decorators import multi_autocomplete
from starbot.models.role_picker import RolePickerEntryModel, RolePickerModel

logger = logging.getLogger(__name__)


class RoleSelectDropdown(Select):
    """Dropdown used to manage a user's roles."""

    def __init__(
        self, *args, entries: list[RolePickerEntryModel] = (), member: Member = None, **kwargs
    ) -> None:
        # Construct our option dict
        user_roles = {role.id for role in member.roles}
        options = [
            SelectOption(
                label=entry.message, value=str(entry.role_id), default=entry.role_id in user_roles
            )
            for entry in entries
        ]

        self.__available = {entry.role_id for entry in entries}

        super().__init__(
            *args,
            **kwargs,
            options=options,
            min_values=0,
            max_values=len(options),
            placeholder="None",
        )

    async def callback(self, interaction: MessageInteraction) -> None:
        """Callback for when the user selects an option."""
        user_roles = {role.id for role in interaction.user.roles}
        selected = {int(option) for option in self.values}

        added_roles = (Object(role) for role in (selected - user_roles) & self.__available)
        removed_roles = (Object(role) for role in (user_roles - selected) & self.__available)

        try:
            await interaction.user.remove_roles(
                *removed_roles, reason=f"Used role picker in {interaction.channel}"
            )
            await interaction.user.add_roles(
                *added_roles, reason=f"Used role picker in {interaction.channel}"
            )
        except HTTPException as e:
            logger.debug(f"Failed to update roles for {interaction.user}: {e}")
            await interaction.response.edit_message(
                content=":x: Failed to update roles. Please contact a server admin.", view=None
            )
            return

        await interaction.response.edit_message(
            content=":white_check_mark: Roles updated!", view=None
        )


class RolePicker(Cog):
    """General informations about the bot."""

    def __init__(self, bot: StarBot) -> None:
        self.bot = bot

    @Cog.listener("on_message_interaction")
    async def display_role_picker(self, inter: MessageInteraction) -> None:
        """Display role picker if the custom ID matches."""
        if not inter.component.custom_id.startswith("luna_role_picker_"):
            return

        picker_id = int(inter.component.custom_id.removeprefix("luna_role_picker_"))

        async with self.bot.Session() as session:
            picker = (
                await session.execute(
                    select(RolePickerModel)
                    .options(selectinload(RolePickerModel.role_picker_entries))
                    .where(RolePickerModel.id == picker_id)
                )
            ).first()

        if picker is None:
            await inter.send(":x: Could not find a role picker with that ID.", ephemeral=True)
            return

        if len(picker[0].role_picker_entries) == 0:
            await inter.send(":x: This role picker has no entries.", ephemeral=True)
            return

        view = View()
        dropdown = RoleSelectDropdown(entries=picker[0].role_picker_entries, member=inter.author)
        view.add_item(dropdown)

        await inter.send("Please select your new roles in the dropdown.", view=view, ephemeral=True)

    @require_permission(role_id="config.perms.role", permissions="config.perms.discord")
    @slash_command(name="role-picker")
    async def role_picker(self, inter: ACI) -> None:
        """Manage role pickers inside the guild."""

    @role_picker.sub_command()
    async def create(self, inter: ACI, channel: TextChannel, title: str) -> None:
        """Create a new role picker."""
        async with self.bot.Session() as session:
            role_picker = RolePickerModel(
                guild_id=inter.guild.id, channel_id=channel.id, title=title
            )
            session.add(role_picker)
            await session.commit()

            # Fake view containing a button with a known ID
            view = View()
            button = Button(
                custom_id=f"luna_role_picker_{role_picker.id}",
                label=title,
                style=ButtonStyle.primary,
            )
            view.add_item(button)

            try:
                message = await channel.send(view=view)
            except HTTPException:
                # Clean up the role picker if the message could not be sent
                await session.delete(role_picker)
                await session.commit()

                await inter.send(
                    (
                        "Failed to create view. "
                        "Does the bot have the permission to post in this channel?"
                    ),
                    ephemeral=True,
                )

            # Set message ID now that we have it
            role_picker.message_id = message.id
            await session.commit()

        logger.debug(f"Created role picker {role_picker.id} in {inter.guild.name}")
        await inter.send(
            ":white_check_mark: Role picker created! Please now add roles using `/role-picker add`."
        )

    @role_picker.sub_command()
    async def add(self, inter: ACI, picker: int, role: Role, message: Optional[str] = None) -> None:
        """Add a role to a role picker."""
        if not message:
            message = role.name

        async with self.bot.Session() as session:
            picker_ = (
                await session.execute(
                    select(RolePickerModel)
                    .options(selectinload(RolePickerModel.role_picker_entries))
                    .where(RolePickerModel.id == picker)
                )
            ).first()

            if picker_ is None or picker_[0].guild_id != inter.guild.id:
                await inter.send(":x: Invalid role picker.", ephemeral=True)
                return

            if any(entry.role_id == role.id for entry in picker_[0].role_picker_entries):
                await inter.send(":x: Role already in picker.", ephemeral=True)
                return

            role_picker_entry = RolePickerEntryModel(
                picker_id=picker, role_id=role.id, message=message
            )
            session.add(role_picker_entry)
            await session.commit()

        # Warn the user if the bot may not be able to add that role
        warnings = ""

        if not inter.guild.me.guild_permissions.manage_roles:
            warnings += '\n:warning: The bot doesn\'t have the "Manage roles" permission.'
        if not inter.guild.me.top_role.position > role.position:
            warnings += "\n:warning: The bot's highest role is lower than the added role."

        await inter.send(":white_check_mark: Role added!" + warnings)

    @role_picker.sub_command()
    async def remove(self, inter: ACI, picker: int, role: Role) -> None:
        """Remove a role from a role picker."""
        async with self.bot.Session() as session:
            picker_ = (
                await session.execute(
                    select(RolePickerModel)
                    .options(selectinload(RolePickerModel.role_picker_entries))
                    .where(RolePickerModel.id == picker)
                )
            ).first()

            if picker_ is None or picker_[0].guild_id != inter.guild.id:
                await inter.send(":x: Invalid role picker.", ephemeral=True)
                return

            for entry in picker_[0].role_picker_entries:
                if entry.role_id == role.id:
                    await session.delete(entry)
                    await session.commit()
                    await inter.send(":white_check_mark: Role removed!")
                    return

        await inter.send(":x: Role not in picker.", ephemeral=True)

    @role_picker.sub_command()
    async def delete(self, inter: ACI, picker: int) -> None:
        """Permanently delete a role picker."""
        async with self.bot.Session() as session:
            picker_ = (
                await session.execute(
                    select(RolePickerModel)
                    .options(selectinload(RolePickerModel.role_picker_entries))
                    .where(RolePickerModel.id == picker)
                )
            ).first()

            if picker_ is None or picker_[0].guild_id != inter.guild.id:
                await inter.send(":x: Invalid role picker.", ephemeral=True)
                return

            for entry in picker_[0].role_picker_entries:
                await session.delete(entry)

            await session.delete(picker_[0])
            await session.commit()

        warnings = ""

        try:
            await inter.guild.get_channel(picker_[0].channel_id).get_partial_message(
                picker_[0].message_id
            ).delete()
        except (HTTPException, AttributeError):
            warnings += (
                "\n:warning: Failed to delete picker message. It may have been already deleted."
            )

        await inter.send(":white_check_mark: Role picker deleted." + warnings)

    @multi_autocomplete((add, "picker"), (remove, "picker"), (delete, "picker"))
    async def autocomplete_picker_id(self, inter: ACI, prefix: str) -> list:
        """Autocomplete role picker ID."""
        suggestions = {}

        async with self.bot.Session() as session:
            pickers = await session.stream(
                select(RolePickerModel).where(RolePickerModel.guild_id == inter.guild.id)
            )

            async for picker in pickers:
                if len(suggestions) == 25:
                    break

                if prefix in picker[0].title:
                    suggestions[picker[0].title] = picker[0].id

        return suggestions


def setup(bot: StarBot) -> None:
    """Load the module."""
    bot.add_cog(RolePicker(bot))
