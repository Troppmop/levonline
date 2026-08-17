from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.models.base import TimestampMixin, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.resident import Resident


class Room(UUIDPrimaryKey, TimestampMixin, table=True):
    """Physical room used to lay out the presence tracker by floor/position
    instead of alphabetically."""

    __tablename__ = "rooms"

    floor: int = Field(index=True)
    room_number: str = Field(index=True)
    # Sort position within a floor so the UI can render the tracker in the
    # same physical layout as the building, left-to-right / top-to-bottom.
    display_order: int = Field(default=0)
    capacity: int = Field(default=1)

    residents: list["Resident"] = Relationship(back_populates="room")
