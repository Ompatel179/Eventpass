from fastapi import FastAPI,HTTPException
from datetime import datetime
from pydantic import BaseModel,Field

class EventCreate(BaseModel):
    name:str = Field(min_length=1)
    starts_at: datetime
    location:str
    capacity:int = Field(gt=0)
class EventRead(EventCreate):
    id:int


app = FastAPI()
events: list[EventRead] = []

@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}

@app.post("/events", status_code=201)
def create_event(event:EventCreate) -> EventRead:
    new_event = EventRead(id=len(events)+1, **event.model_dump())
    events.append(new_event)
    return new_event

@app.get("/events")
def list_events() -> list[EventRead]:
    return events

@app.get("/events/{event_id}")
def get_event(event_id: int) -> EventRead:
    for event in events:
        if event.id == event_id:
            return event
    raise HTTPException(status_code=404, detail="Event not found")