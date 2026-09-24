"""SQLite persistence layer (Phase 4 — progress tracking & profiles).

Uses Python's stdlib ``sqlite3`` only — no new dependencies (see spec.html
Phase 4). The DB file lives at ``<repo>/data/talkbetter.db`` by default and is
gitignored. Schema is created on first use via :func:`init_db`.

Three tables:
  profiles         — one row per person sharing this local machine.
  sessions         — one row per analyzed recording, linked to a profile. We store
                     the headline metrics as columns (so history/charts are cheap to
                     query) plus the full AnalysisResponse JSON for replay/export.
  lesson_progress  — one row per (profile, accent-course lesson): a profile's standing
                     on a lesson (attempts, best score, completion). Lessons themselves
                     are static content in services/course.py, not a DB table.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id           INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    mode                 TEXT NOT NULL DEFAULT 'free',   -- 'free' | 'accent'
    duration_sec         REAL NOT NULL DEFAULT 0,
    transcript           TEXT NOT NULL DEFAULT '',
    -- Phase 1 metrics
    words_per_minute     REAL,
    total_words          INTEGER,
    long_pauses          INTEGER,
    filler_total         INTEGER,
    filler_rate_per_min  REAL,
    -- Phase 2 / 3 metrics (nullable until those phases are built)
    clarity_score        INTEGER,
    pron_score           REAL,
    -- full AnalysisResponse for replay / export
    response_json        TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sessions_profile_created
    ON sessions(profile_id, created_at);

CREATE TABLE IF NOT EXISTS lesson_progress (
    profile_id        INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    lesson_id         TEXT NOT NULL,                 -- slug from services/course.py
    status            TEXT NOT NULL DEFAULT 'attempted',  -- 'attempted' | 'completed'
    attempts          INTEGER NOT NULL DEFAULT 0,
    best_score        REAL,                          -- best pron_score reached (nullable)
    last_score        REAL,                          -- most recent attempt's pron_score
    last_practiced_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at      TEXT,                          -- first time it crossed target score
    PRIMARY KEY (profile_id, lesson_id)
);
"""


def _connect() -> sqlite3.Connection:
    """Open a connection with sane defaults.

    ``check_same_thread=False`` because FastAPI may serve requests on different
    threads; each call opens and closes its own short-lived connection so this
    is safe. Row factory gives us dict-like access by column name.
    """
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context manager yielding a connection, committing on success."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
