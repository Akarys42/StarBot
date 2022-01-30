from sqlalchemy import BigInteger, Column, Integer
from sqlalchemy.orm import relationship

from starbot.models._base import Base


class GuildModel(Base):
    """Represent a known discord guild."""

    __tablename__ = "guild"

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True)

    config_entries = relationship("ConfigEntryModel", back_populates="guild")

    def __repr__(self) -> str:
        return f"<GuildModel(id={self.id}, discord_id={self.guild_id})>"
