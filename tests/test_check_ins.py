from collections import Counter
from concurrent.futures import ThreadPoolExecutor


def scan(client, event_id, headers, qr_token):
    return client.post(
        f"/events/{event_id}/check-ins", json={"qr_token": qr_token}, headers=headers
    )


def test_organizer_can_check_in_ticket(client, organizer_headers, event_id, ticket):
    response = scan(client, event_id, organizer_headers, ticket["qr_token"])
    assert response.status_code == 201
    assert response.json()["registration_id"] == ticket["id"]


def test_second_scan_is_rejected(client, organizer_headers, event_id, ticket):
    scan(client, event_id, organizer_headers, ticket["qr_token"])
    response = scan(client, event_id, organizer_headers, ticket["qr_token"])
    assert response.status_code == 409
    assert response.json() == {"detail": "Ticket already checked in"}


def test_unknown_ticket_returns_404(client, organizer_headers, event_id):
    response = scan(client, event_id, organizer_headers, "made-up-token")
    assert response.status_code == 404


def test_ticket_for_another_event_returns_404(client, organizer_headers, event_id, ticket):
    other_event = client.post(
        "/events",
        json={"name": "AI Club", "starts_at": "2030-02-01T18:00:00", "location": "CoRE", "capacity": 30},
        headers=organizer_headers,
    ).json()
    response = scan(client, other_event["id"], organizer_headers, ticket["qr_token"])
    assert response.status_code == 404


def test_empty_qr_token_returns_422(client, organizer_headers, event_id):
    response = scan(client, event_id, organizer_headers, "")
    assert response.status_code == 422


def test_student_cannot_check_in(client, student_headers, event_id, ticket):
    response = scan(client, event_id, student_headers, ticket["qr_token"])
    assert response.status_code == 403


def test_simultaneous_scans_only_one_succeeds(client, organizer_headers, event_id, ticket):
    def one_scan(_):
        return scan(client, event_id, organizer_headers, ticket["qr_token"]).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = Counter(pool.map(one_scan, range(20)))

    assert results == {201: 1, 409: 19}