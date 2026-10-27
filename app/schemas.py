from datetime import datetime
from pydantic import BaseModel, Field

class EventCreate(BaseModel):
    name: str = Field(min_length=1)
    starts_at: datetime
    location: str = Field(min_length=1)
    capacity: int = Field(gt=0)


class EventRead(EventCreate):
    id: int