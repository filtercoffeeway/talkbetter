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
    ActivityResult,
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


# ---------- 30-day program ----------
def get_activity_results(profile_id: int) -> dict[tuple[int, str], ActivityResult]:
    """Return ``{(day, activity_id): ActivityResult}`` for one profile.

    Activities never attempted are absent; callers treat that as not done.
    """
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT day, activity_id, attempts, best_score, last_score,
                   first_done_at, last_done_at
            FROM program_activity_results
            WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchall()
    return {
        (r["day"], r["activity_id"]): ActivityResult(
            attempts=r["attempts"],
            best_score=r["best_score"],
            last_score=r["last_score"],
            first_done_at=r["first_done_at"],
            last_done_at=r["last_done_at"],
        )
        for r in rows
    }


def record_activity_attempt(
    profile_id: int, day: int, activity_id: str, score: float | None, session_id: int
) -> None:
    """Count one attempt at a program activity, keeping the best score."""
    with db.get_conn() as conn:
        conn.execute(
            """
            INSERT INTO program_activity_results (
                profile_id, day, activity_id, attempts, best_score, last_score, last_session_id
            ) VALUES (?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(profile_id, day, activity_id) DO UPDATE SET
                attempts        = attempts + 1,
                best_score      = CASE
                                    WHEN best_score IS NULL THEN excluded.best_score
                                    WHEN excluded.best_score IS NULL THEN best_score
                                    ELSE MAX(best_score, excluded.best_score)
                                  END,
                last_score      = excluded.last_score,
                last_session_id = excluded.last_session_id,
                last_done_at    = datetime('now', 'localtime')
            """,
            (profile_id, day, activity_id, score, score, session_id),
        )


def record_benchmark(
    profile_id: int, day: int, part: str, session_id: int, metrics: dict
) -> bool:
    """Store a benchmark take if it's the first for (profile, day, part).

    Returns True if stored, False if that part already had its take today —
    the first take is the ground truth, retakes don't overwrite it.
    """
    cols = ("score", "words_per_minute", "filler_rate_per_min", "long_pauses",
            "confidence", "structure", "clarity")
    with db.get_conn() as conn:
        cur = conn.execute(
            f"""
            INSERT OR IGNORE INTO benchmark_results (
                profile_id, day, part, session_id, {", ".join(cols)}
            ) VALUES (?, ?, ?, ?, {", ".join("?" for _ in cols)})
            """,
            (profile_id, day, part, session_id, *(metrics.get(c) for c in cols)),
        )
        return cur.rowcount == 1


def list_benchmarks(profile_id: int) -> list[dict]:
    """All benchmark takes for a profile, oldest day first, as plain dicts."""
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT day, part, created_at, score, words_per_minute,
                   filler_rate_per_min, long_pauses, confidence, structure, clarity
            FROM benchmark_results
            WHERE profile_id = ?
            ORDER BY day, part
            """,
            (profile_id,),
        ).fetchall()
    return [dict(r) for r in rows]


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
