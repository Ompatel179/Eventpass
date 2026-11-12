def test_student_can_register(client, student_headers, event_id):
    response = client.post(f"/events/{event_id}/registrations", headers=student_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["event_id"] == event_id
    assert len(body["qr_token"]) == 22


def test_registering_twice_returns_409(client, student_headers, event_id, ticket):
    response = client.post(f"/events/{event_id}/registrations", headers=student_headers)
    assert response.status_code == 409


def test_register_for_missing_event_returns_404(client, student_headers):
    response = client.post("/events/999/registrations", headers=student_headers)
    assert response.status_code == 404


def test_register_requires_login(client, event_id):
    response = client.post(f"/events/{event_id}/registrations")
    assert response.status_code == 401


def test_every_ticket_gets_a_different_token(client, other_student_headers, event_id, ticket):
    other = client.post(f"/events/{event_id}/registrations", headers=other_student_headers)
    assert other.json()["qr_token"] != ticket["qr_token"]


def test_my_registrations_shows_only_my_tickets(
    client, student_headers, other_student_headers, ticket
):
    mine = client.get("/me/registrations", headers=student_headers).json()
    theirs = client.get("/me/registrations", headers=other_student_headers).json()
    assert [t["qr_token"] for t in mine] == [ticket["qr_token"]]
    assert theirs == []


def test_qr_code_is_a_png_image(client, student_headers, ticket):
    response = client.get(f"/me/registrations/{ticket['id']}/qr", headers=student_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_cannot_get_someone_elses_qr_code(client, other_student_headers, ticket):
    response = client.get(f"/me/registrations/{ticket['id']}/qr", headers=other_student_headers)
    assert response.status_code == 404


def test_organizer_list_hides_qr_tokens(client, organizer_headers, event_id, ticket):
    response = client.get(f"/events/{event_id}/registrations", headers=organizer_headers)
    assert response.status_code == 200
    registrations = response.json()
    assert len(registrations) == 1
    assert "qr_token" not in registrations[0]


def test_student_cannot_list_registrations(client, student_headers, event_id):
    response = client.get(f"/events/{event_id}/registrations", headers=student_headers)
    assert response.status_code == 403

def make_event(client, organizer_headers, capacity):
    response = client.post(
        "/events",
        json={"name": "Tiny Event", "starts_at": "2030-05-01T18:00:00Z", "location": "Room 1", "capacity": capacity},
        headers=organizer_headers,
    )
    return response.json()["id"]


def test_full_event_rejects_registration(client, organizer_headers, student_headers, other_student_headers):
    tiny = make_event(client, organizer_headers, capacity=1)
    first = client.post(f"/events/{tiny}/registrations", headers=student_headers)
    second = client.post(f"/events/{tiny}/registrations", headers=other_student_headers)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Event is full"


def test_already_registered_wins_over_full(client, organizer_headers, student_headers):
    tiny = make_event(client, organizer_headers, capacity=1)
    client.post(f"/events/{tiny}/registrations", headers=student_headers)
    again = client.post(f"/events/{tiny}/registrations", headers=student_headers)
    assert again.json()["detail"] == "You are already registered for this event"
