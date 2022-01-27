from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from starbot.models._base import Base


class ConfigEntryModel(Base):
    """An entry in the config table of a specific guild."""

    __tablename__ = "config_entry"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("guild.id"))

    key = Column(String(255))
    value = Column(String(255))

    guild = relationship("GuildModel", back_populates="config_entries")

    def __str__(self) -> str:
        return f"<ConfigEntry(id={self.id}, guild_id={self.guild_id}, {self.key}={self.value}>"
