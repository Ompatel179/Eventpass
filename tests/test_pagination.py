def create_events(client, headers, count):
    for i in range(count):
        client.post(
            "/events",
            json={
                "name": f"Event {i + 1}",
                "starts_at": "2030-01-01T18:00:00Z",
                "location": "Room 101",
                "capacity": 50,
            },
            headers=headers,
        )


def event_ids(client, query):
    return [event["id"] for event in client.get(f"/events?{query}").json()]


def test_default_page_size_is_50(client, organizer_headers):
    create_events(client, organizer_headers, 51)
    assert len(client.get("/events").json()) == 50


def test_limit_and_offset_walk_through_pages(client, organizer_headers):
    create_events(client, organizer_headers, 5)

    assert event_ids(client, "limit=2&offset=0") == [1, 2]
    assert event_ids(client, "limit=2&offset=2") == [3, 4]
    assert event_ids(client, "limit=2&offset=4") == [5]
    assert event_ids(client, "limit=2&offset=10") == []


def test_new_event_shows_up_on_cached_pages(client, organizer_headers):
    create_events(client, organizer_headers, 5)
    assert event_ids(client, "limit=2&offset=4") == [5]

    create_events(client, organizer_headers, 1)
    assert event_ids(client, "limit=2&offset=4") == [5, 6]


def test_bad_page_values_are_rejected(client):
    assert client.get("/events?limit=0").status_code == 422
    assert client.get("/events?limit=101").status_code == 422
    assert client.get("/events?offset=-1").status_code == 422


def test_registrations_are_paginated(
    client, organizer_headers, student_headers, other_student_headers, event_id
):
    client.post(f"/events/{event_id}/registrations", headers=student_headers)
    client.post(f"/events/{event_id}/registrations", headers=other_student_headers)
    url = f"/events/{event_id}/registrations"

    first = client.get(f"{url}?limit=1&offset=0", headers=organizer_headers).json()
    second = client.get(f"{url}?limit=1&offset=1", headers=organizer_headers).json()

    assert len(first) == 1 and len(second) == 1
    assert first[0]["id"] != second[0]["id"]