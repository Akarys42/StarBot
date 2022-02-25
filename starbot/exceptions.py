from disnake.ext.commands import CommandError


class GuildNotConfiguredError(CommandError):
    """Raised when a guild is not configured."""


class InDmsError(CommandError):
    """Raised when a command is being executed in a DM."""
