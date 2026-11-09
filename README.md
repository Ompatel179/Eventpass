# EventPass

QR-code event check-in for student clubs. Students register and get a QR ticket; organizers scan tickets at the door from a phone browser, and every ticket can be checked in exactly once — even when several organizers scan at the same moment.

**Live demo:** available on request (hosted on Render + Neon free tier; the first request after idle takes ~1 minute to wake up).

## Highlights

- **Race-safe check-in** — a database unique constraint (not application code) guarantees one check-in per ticket. Under load, 2,862 concurrent scans of 2,000 tickets produced **0 duplicates**.
- **Found and fixed a production-style deadlock** with load testing (details below): the API froze at 13 req/s under load; after the fix it served **~950 req/s with 0 errors** on a single worker.
- **Indexed by evidence** — `EXPLAIN ANALYZE` on a 1M-row table showed a sequential scan; one index cut the query from **16.2 ms to 0.08 ms**.
- **76 automated tests, 98% line coverage**, run by GitHub Actions on every pull request; `main` is protected and only accepts green PRs.

## Tech stack

| Area | Tools |
|---|---|
| API | Python 3.11, FastAPI, Pydantic |
| Data | PostgreSQL 16, SQLAlchemy 2, Alembic migrations |
| Cache / rate limits | Redis |
| Auth | JWT bearer tokens, Argon2 password hashing, student / organizer roles |
| Frontend | Plain HTML + JavaScript scanner page (`/scanner`) using the phone camera |
| Testing | pytest, Locust (load testing) |
| DevOps | Docker, Docker Compose, GitHub Actions, Render (app + Redis), Neon (Postgres) |

## Architecture

```mermaid
flowchart LR
    Phone["Organizer phone<br/>/scanner page"] -->|HTTPS| API["FastAPI app<br/>(Docker on Render)"]
    Student["Student"] -->|HTTPS| API
    API --> PG[("PostgreSQL<br/>Neon")]
    API --> Redis[("Redis<br/>rate limits + cache")]
```

## How it works

1. A student signs up, logs in, and registers for an event. The API returns a ticket with a random, unguessable QR token (and prepares a ticket email in the background).
2. At the door, an organizer opens `/scanner` on their phone, logs in, picks the event, and points the camera at the student's QR code.
3. The API inserts a check-in row. **201** = welcome in, **409** = this ticket was already used, **404** = not a ticket for this event.
4. Organizers can see live attendance numbers and export a CSV of attendees.

## Performance (measured)

All numbers come from Locust load tests in this repo (`loadtest/`), run locally on a MacBook (Postgres 16 and Redis in Docker; Locust on the same machine), against a database seeded with 10,000 students.

**Baseline — realistic pacing (users pause 1–3 s between actions):**

| Simulated users | Requests | Errors | Req/s | Check-in p50 | Check-in p95 |
|---|---|---|---|---|---|
| 50 | 1,957 | 0 | 33 | 13 ms | 19 ms |
| 100 | 3,731 | 0 | 63 | 10 ms | 17 ms |
| 200 | 7,462 | 0 | 126 | 8 ms | 49 ms |

**Stress — no pauses, 100 users, steady state:**

| Setup | Max DB connections | Errors | Req/s |
|---|---|---|---|
| Before the deadlock fix (1 worker) | 15 | 10% | 13 (frozen) |
| After the fix, 1 worker | 15 | 0 | ~950 |
| After the fix, 2 workers | 30 | 0 | ~1,500 |
| After the fix, 4 workers | 60 | 0 | ~1,940 |
| After the fix, 4 workers, small pool | 20 | 0 | ~1,810 |

**Index on `registrations.user_id` (1,000,000 rows):** query 16.2 ms → 0.08 ms; `GET /me/registrations` median 25 ms → 8 ms under load.

## Engineering notes

### The deadlock load testing found
With no pauses between requests, the API handled ~800 req/s for four seconds and then completed **zero** requests for 30 seconds, followed by a burst of `500` errors. The 30 seconds matched SQLAlchemy's pool timeout.

Cause: FastAPI runs regular (`def`) endpoints on a pool of ~40 threads, but the database pool had 15 connections. A request takes a connection in one thread hop (`get_current_user`) and needs *another* thread hop to finish. Under load, all 40 threads were waiting for connections while all 15 connections were held by requests waiting for a thread — a deadlock, broken only by the timeout.

