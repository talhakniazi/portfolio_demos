-- PureSpace website database (SQLite). Created by:  flask --app purespace init-db
CREATE TABLE IF NOT EXISTS enquiries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ref           TEXT    NOT NULL UNIQUE,          -- shown to the customer, e.g. PS-261102-K7QX
    kind          TEXT    NOT NULL CHECK (kind IN ('quote', 'contact')),
    status        TEXT    NOT NULL DEFAULT 'new'
                          CHECK (status IN ('new', 'contacted', 'quoted', 'booked', 'lost', 'archived')),
    created_at    TEXT    NOT NULL,                 -- ISO 8601, UTC
    updated_at    TEXT    NOT NULL,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    phone         TEXT,
    postcode      TEXT,
    sector        TEXT,                             -- residential / commercial (quotes only)
    service       TEXT,                             -- e.g. regular, deep, end_of_tenancy, office
    bedrooms      INTEGER,
    bathrooms     INTEGER,
    floor_area    INTEGER,                          -- square feet (commercial)
    frequency     TEXT,
    extras        TEXT,                             -- comma-separated extras
    preferred_date TEXT,
    message       TEXT,
    estimate_low  INTEGER,                          -- guide price in pounds, calculated by the server
    estimate_high INTEGER,
    contact_pref  TEXT,
    source_ip_hash TEXT                             -- salted hash only; the raw IP address is never stored
);
CREATE INDEX IF NOT EXISTS ix_enquiries_created ON enquiries (created_at);
CREATE INDEX IF NOT EXISTS ix_enquiries_status ON enquiries (status);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    enquiry_id  INTEGER NOT NULL REFERENCES enquiries (id) ON DELETE CASCADE,
    created_at  TEXT    NOT NULL,
    author      TEXT    NOT NULL,
    body        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,                    -- scrypt hash (werkzeug); passwords are never stored
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS events (                -- rate limiting (form posts, failed logins)
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    action  TEXT NOT NULL,
    key     TEXT NOT NULL,                          -- salted hash of IP (+ username for logins)
    at      REAL NOT NULL                           -- unix time
);
CREATE INDEX IF NOT EXISTS ix_events ON events (action, key, at);
