from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, Registration
from app.schemas import EventCreate, EventRead, RegistrationCreate, RegistrationRead



app = FastAPI()


@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}

@app.post("/events", status_code=201)
def create_event(event: EventCreate, db: Session = Depends(get_db)) -> EventRead:
    db_event = Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.get("/events")
def list_events(db: Session = Depends(get_db)) -> list[EventRead]:
    return list(db.scalars(select(Event).order_by(Event.id)))

@app.get("/events/{event_id}")
def get_event(event_id: int, db: Session = Depends(get_db)) -> EventRead:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/events/{event_id}/registrations", status_code=201)
def create_registration(
    event_id: int,
    registration: RegistrationCreate,
    db: Session = Depends(get_db),
) -> RegistrationRead:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    db_registration = Registration(event_id=event_id, **registration.model_dump())
    db.add(db_registration)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This email is already registered for this event",
        )
    db.refresh(db_registration)
    return db_registration

@app.get("/events/{event_id}/registrations")
def list_registrations(event_id: int, db: Session = Depends(get_db)) -> list[RegistrationRead]:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return list(
        db.scalars(
            select(Registration)
            .where(Registration.event_id == event_id)
            .order_by(Registration.id)
        )
    )