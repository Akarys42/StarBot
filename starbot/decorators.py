from disnake.ext.commands import InvokableSlashCommand


def bypass_guild_configured_check(func: callable) -> callable:
    """Decorator to skip the config check."""
    func.__starbot_bypass_config_check__ = True
    return func


def multi_autocomplete(*autocompletes: tuple[InvokableSlashCommand, str]) -> callable:
    """
    Decorator used to use the same autocomplete for multiple commands.

    The arguments should be tuples of (slash_command, argument_to_complete).
    """

    def decorator(func: callable) -> callable:
        for command, argument in autocompletes:
            command.autocomplete(argument)(func)
        return func

    return decorator
