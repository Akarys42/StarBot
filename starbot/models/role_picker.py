from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from starbot.models._base import Base


class RolePickerModel(Base):
    """Represent a single role picker, clickable by users."""

    __tablename__ = "role_picker"

    id = Column(Integer, primary_key=True)

    guild_id = Column(BigInteger, ForeignKey("guild.guild_id"), nullable=False)
    channel_id = Column(BigInteger)
    message_id = Column(BigInteger)
    title = Column(String)

    guild = relationship("GuildModel")
    role_picker_entries = relationship("RolePickerEntryModel", back_populates="role_picker")


class RolePickerEntryModel(Base):
    """Represent a single role available in a picker."""

    __tablename__ = "role_picker_entry"

    id = Column(Integer, primary_key=True)

    picker_id = Column(BigInteger, ForeignKey("role_picker.id"), nullable=False)
    role_id = Column(BigInteger)
    message = Column(String)

    role_picker = relationship("RolePickerModel", back_populates="role_picker_entries")
