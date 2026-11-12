import logging

from app.emails import send_email

EVIL_EVENT = {
    "name": "<script>alert(1)</script>",
    "starts_at": "2030-01-01T18:00:00Z",
    "location": "Room 101",
    "capacity": 50,
}


def register(client, event_id, headers):
    return client.post(f"/events/{event_id}/registrations", headers=headers)


def test_registering_emails_the_ticket(client, student_headers, event_id, sent_emails):
    register(client, event_id, student_headers)

    assert len(sent_emails) == 1
    email = sent_emails[0]
    assert email["to"] == "student@test.com"
    assert email["subject"] == "Your ticket for Test Event"
    assert email["attachment_name"] == "ticket.png"
    assert email["attachment"].startswith(b"\x89PNG")


def test_duplicate_registration_sends_no_second_email(
    client, student_headers, event_id, sent_emails
):
    register(client, event_id, student_headers)
    assert register(client, event_id, student_headers).status_code == 409
    assert len(sent_emails) == 1


def test_event_name_is_escaped_in_email(
    client, organizer_headers, student_headers, sent_emails
):
    response = client.post("/events", json=EVIL_EVENT, headers=organizer_headers)
    register(client, response.json()["id"], student_headers)

    body = sent_emails[0]["html"]
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_default_sender_only_logs(caplog):
    with caplog.at_level(logging.INFO, logger="eventpass"):
        send_email(to="a@test.com", subject="Hi", html="<p>Hi</p>", attachment=b"1234")

    assert "Email ready (no provider, not sent): Hi, attachment 4 bytes" in caplog.text
    assert "a@test.com" not in caplog.text