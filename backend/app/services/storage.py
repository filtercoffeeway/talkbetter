"""Phase 4 — persistence + progress queries over the SQLite DB.

Profiles let more than one person share this local install; each person's
sessions are kept separate. ``save_session`` is called after every analysis;
``list_history`` powers the dashboard charts and the streak counter.

All functions open their own short-lived connection (see app.db).
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from app import db
from app.models.schemas import (
    AnalysisResponse,
    HistoryResponse,
    Profile,
    SessionSummary,
)


# ---------- profiles ----------
def list_profiles() -> list[Profile]:
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.created_at,
                   COUNT(s.id) AS session_count
            FROM profiles p
            LEFT JOIN sessions s ON s.profile_id = p.id
            GROUP BY p.id
            ORDER BY p.name COLLATE NOCASE
            """
        ).fetchall()
    return [Profile(**dict(r)) for r in rows]


def create_profile(name: str) -> Profile:
    """Create a profile, or return the existing one if the name is taken.

    Names are matched case-insensitively (see UNIQUE COLLATE NOCASE), so
    "Mahesh" and "mahesh" are the same person.
    """
    name = name.strip()
    if not name:
        raise ValueError("Profile name cannot be empty.")
    with db.get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO profiles (name) VALUES (?)", (name,)
        )
        row = conn.execute(
            """
            SELECT p.id, p.name, p.created_at,
                   COUNT(s.id) AS session_count
            FROM profiles p
            LEFT JOIN sessions s ON s.profile_id = p.id
            WHERE p.name = ? COLLATE NOCASE
            GROUP BY p.id
            """,
            (name,),
        ).fetchone()
    return Profile(**dict(row))


def profile_exists(profile_id: int) -> bool:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
    return row is not None


# ---------- sessions ----------
def save_session(
    profile_id: int, mode: str, response: AnalysisResponse
) -> int:
    """Persist one analyzed recording. Returns the new session id.

    Headline metrics are flattened into columns for cheap charting; the full
    response is stored as JSON for replay/export. Phase 2/3 metrics are pulled
    out only if those sections are present (they're nullable).
    """
    pf = response.pace_fillers
    clarity = response.language.clarity.score if response.language else None
    pron = response.accent.pron_score if response.accent else None

    with db.get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (
                profile_id, mode, duration_sec, transcript,
                words_per_minute, total_words, long_pauses,
                filler_total, filler_rate_per_min,
                clarity_score, pron_score, response_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                mode,
                response.transcript.duration_sec,
                response.transcript.text,
                pf.words_per_minute,
                pf.total_words,
                pf.long_pauses,
                pf.filler_total,
                pf.filler_rate_per_min,
                clarity,
                pron,
                response.model_dump_json(),
            ),
        )
        return int(cur.lastrowid)


def list_history(profile_id: int, limit: int = 100) -> HistoryResponse:
    """Return a profile's sessions (newest first) plus the current streak."""
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, profile_id, created_at, mode, duration_sec, transcript,
                   words_per_minute, total_words, long_pauses,
                   filler_total, filler_rate_per_min, clarity_score, pron_score
            FROM sessions
            WHERE profile_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (profile_id, limit),
        ).fetchall()

    sessions = [SessionSummary(**dict(r)) for r in rows]
    streak = _current_streak(s.created_at for s in sessions)
    return HistoryResponse(
        profile_id=profile_id, current_streak=streak, sessions=sessions
    )


def _current_streak(created_ats) -> int:
    """Count consecutive calendar days with >=1 session, ending today/yesterday.

    A streak stays alive if you practiced today; if the most recent session was
    yesterday it still counts (you can keep it going today). Older than that and
    the streak is 0.
    """
    days = set()
    for ts in created_ats:
        try:
            days.add(datetime.fromisoformat(ts).date())
        except (ValueError, TypeError):
            continue
    if not days:
        return 0

    today = date.today()
    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