Confirmed by experiment (a pool larger than the thread count made the freeze disappear), then fixed properly: an `asyncio.Semaphore` middleware admits only as many requests as there are connections. This keeps pools small, which matters because Postgres has a connection limit and every worker process has its own pool. The tuning result: 4 workers × 5 connections kept 93% of the throughput of 4 × 15 — the bottleneck is CPU, not the database.

### Design decisions

| Decision | Why | Trade-off |
|---|---|---|
| Unique constraint enforces one check-in per ticket | The database is the only place that sees every concurrent request | Duplicate scans surface as a caught `IntegrityError` → 409 |
| Sign-up always creates a student; organizers are promoted separately | Clients must never choose their own privileges | Needs an admin step (SQL for now) |
| Redis fixed-window rate limits on login (per email + per IP) and sign-up | Stops password guessing before the slow Argon2 check runs | Fixed windows allow short bursts at window edges |
| Client IP from `CF-Connecting-IP` | Render sits behind Cloudflare, which overwrites this header; `X-Forwarded-For` can be spoofed | Tied to the hosting setup |
| Rate limiting and caching **fail open** | If Redis is down, the app gets slower, not broken | No rate limiting during a Redis outage |
| Cache event reads (60 s TTL) with versioned keys for pagination | Creating an event bumps a version number instead of hunting down every cached page | A list can be up to 60 s stale if Redis drops an invalidation |
| Background tasks for ticket emails | The student gets a response immediately | A task is lost if the server restarts at that moment (no retry queue); no email provider is connected yet, so emails are only logged |
| `limit`/`offset` pagination (max 100) | Simple and enough at this size | Large offsets get slower; keyset pagination would scale better |
| `pool_pre_ping=True` | Neon closes idle connections; this checks a connection before using it | One tiny extra query per checkout |

## Running locally

**With Docker Compose** (app + Postgres + Redis):

```bash
cp .env.example .env
# set SECRET_KEY in .env, e.g. python -c "import secrets; print(secrets.token_urlsafe(32))"
docker compose up --build
```

Open <http://localhost:8000/docs> for the interactive API and <http://localhost:8000/scanner> for the scanner page. To make an account an organizer:

```bash
docker compose exec db psql -U eventpass -d eventpass -c "UPDATE users SET role = 'organizer' WHERE email = 'you@example.com';"
```

**Running the tests** (needs Postgres on port 5432 with an `eventpass_test` database, and Redis on 6379 — see `.env.example`):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

**Load testing:** `pip install -r requirements-loadtest.txt`, seed a separate `eventpass_load` database with `python -m loadtest.seed`, then run `locust -f loadtest/locustfile.py`. `loadtest/bulk_registrations.sql` grows the data to 1M registrations for index experiments.

## API

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | anyone | Create a student account (rate limited) |
| POST | `/auth/login` | anyone | Get a JWT (rate limited) |
| GET | `/auth/me` | logged in | Current user |
| GET | `/events` | anyone | List events (`limit`, `offset`; cached) |
| POST | `/events` | organizer | Create an event |
| GET | `/events/{id}` | anyone | One event (cached) |
| POST | `/events/{id}/registrations` | student | Register and get a QR ticket |
| GET | `/events/{id}/registrations` | organizer | Registrations for an event (paginated) |
| GET | `/me/registrations` | logged in | My tickets |
| GET | `/me/registrations/{id}/qr` | ticket owner | Ticket QR code as PNG |
| POST | `/events/{id}/check-ins` | organizer | Check in a ticket (201 / 409 / 404) |
| GET | `/events/{id}/attendance` | organizer | Capacity, registered, checked-in counts |
| GET | `/events/{id}/attendees.csv` | organizer | CSV export |
| GET | `/health` | anyone | Liveness + database check (503 if the DB is down) |
| GET | `/scanner` | anyone | Phone scanner page |

## Deployment

Pushing to `main` (only possible through a pull request with passing CI) triggers Render to build the Docker image and deploy after the checks pass. The container runs `alembic upgrade head` before starting, so schema changes ship with the code.

## Limitations and next steps

- A student/organizer web UI (today only the scanner page has a UI; everything else uses `/docs`)
- Store event times as `timestamptz` (time-zone aware) before building the UI
- Connect an email provider (required for password reset)
- Password reset
- Use it at a real club meeting and report real-world numbers