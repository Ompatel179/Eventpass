import redis

from app.main import app
from app.models import Event
from app.rate_limit import get_redis
from tests.conftest import test_redis

NEW_EVENT = {
    "name": "Second Event",
    "starts_at": "2030-02-01T18:00:00Z",
    "location": "Room 202",
    "capacity": 30,
}


def change_name_behind_cache(db, event_id):
    db.get(Event, event_id).name = "Changed directly in the database"
    db.commit()


def test_event_list_second_read_comes_from_cache(client, db, event_id):
    first = client.get("/events").json()
    change_name_behind_cache(db, event_id)
    assert client.get("/events").json() == first


def test_single_event_second_read_comes_from_cache(client, db, event_id):
    first = client.get(f"/events/{event_id}").json()
    change_name_behind_cache(db, event_id)
    assert client.get(f"/events/{event_id}").json() == first


def test_new_event_appears_immediately(client, organizer_headers, event_id):
    assert len(client.get("/events").json()) == 1
    client.post("/events", json=NEW_EVENT, headers=organizer_headers)
    assert len(client.get("/events").json()) == 2


def test_cached_entries_always_expire(client, event_id):
    client.get("/events")
    client.get(f"/events/{event_id}")

    list_keys = list(test_redis.scan_iter("cache:events:list:*"))
    assert len(list_keys) == 1
    assert 0 < test_redis.ttl(list_keys[0]) <= 60
    assert 0 < test_redis.ttl(f"cache:event:{event_id}") <= 60


def test_missing_event_is_not_cached(client):
    assert client.get("/events/999").status_code == 404
    assert test_redis.exists("cache:event:999") == 0


def test_events_still_work_when_redis_is_down(client, event_id):
    broken = redis.Redis(host="localhost", port=1, socket_connect_timeout=0.1)
    app.dependency_overrides[get_redis] = lambda: broken

    assert client.get("/events").status_code == 200
    assert client.get(f"/events/{event_id}").status_code == 200