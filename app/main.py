import io

import qrcode
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, Registration, User
from app.schemas import (
    EventCreate,
    EventRead,
    TicketRead,
    RegistrationRead,
    Token,
    UserCreate,
    UserRead,
)
from app.security import create_access_token, hash_password, verify_password,get_current_user,require_organizer


app = FastAPI()


@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}

@app.post("/events", status_code=201, dependencies=[Depends(require_organizer)])
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketRead:
    if db.get(Event, event_id) is None:
        raise HTTPException(status_code=404, detail="Event not found")

    registration = Registration(event_id=event_id, user_id=current_user.id)
    db.add(registration)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You are already registered for this event")
    db.refresh(registration)
    return registration

@app.get("/events/{event_id}/registrations",dependencies=[Depends(require_organizer)],
)
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

@app.post("/auth/signup", status_code=201)
def signup(user: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    db_user = User(
        email=user.email.lower(),
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(db_user)
    return db_user

@app.post("/auth/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user), token_type="bearer")

@app.get("/auth/me")
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user

@app.get("/me/registrations")
def list_my_registrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TicketRead]:
    return list(
        db.scalars(
            select(Registration)
            .where(Registration.user_id == current_user.id)
            .order_by(Registration.id)
        )
    )


@app.get("/me/registrations/{registration_id}/qr")
def get_my_qr_code(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    registration = db.get(Registration, registration_id)
    if registration is None or registration.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Registration not found")

    image = qrcode.make(registration.qr_token)
    buffer = io.BytesIO()
    image.save(buffer)
    return Response(content=buffer.getvalue(), media_type="image/png")