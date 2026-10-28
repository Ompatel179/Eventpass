from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class EventCreate(BaseModel):
    name: str = Field(min_length=1)
    starts_at: datetime
    location: str = Field(min_length=1)
    capacity: int = Field(gt=0)


class EventRead(EventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int

class RegistrationCreate(BaseModel):
    student_name: str = Field(min_length=1)
    student_email: EmailStr


class RegistrationRead(RegistrationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    created_at: datetime