import csv
import io


def test_attendance_counts_registered_and_checked_in(
    client, organizer_headers, other_student_headers, event_id, ticket
):
    client.post(f"/events/{event_id}/registrations", headers=other_student_headers)
    client.post(
        f"/events/{event_id}/check-ins",
        json={"qr_token": ticket["qr_token"]},
        headers=organizer_headers,
    )
    response = client.get(f"/events/{event_id}/attendance", headers=organizer_headers)
    assert response.status_code == 200
    assert response.json() == {
        "event_id": event_id,
        "capacity": 50,
        "registered": 2,
        "checked_in": 1,
    }


def test_attendance_requires_organizer(client, student_headers, event_id):
    response = client.get(f"/events/{event_id}/attendance", headers=student_headers)
    assert response.status_code == 403


def test_attendance_for_missing_event_returns_404(client, organizer_headers):
    response = client.get("/events/999/attendance", headers=organizer_headers)
    assert response.status_code == 404


def test_csv_lists_everyone_including_no_shows(
    client, organizer_headers, other_student_headers, event_id, ticket
):
    client.post(f"/events/{event_id}/registrations", headers=other_student_headers)
    client.post(
        f"/events/{event_id}/check-ins",
        json={"qr_token": ticket["qr_token"]},
        headers=organizer_headers,
    )
    response = client.get(f"/events/{event_id}/attendees.csv", headers=organizer_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [(row["email"], row["checked_in"]) for row in rows] == [
        ("student@test.com", "yes"),
        ("other@test.com", "no"),
    ]


def test_csv_requires_organizer(client, student_headers, event_id):
    response = client.get(f"/events/{event_id}/attendees.csv", headers=student_headers)
    assert response.status_code == 403