from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
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

class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "student_email", name="uq_registrations_event_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    student_name: Mapped[str]
    student_email: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())    