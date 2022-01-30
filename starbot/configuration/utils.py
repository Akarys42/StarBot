from typing import Any

MISSING = object()


def get_dotted_path(obj: dict, path: str) -> Any:
    """Returns the value of the given dotted path in the given nested structure."""
    for key in path.split("."):
        obj = obj.get(key, MISSING)

        if obj is MISSING:
            return None

    return obj
