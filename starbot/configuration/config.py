from typing import Any

from disnake import Permissions

from starbot.configuration.config_abc import ConfigABC
from starbot.configuration.definition import DEFINITION
from starbot.configuration.utils import get_dotted_path


class GuildConfig(ConfigABC):
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

    def get(self, key: str) -> Any:
        """Get the value of a configuration entry."""
        if not (definition := get_dotted_path(DEFINITION, key)):
            raise KeyError(f"The configuration entry '{key}' does not exist.")

        if key in self.entries:
            return self.convert_entry(self.entries[key], definition)
        else:
            return self.convert_entry(definition["default"], definition)

    def convert_entry(self, value: Any, definition: dict) -> Any:
        """Convert the string value to the correct type."""
        if value is None:
            return None

        match definition["type"]:
            case "role":
                return int(value)
            case "int":
                return int(value, base=0)
            case "bool":
                return value.lower() in ["true", "t", "yes", "y", "1"]
            case "discord_permission":
                return Permissions(**{value: True})
            case "choice":
                if value not in definition["choices"]:
                    raise ValueError(f"The value '{value}' is not in the list of choices.")
                return value
            case "str":
                return value
            case _:
                raise ValueError(f"Unknown type '{definition['type']}'.")

    def __str__(self) -> str:
        return f"<GuildConfig(guild_id={self.guild_id})>"
