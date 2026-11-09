import json
import os
import random
from pathlib import Path

from locust import HttpUser, between, task

DATA = json.loads((Path(__file__).parent / "data.json").read_text())
EVENT_ID = DATA["event_id"]
PASSWORD = DATA["password"]
PACE = float(os.environ.get("PACE", "1"))

unused_tokens = list(DATA["qr_tokens"])
random.shuffle(unused_tokens)
student_emails = iter(DATA["student_emails"])
organizer_emails = iter(DATA["organizer_emails"])


def fake_ip() -> str:
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def log_in(user: HttpUser, email: str) -> None:
    user.client.headers["CF-Connecting-IP"] = fake_ip()
    response = user.client.post("/auth/login", data={"username": email, "password": PASSWORD})
    user.client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


class Student(HttpUser):
    weight = 4
    wait_time = between(1 * PACE, 3 * PACE)

    def on_start(self):
        log_in(self, next(student_emails))

    @task(3)
    def browse_events(self):
        self.client.get("/events")

    @task(1)
    def view_event(self):
        self.client.get(f"/events/{EVENT_ID}", name="/events/[id]")

    @task(2)
    def my_tickets(self):
        self.client.get("/me/registrations")


class Organizer(HttpUser):
    weight = 1
    wait_time = between(0.5 * PACE, 1 * PACE)

    def on_start(self):
        log_in(self, next(organizer_emails))

    @task
    def scan_ticket(self):
        if unused_tokens:
            token = unused_tokens.pop()
        else:
            token = random.choice(DATA["qr_tokens"])

        with self.client.post(
            f"/events/{EVENT_ID}/check-ins",
            json={"qr_token": token},
            name="/events/[id]/check-ins",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 409):
                response.success()