"""Fire many simultaneous check-ins for ONE ticket and count the results.

Usage: python scripts/race_check_in.py [event_id] [number_of_scans]
"""

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib import error, parse, request

BASE_URL = "http://127.0.0.1:8000"


def call(method: str, path: str, token: str | None = None, json_body=None, form=None):
    headers = {}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as response:
            return response.status, json.loads(response.read() or "null")
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or "null")


def login(email: str, password: str) -> str:
    _, body = call("POST", "/auth/login", form={"username": email, "password": password})
    return body["access_token"]


def main(event_id: int, scans: int) -> None:
    student = login("student@rutgers.edu", "studentpass123")
    organizer = login("organizer@rutgers.edu", "organizerpass123")

    status, ticket = call("POST", f"/events/{event_id}/registrations", token=student)
    if status == 409:
        _, tickets = call("GET", "/me/registrations", token=student)
        ticket = next(t for t in tickets if t["event_id"] == event_id)

    def scan(_: int) -> int:
        status, _ = call(
            "POST",
            f"/events/{event_id}/check-ins",
            token=organizer,
            json_body={"qr_token": ticket["qr_token"]},
        )
        return status

    with ThreadPoolExecutor(max_workers=scans) as pool:
        results = Counter(pool.map(scan, range(scans)))

    print(f"{scans} simultaneous scans of one ticket -> {dict(results)}")


if __name__ == "__main__":
    event_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    scans = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    main(event_id, scans)