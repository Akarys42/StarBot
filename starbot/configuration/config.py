from typing import Any

from starbot.configuration.definition import DEFINITION
from starbot.configuration.utils import get_dotted_path


class GuildConfig:
    """
    Represents one node inside the guild configuration.

    The structure is defined in the configuration definition file.
    Each node can be accessed using the dot notation.
    """

    def __init__(self, guild_id: int, entries: dict[str, str], prefix: str = "") -> None:
        self.guild_id = guild_id
        self.entries = entries
        self.prefix = prefix

    def __getattr__(self, item: str) -> Any:
        path = item if not self.prefix else f"{self.prefix}.{item}"

        if not (definition := get_dotted_path(DEFINITION, path)):
            raise AttributeError(f"The configuration entry '{path}' does not exist.")

        # If this has a `type` attribute then we know it is an entry
        if "type" in definition:
            value = self.entries[path] if path in self.entries else definition["default"]

            return self.convert_entry(value, definition)
        # If not, we can just nest another config
        else:
            return GuildConfig(self.guild_id, self.entries, path)

    def convert_entry(self, value: str, definition: dict) -> Any:
        """Convert the string value to the correct type."""
        match definition["type"]:
            case "int":
                return int(value)
            case "bool":
                return value.lower() in ["true", "t", "yes", "y", "1"]
            case "str":
                return value
            case _:
                raise ValueError(f"Unknown type '{definition['type']}'.")

    def __str__(self) -> str:
        return f"<GuildConfig(guild_id={self.guild_id})>"
