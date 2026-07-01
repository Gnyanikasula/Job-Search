"""
database/models.py — SQLite schema definitions
"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    cv_text     TEXT DEFAULT '',
    description TEXT DEFAULT '',
    location    TEXT DEFAULT '',
    country     TEXT DEFAULT 'UK',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    profile_id  TEXT PRIMARY KEY,
    gemini_key  TEXT DEFAULT '',
    groq_key    TEXT DEFAULT '',
    serper_key  TEXT DEFAULT '',
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    profile_id    TEXT NOT NULL,
    title         TEXT,
    company       TEXT,
    location      TEXT,
    source        TEXT,
    url           TEXT,
    description   TEXT DEFAULT '',
    date_posted   TEXT,
    fetched_at    TEXT DEFAULT (datetime('now')),
    status        TEXT DEFAULT 'New',
    score         INTEGER DEFAULT -1,
    score_data    TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS scores (
    fingerprint   TEXT PRIMARY KEY,
    profile_id    TEXT,
    score         INTEGER,
    breakdown     TEXT,
    scored_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id    TEXT,
    trigger       TEXT,
    jobs_found    INTEGER DEFAULT 0,
    jobs_new      INTEGER DEFAULT 0,
    ran_at        TEXT DEFAULT (datetime('now')),
    error         TEXT DEFAULT ''
);
"""
