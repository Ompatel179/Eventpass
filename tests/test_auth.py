from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import SECRET_KEY


def make_token(secret: str, expires_in_minutes: int) -> str:
    payload = {
        "sub": "1",
        "role": "organizer",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_signup_creates_student(client):
    response = client.post("/auth/signup", json={"email": "new@test.com", "password": "newpass123"})
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "student"
    assert "password" not in body
    assert "hashed_password" not in body


def test_signup_cannot_choose_role(client):
    response = client.post(
        "/auth/signup",
        json={"email": "sneaky@test.com", "password": "sneakypass123", "role": "organizer"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "student"


def test_signup_duplicate_email_is_case_insensitive(client):
    client.post("/auth/signup", json={"email": "dup@test.com", "password": "duppass123"})
    response = client.post("/auth/signup", json={"email": "DUP@Test.com", "password": "duppass123"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "longenough123"},
        {"email": "short@test.com", "password": "short"},
        {"email": "missing@test.com"},
    ],
)
def test_signup_rejects_invalid_input(client, payload):
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 422


def test_login_returns_bearer_token(client):
    client.post("/auth/signup", json={"email": "login@test.com", "password": "loginpass123"})
    response = client.post(
        "/auth/login", data={"username": "login@test.com", "password": "loginpass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_errors_do_not_reveal_which_part_was_wrong(client):
    client.post("/auth/signup", json={"email": "real@test.com", "password": "realpass123"})
    wrong_password = client.post(
        "/auth/login", data={"username": "real@test.com", "password": "wrongpass123"}
    )
    unknown_email = client.post(
        "/auth/login", data={"username": "ghost@test.com", "password": "realpass123"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_returns_current_user(client, student_headers):
    response = client.get("/auth/me", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "student@test.com"


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_valid_handmade_token_is_accepted(client, student_headers):
    token = make_token(SECRET_KEY, 30)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_forged_token_is_rejected(client, student_headers):
    token = make_token("not-the-real-secret-but-long-enough-for-hs256", 30)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client, student_headers):
    token = make_token(SECRET_KEY, -1)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_role_claim_in_token_is_not_trusted(client, student_headers):
    token = make_token(SECRET_KEY, 30)
    response = client.post(
        "/events",
        json={"name": "Hack", "starts_at": "2030-01-01T18:00:00", "location": "X", "capacity": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

def test_token_for_deleted_user_is_rejected(client):
    token = make_token(SECRET_KEY, 30)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401