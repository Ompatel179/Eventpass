import pytest

def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to EventPass!"}

VALID_EVENT = {
    "name": "Career Fair",
    "starts_at": "2030-03-01T10:00:00Z",
    "location": "Busch Student Center",
    "capacity": 200,
}


def test_organizer_can_create_event(client, organizer_headers):
    response = client.post("/events", json=VALID_EVENT, headers=organizer_headers)
    assert response.status_code == 201
    assert response.json() == {"id": 1, **VALID_EVENT}


def test_student_cannot_create_event(client, student_headers):
    response = client.post("/events", json=VALID_EVENT, headers=student_headers)
    assert response.status_code == 403


def test_logged_out_cannot_create_event(client):
    response = client.post("/events", json=VALID_EVENT)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "field, value",
    [
        ("capacity", 0),
        ("capacity", -5),
        ("name", ""),
        ("location", ""),
        ("starts_at", "not-a-date"),
    ],
)
def test_create_event_rejects_invalid_fields(client, organizer_headers, field, value):
    payload = {**VALID_EVENT, field: value}
    response = client.post("/events", json=payload, headers=organizer_headers)
    assert response.status_code == 422


def test_create_event_requires_all_fields(client, organizer_headers):
    payload = {key: value for key, value in VALID_EVENT.items() if key != "location"}
    response = client.post("/events", json=payload, headers=organizer_headers)
    assert response.status_code == 422


def test_list_events_is_public_and_ordered(client, organizer_headers):
    client.post("/events", json={**VALID_EVENT, "name": "First"}, headers=organizer_headers)
    client.post("/events", json={**VALID_EVENT, "name": "Second"}, headers=organizer_headers)
    response = client.get("/events")
    assert response.status_code == 200
    assert [event["name"] for event in response.json()] == ["First", "Second"]


def test_get_event(client, event_id):
    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Event"


def test_get_missing_event_returns_404(client):
    response = client.get("/events/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}


def test_get_event_with_non_numeric_id_returns_422(client):
    assert client.get("/events/abc").status_code == 422

def test_event_time_without_timezone_is_rejected(client, organizer_headers):
    naive = {**VALID_EVENT, "starts_at": "2030-03-01T10:00:00"}
    response = client.post("/events", json=naive, headers=organizer_headers)
    assert response.status_code == 422


def test_event_time_is_returned_in_utc(client, organizer_headers):
    new_jersey = {**VALID_EVENT, "starts_at": "2030-03-01T10:00:00-05:00"}
    response = client.post("/events", json=new_jersey, headers=organizer_headers)
    assert response.json()["starts_at"] == "2030-03-01T15:00:00Z"