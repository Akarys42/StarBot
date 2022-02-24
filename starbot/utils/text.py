def truncate(text: str, max_length: int) -> str:
    """Return text truncated to the max_length character if needed."""
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text
