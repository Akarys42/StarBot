import enum
from datetime import datetime

import sqlalchemy
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Interval, String
from sqlalchemy.orm import relationship

from starbot.models._base import Base


class InfractionTypes(enum.Enum):
    """Enum for the different types of infractions."""

    NOTE = 1
    WARNING = 2
    MUTE = 3
    KICK = 4
    BAN = 5


class InfractionModel(Base):
    """An infraction committed by a user."""

    __tablename__ = "infraction"

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey("guild.guild_id"), nullable=False)

    user_id = Column(BigInteger)
    moderator_id = Column(BigInteger)

    created_at = Column(DateTime, nullable=False)
    duration = Column(Interval, nullable=True, default=None)
    reason = Column(String, nullable=True)
    type = Column(sqlalchemy.Enum(InfractionTypes))
    cancelled = Column(Boolean, nullable=False, default=False)

    dm_sent = Column(Boolean)

    guild = relationship("GuildModel")

    @property
    def active(self) -> bool:
        """
        Whether the infraction is still active.

        False if the infraction has been cancelled or has expired.
        """
        return not self.cancelled and (
            not self.duration or (datetime.now() < self.created_at + self.duration)
        )

    def __str__(self) -> str:
        return f"<InfractionModel {self.id}>"
