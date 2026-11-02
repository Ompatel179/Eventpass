import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
assert "test" in TEST_DATABASE_URL, "Refusing to run tests against a non-test database"

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE check_ins, registrations, events, users RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def student_headers(client) -> dict[str, str]:
    client.post("/auth/signup", json={"email": "student@test.com", "password": "studentpass123"})
    response = client.post(
        "/auth/login", data={"username": "student@test.com", "password": "studentpass123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def organizer_headers(client, db) -> dict[str, str]:
    db.add(
        User(
            email="organizer@test.com",
            hashed_password=hash_password("organizerpass123"),
            role="organizer",
        )
    )
    db.commit()
    response = client.post(
        "/auth/login", data={"username": "organizer@test.com", "password": "organizerpass123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def event_id(client, organizer_headers) -> int:
    response = client.post(
        "/events",
        json={
            "name": "Test Event",
            "starts_at": "2030-01-01T18:00:00",
            "location": "Room 101",
            "capacity": 50,
        },
        headers=organizer_headers,
    )
    return response.json()["id"]


@pytest.fixture
def ticket(client, student_headers, event_id) -> dict:
    response = client.post(f"/events/{event_id}/registrations", headers=student_headers)
    return response.json()