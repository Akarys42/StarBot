from pathlib import Path

from yaml import safe_load

SPECIAL_TYPES = {
    "role": "int",
    "discord_permission": "str",
}

_DEFINITION_FILE = Path("starbot/configuration/config-definition.yaml")

with _DEFINITION_FILE.open() as file:
    DEFINITION = safe_load(file)