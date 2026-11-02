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




class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    user_id: int
    created_at: datetime


class TicketRead(RegistrationRead):
    qr_token: str

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

class CheckInRequest(BaseModel):
    qr_token: str = Field(min_length=1)


class CheckInRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    registration_id: int
    checked_in_by: int
    checked_in_at: datetime