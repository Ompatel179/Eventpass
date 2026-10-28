from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("name <> ''", name="events_name_check"),
        CheckConstraint("location <> ''", name="events_location_check"),
        CheckConstraint("capacity > 0", name="events_capacity_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    starts_at: Mapped[datetime]
    location: Mapped[str]
    capacity: Mapped[int]