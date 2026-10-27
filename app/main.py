from fastapi import FastAPI
from datetime import datetime
from pydantic import BaseModel,Field

class EventCreate(BaseModel):
    name:str = Field(min_length=1)
    starts_at: datetime
    location:str
    capacity:int = Field(gt=0)

app = FastAPI()

@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}
@app.post("/events", status_code=201)
def create_event(event:EventCreate) -> EventCreate:
    return event