import json
from datetime import datetime
from pathlib import Path

from app.database import SessionLocal, engine
from app.models import Event, Registration, User
from app.security import hash_password

STUDENTS = 2000
ORGANIZERS = 50
PASSWORD = "loadtest-password"
OUTPUT = Path(__file__).parent / "data.json"


def main() -> None:
    assert engine.url.database == "eventpass_load", "Only seed the load-test database"

    hashed = hash_password(PASSWORD)
    with SessionLocal() as db:
        event = Event(
            name="Load Test Event",
            starts_at=datetime(2030, 1, 1, 18, 0),
            location="Load Test Hall",
            capacity=10000,
        )
        organizers = [
            User(email=f"organizer{i}@loadtest.example", hashed_password=hashed, role="organizer")
            for i in range(ORGANIZERS)
        ]
        students = [
            User(email=f"student{i}@loadtest.example", hashed_password=hashed)
            for i in range(STUDENTS)
        ]
        db.add(event)
        db.add_all(organizers + students)
        db.flush()

        registrations = [Registration(event_id=event.id, user_id=s.id) for s in students]
        db.add_all(registrations)
        db.flush()

        data = {
            "event_id": event.id,
            "password": PASSWORD,
            "organizer_emails": [u.email for u in organizers],
            "student_emails": [u.email for u in students],
            "qr_tokens": [r.qr_token for r in registrations],
        }
        db.commit()

    OUTPUT.write_text(json.dumps(data))
    print(f"Seeded {STUDENTS} students, {ORGANIZERS} organizers, event {data['event_id']}")


if __name__ == "__main__":
    main()
    