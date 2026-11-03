import io
import csv
import logging
import time

import qrcode
from fastapi import Depends, FastAPI, HTTPException, Response,Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func,select,text
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, Registration, User, CheckIn
from app.schemas import (
    EventCreate,
    EventRead,
    TicketRead,
    RegistrationRead,
    Token,
    UserCreate,
    UserRead,
    CheckInRequest,
    CheckInRead,
    AttendanceRead,
)
from app.security import create_access_token, hash_password, verify_password,get_current_user,require_organizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("eventpass")

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

def get_event_or_404(event_id: int, db: Session) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.get("/")
def home() -> dict[str,str]:
    return {"message": "Welcome to EventPass!"}

@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok"}

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
    get_event_or_404(event_id, db)

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
    get_event_or_404(event_id, db)

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

@app.post("/events/{event_id}/check-ins", status_code=201)
def check_in(
    event_id: int,
    body: CheckInRequest,
    staff: User = Depends(require_organizer),
    db: Session = Depends(get_db),
) -> CheckInRead:
    registration = db.scalar(
        select(Registration).where(Registration.qr_token == body.qr_token)
    )
    if registration is None or registration.event_id != event_id:
        raise HTTPException(status_code=404, detail="Ticket not valid for this event")

    check_in_record = CheckIn(registration_id=registration.id, checked_in_by=staff.id)
    db.add(check_in_record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ticket already checked in")
    db.refresh(check_in_record)
    return check_in_record

@app.get("/events/{event_id}/attendance", dependencies=[Depends(require_organizer)])
def get_attendance(event_id: int, db: Session = Depends(get_db)) -> AttendanceRead:
    event = get_event_or_404(event_id, db)
    registered = db.scalar(
        select(func.count())
        .select_from(Registration)
        .where(Registration.event_id == event_id)
    )
    checked_in = db.scalar(
        select(func.count())
        .select_from(CheckIn)
        .join(Registration, CheckIn.registration_id == Registration.id)
        .where(Registration.event_id == event_id)
    )
    return AttendanceRead(
        event_id=event.id,
        capacity=event.capacity,
        registered=registered,
        checked_in=checked_in,
    )

@app.get("/events/{event_id}/attendees.csv", dependencies=[Depends(require_organizer)])
def export_attendees(event_id: int, db: Session = Depends(get_db)) -> Response:
    get_event_or_404(event_id, db)
    rows = db.execute(
        select(User.email, Registration.created_at, CheckIn.checked_in_at)
        .select_from(Registration)
        .join(User, Registration.user_id == User.id)
        .outerjoin(CheckIn, CheckIn.registration_id == Registration.id)
        .where(Registration.event_id == event_id)
        .order_by(Registration.id)
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "registered_at", "checked_in", "checked_in_at"])
    for email, registered_at, checked_in_at in rows:
        writer.writerow([
            email,
            registered_at.isoformat(),
            "yes" if checked_in_at else "no",
            checked_in_at.isoformat() if checked_in_at else "",
        ])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="event_{event_id}_attendees.csv"'},
    )