import secrets
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

def generate_qr_token() -> str:
    return secrets.token_urlsafe(16)

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
        UniqueConstraint("event_id", "user_id", name="uq_registrations_event_user"),
        UniqueConstraint("qr_token", name="uq_registrations_qr_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="registrations_user_id_fkey"), index=True
    )
    qr_token: Mapped[str] = mapped_column(default=generate_qr_token)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('organizer', 'student')", name="users_role_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str]
    role: Mapped[str] = mapped_column(server_default="student")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())    

class CheckIn(Base):
    __tablename__ = "check_ins"
    __table_args__ = (
        UniqueConstraint("registration_id", name="uq_check_ins_registration"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    registration_id: Mapped[int] = mapped_column(
        ForeignKey("registrations.id", name="check_ins_registration_id_fkey")
    )
    checked_in_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="check_ins_checked_in_by_fkey")
    )
    checked_in_at: Mapped[datetime] = mapped_column(server_default=func.now())