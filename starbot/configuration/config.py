class GuildConfig:
    """TODO."""

    def __init__(self, guild_id: int, entries: dict[str, str]) -> None:
        self.guild_id = guild_id

    def __str__(self) -> str:
        return f"<GuildConfig(guild_id={self.guild_id})>"
