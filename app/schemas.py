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

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str