from typing import Any

from dateutil.relativedelta import relativedelta
from disnake.ext.commands import BadArgument

from starbot.utils.time import humanized_delta, parse_duration


def convert_relativedelta(argument: str) -> relativedelta:
    """Convert a duration string into a timedelta object."""
    if not (delta := parse_duration(argument)):
        raise BadArgument(f"Invalid duration: {argument}.")

    return delta


def autocomplete_relativedelta(_cog: Any, _inter: Any, argument: str) -> list:
    """Echo a human-readable duration string."""
    if not argument:
        return ["Start typing"]

    if not (delta := parse_duration(argument)):
        return ["Invalid duration"]

    return [humanized_delta(delta)]
