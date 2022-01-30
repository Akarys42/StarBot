from pathlib import Path
from typing import Any

from yaml import safe_load

DEFINITION_FILE = Path("starbot/configuration/config-definition.yaml")
with DEFINITION_FILE.open() as file:
    DEFINITION = safe_load(file)


def _get_dotted_path(obj: dict, path: str) -> Any:
    """Returns the value of the given dotted path in the given nested structure."""
    for key in path.split("."):
        obj = obj[key]

    return obj


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

        if not (definition := _get_dotted_path(DEFINITION, path)):
            raise AttributeError(f"The configuration entry '{path}' does not exist.")

        # If this has a `type` attribute then we know it is an entry
        if "type" in definition:
            value = self.entries[path] if path in self.entries else definition["default"]

            return self._convert_entry(value, definition)
        # If not, we can just nest another config
        else:
            return GuildConfig(self.guild_id, self.entries, path)

    def _convert_entry(self, value: str, definition: dict) -> Any:
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
