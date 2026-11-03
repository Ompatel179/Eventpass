import logging

from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


class BrokenSession:
    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("database is down"))


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_is_down(client):
    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="eventpass"):
        client.get("/health")
    assert "GET /health -> 200" in caplog.text