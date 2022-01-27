from disnake.ext.commands import CommandError


class GuildNotConfiguredError(CommandError):
    """Raised when a guild is not configured."""
