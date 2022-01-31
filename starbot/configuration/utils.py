from __future__ import annotations

from typing import Any

from starbot.configuration import config as configmodule
from starbot.configuration.definition import DEFINITION

MISSING = object()


def get_dotted_path(obj: dict, path: str) -> Any:
    """Returns the value of the given dotted path in the given nested structure."""
    if not path:
        return obj

    for key in path.split("."):
        obj = obj.get(key, MISSING)

        if obj is MISSING:
            return None

    return obj


def config_to_tree(config: configmodule.GuildConfig, path: str = "") -> dict:
    """Converts a GuildConfig object to a nested dictionary."""
    node = {}

    for key, value in get_dotted_path(DEFINITION, path).items():
        assert isinstance(value, dict)

        # If we have a key we can add it to our node.
        if "type" in value:
            node[key] = getattr(config, key)
        # Otherwise we recurse into it.
        else:
            new_path = f"{path}.{key}" if path else key
            node[key] = config_to_tree(getattr(config, key), new_path)

    return node
