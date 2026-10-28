from datetime import datetime
from pydantic import BaseModel, Field , ConfigDict

class EventCreate(BaseModel):
    name: str = Field(min_length=1)
    starts_at: datetime
    location: str = Field(min_length=1)
    capacity: int = Field(gt=0)


class EventRead(EventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int