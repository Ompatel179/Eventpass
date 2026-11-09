INSERT INTO events (name, starts_at, location, capacity)
SELECT 'Bulk Event ' || g, '2030-01-01 18:00', 'Bulk Hall', 100000
FROM generate_series(1, 99) AS g;

INSERT INTO registrations (event_id, user_id, qr_token)
SELECT e.id, u.id, md5(random()::text || e.id || '-' || u.id)
FROM events e
CROSS JOIN users u
WHERE e.name LIKE 'Bulk Event %' AND u.role = 'student';

ANALYZE;
