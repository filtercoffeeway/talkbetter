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
    LessonProgress,
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


# ---------- course / lesson progress (Phase 4 — accent course) ----------
def get_lesson_progress(profile_id: int) -> dict[str, LessonProgress]:
    """Return ``{lesson_id: LessonProgress}`` for one profile.

    Lessons the profile has never attempted are simply absent from the map;
    callers (services/course.py) treat a missing entry as "not_started".
    """
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT lesson_id, status, attempts, best_score, last_score,
                   last_practiced_at, completed_at
            FROM lesson_progress
            WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchall()
    return {
        r["lesson_id"]: LessonProgress(
            status=r["status"],
            attempts=r["attempts"],
            best_score=r["best_score"],
            last_score=r["last_score"],
            last_practiced_at=r["last_practiced_at"],
            completed_at=r["completed_at"],
        )
        for r in rows
    }


def record_lesson_attempt(
    profile_id: int, lesson_id: str, score: float | None, target_score: float
) -> LessonProgress:
    """Record one practice attempt at a lesson and return the updated standing.

    Read-modify-write so we can keep the *best* score and a stable
    ``completed_at`` across attempts. A lesson becomes ``completed`` the first
    time an attempt's ``score`` reaches ``target_score``; once completed it stays
    completed even if a later attempt scores lower. Attempts without a score
    (e.g. Phase 3 not configured) still count toward ``attempts`` and leave the
    lesson ``attempted``.
    """
    with db.get_conn() as conn:
        row = conn.execute(
            """
            SELECT attempts, best_score, status, completed_at
            FROM lesson_progress
            WHERE profile_id = ? AND lesson_id = ?
            """,
            (profile_id, lesson_id),
        ).fetchone()

        attempts = (row["attempts"] if row else 0) + 1
        prev_best = row["best_score"] if row else None
        best_score = max([s for s in (prev_best, score) if s is not None], default=None)
        completed_at = row["completed_at"] if row else None
        status = row["status"] if row else "attempted"

        if score is not None and score >= target_score:
            status = "completed"
            if completed_at is None:
                completed_at = datetime.now().isoformat(" ", "seconds")

        conn.execute(
            """
            INSERT INTO lesson_progress (
                profile_id, lesson_id, status, attempts,
                best_score, last_score, last_practiced_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            ON CONFLICT(profile_id, lesson_id) DO UPDATE SET
                status            = excluded.status,
                attempts          = excluded.attempts,
                best_score        = excluded.best_score,
                last_score        = excluded.last_score,
                last_practiced_at = excluded.last_practiced_at,
                completed_at      = excluded.completed_at
            """,
            (profile_id, lesson_id, status, attempts, best_score, score, completed_at),
        )
        updated = conn.execute(
            """
            SELECT status, attempts, best_score, last_score,
                   last_practiced_at, completed_at
            FROM lesson_progress
            WHERE profile_id = ? AND lesson_id = ?
            """,
            (profile_id, lesson_id),
        ).fetchone()

    return LessonProgress(
        status=updated["status"],
        attempts=updated["attempts"],
        best_score=updated["best_score"],
        last_score=updated["last_score"],
        last_practiced_at=updated["last_practiced_at"],
        completed_at=updated["completed_at"],
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
