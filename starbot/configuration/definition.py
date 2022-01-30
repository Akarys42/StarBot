from pathlib import Path

from yaml import safe_load

_DEFINITION_FILE = Path("starbot/configuration/config-definition.yaml")

with _DEFINITION_FILE.open() as file:
    DEFINITION = safe_load(file)
