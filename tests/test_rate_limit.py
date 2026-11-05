import redis

from app.main import app
from app.rate_limit import get_redis
from tests.conftest import test_redis


def attempt_login(client, email="nobody@test.com", headers=None):
    return client.post(
        "/auth/login",
        data={"username": email, "password": "wrongpassword"},
        headers=headers,
    )


def test_login_blocked_after_five_attempts_for_same_email(client):
    for _ in range(5):
        assert attempt_login(client).status_code == 401

    response = attempt_login(client)
    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= 60


def test_email_limit_does_not_block_other_accounts(client):
    for _ in range(6):
        attempt_login(client)

    assert attempt_login(client, email="someone-else@test.com").status_code == 401


def test_login_blocked_after_twenty_attempts_from_same_ip(client):
    attacker = {"CF-Connecting-IP": "203.0.113.1"}
    for i in range(20):
        assert attempt_login(client, f"user{i}@test.com", attacker).status_code == 401

    assert attempt_login(client, "user20@test.com", attacker).status_code == 429

    other_person = {"CF-Connecting-IP": "203.0.113.2"}
    assert attempt_login(client, "user21@test.com", other_person).status_code == 401


def test_signup_blocked_after_ten_attempts_from_same_ip(client):
    for i in range(10):
        response = client.post(
            "/auth/signup", json={"email": f"new{i}@test.com", "password": "password123"}
        )
        assert response.status_code == 201

    response = client.post(
        "/auth/signup", json={"email": "new10@test.com", "password": "password123"}
    )
    assert response.status_code == 429


def test_counter_always_has_an_expiry(client):
    attempt_login(client)
    assert 0 < test_redis.ttl("rate:login:email:nobody@test.com") <= 60


def test_login_still_works_when_redis_is_down(client):
    broken = redis.Redis(host="localhost", port=1, socket_connect_timeout=0.1)
    app.dependency_overrides[get_redis] = lambda: broken

    assert attempt_login(client).status_code == 401