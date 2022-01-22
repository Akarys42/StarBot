# Types supported by arrow.get
import datetime
from enum import Enum
from time import struct_time
from typing import Union

import arrow

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
