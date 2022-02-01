from abc import ABC, abstractmethod
from typing import Any


class ConfigABC(ABC):
    """Base interface for the GuildConfig class."""

    guild_id: int
    entries: dict[str, str]
    prefix: str = ""

    @abstractmethod
    def __init__(self, guild_id: int, entries: dict[str, str], prefix: str = "") -> None:
        ...

    @abstractmethod
    def convert_entry(self, value: str, definition: dict) -> Any:
        """Convert the string value to the correct type."""
        ...
