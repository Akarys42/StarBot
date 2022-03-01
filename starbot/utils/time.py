import datetime
import re
from enum import Enum
from time import struct_time
from typing import Optional, Union

import arrow

# Types supported by arrow.get
from dateutil.relativedelta import relativedelta

# Part of the code in this file is based on the code from python-discord/bot
# See their license in the LICENSE-THIRD-PARTY file.


DURATION_REGEX = re.compile(
    r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
    r"((?P<months>\d+?) ?(months|month) ?)?"
    r"((?P<weeks>\d+?) ?(weeks|week) ?)?"
    r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
    r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
    r"((?P<minutes>\d+?) ?(minutes|minute|M|m) ?)?"
    r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
)

Timestamp = Union[
    arrow.Arrow,
    datetime.datetime,
    datetime.date,
    struct_time,
    int,  # POSIX timestamp
    float,  # POSIX timestamp
    str,  # ISO 8601-formatted string
    tuple[int, int, int],  # ISO calendar tuple
]

TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"


def format_timestamp(timestamp: datetime) -> str:
    """Format a timestamp for logging, with a delta and the UTC time."""
    return (
        f"{discord_timestamp(timestamp, TimestampFormats.RELATIVE)} "
        f"({timestamp.strftime(TIMESTAMP_FORMAT)})"
    )


class TimestampFormats(Enum):
    """
    Represents the different formats possible for Discord timestamps.

    Examples are given in epoch time.
    """

    DATE_TIME = "f"  # January 1, 1970 1:00 AM
    DAY_TIME = "F"  # Thursday, January 1, 1970 1:00 AM
    DATE_SHORT = "d"  # 01/01/1970
    DATE = "D"  # January 1, 1970
    TIME = "t"  # 1:00 AM
    TIME_SECONDS = "T"  # 1:00:00 AM
    RELATIVE = "R"  # 52 years ago


def discord_timestamp(
    timestamp: Timestamp, format_: TimestampFormats = TimestampFormats.DATE_TIME
) -> str:
    """
    Format a timestamp as a Discord-flavored Markdown timestamp.

    `timestamp` can be any type supported by the single-arg `arrow.get()`, except for a `tzinfo`.
    """
    timestamp = int(arrow.get(timestamp).timestamp())
    return f"<t:{timestamp}:{format_.value}>"


def parse_duration(duration: str) -> Optional[relativedelta]:
    """Try to parse a text duration."""
    if not (match := DURATION_REGEX.match(duration)):
        return None

    content = {key: int(value) for key, value in match.groupdict().items() if value}

    return relativedelta(**content)


def humanized_delta(delta: relativedelta) -> str:
    """Return a human-readable string representation of a relativedelta."""
    units = (
        ("year", delta.years),
        ("month", delta.months),
        ("day", delta.days),
        ("hour", delta.hours),
        ("minute", delta.minutes),
        ("second", delta.seconds),
    )
    parts = []

    for unit, value in units:
        if value:
            parts.append(f"{value} {unit}{'s' if value > 1 else ''}")

    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
