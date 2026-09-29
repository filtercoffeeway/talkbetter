"""30-day program — lookups, scoring, and progress assembly.

Content lives in ``program_content.py``; per-profile results in SQLite
(``program_activity_results`` and ``benchmark_results``, see db.py).

Scoring is deterministic so that a score of 70 on day 3 means the same thing as
a 70 on day 24:

* **read** activities score the pronunciation ``pron_score`` (0-100).
* **speak** activities score a weighted composite of
    fluency   30%  — fillers/min and long pauses/min (local)
    pace      10%  — 100 inside 120-160 wpm, falling off either side (local)
    confidence 20% — LLM rubric
    structure 20%  — LLM rubric (thought process: answer first, support, close)
    clarity    20% — LLM grammar/clarity score
  Components that aren't available (no LLM key) are left out and the weights
  renormalize, so keep the LLM configured for the whole 30 days if you want a
  strictly like-for-like trend.
* The **daily benchmark** score is 40% read + 60% speak.
"""
from __future__ import annotations

from datetime import date

from app.models.schemas import (
    AnalysisResponse,
    BenchmarkEntry,
    BenchmarkHistory,
    BenchmarkWeek,
    PaceFillerReport,
    ProgramActivity,
    ProgramAttempt,
    ProgramDay,
    ProgramResponse,
    ProgramSummary,
    ProgramWeek,
)
from app.services import program_content as content
from app.services import storage

TOTAL_DAYS = len(content.DAYS)
BENCHMARK_READ_ID = "benchmark-read"
BENCHMARK_SPEAK_ID = "benchmark-speak"

# A recording shorter than this (in words) doesn't count — likely a mic glitch.
MIN_WORDS = {"read": 3, "speak": 10}

SPEAK_WEIGHTS = {"fluency": 0.30, "pace": 0.10, "confidence": 0.20,
                 "structure": 0.20, "clarity": 0.20}
BENCHMARK_WEIGHTS = {"read": 0.4, "speak": 0.6}
PACE_RANGE = (120.0, 160.0)   # comfortable, clear conversational pace (wpm)


# ---------- content lookups ----------
def week_of(day: int) -> int:
    """Days 1-7 -> week 1 ... days 22-30 -> week 4."""
    return min((day - 1) // 7 + 1, len(content.WEEKS))


def _benchmark_activities(day: int) -> list[dict]:
    return [
        {
            "id": BENCHMARK_READ_ID, "section": "benchmark", "kind": "read",
            "skill": "pronunciation", "title": "Benchmark · read the passage",
            "minutes": 2, "reference_text": content.BENCHMARK_READ_TEXT,
            "instructions": "The same passage every day. Read it once at a natural pace. "
                            "Only your first take of the day counts.",
        },
        {
            "id": BENCHMARK_SPEAK_ID, "section": "benchmark", "kind": "speak",
            "skill": "confidence", "title": "Benchmark · 90-second answer",
            "minutes": 3, "prompt": content.BENCHMARK_PROMPTS[day - 1],
            "target_seconds": content.BENCHMARK_SPEAK_SECONDS,
            "instructions": content.BENCHMARK_SPEAK_INSTRUCTIONS,
        },
    ]


def _day_activities(day: int) -> list[dict]:
    practice = [{"section": "practice", **a} for a in content.DAYS[day - 1]["activities"]]
    return _benchmark_activities(day) + practice


def get_activity(day: int, activity_id: str) -> ProgramActivity | None:
    if not 1 <= day <= TOTAL_DAYS:
        return None
    for a in _day_activities(day):
        if a["id"] == activity_id:
            return ProgramActivity(**a)
    return None


# ---------- scoring ----------
def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def fluency_score(pace: PaceFillerReport) -> float:
    """100 with no fillers or long pauses; -10 per filler/min, -5 per long pause/min."""
    minutes = max(pace.duration_sec, 1.0) / 60.0
    pauses_per_min = pace.long_pauses / minutes
    return _clamp(100 - 10 * pace.filler_rate_per_min - 5 * pauses_per_min)


def pace_score(wpm: float) -> float:
    """100 inside PACE_RANGE, -2 per wpm outside it."""
    lo, hi = PACE_RANGE
    if wpm < lo:
        return _clamp(100 - 2 * (lo - wpm))
    if wpm > hi:
        return _clamp(100 - 2 * (wpm - hi))
    return 100.0


def _weighted(parts: dict[str, float | None], weights: dict[str, float]) -> float | None:
    present = {k: v for k, v in parts.items() if v is not None}
    if not present:
        return None
    total_w = sum(weights[k] for k in present)
    return round(sum(weights[k] * v for k, v in present.items()) / total_w, 1)


def speak_components(response: AnalysisResponse) -> dict[str, float | None]:
    pf = response.pace_fillers
    return {
        "fluency": fluency_score(pf),
        "pace": pace_score(pf.words_per_minute),
        "confidence": response.speaking.confidence if response.speaking else None,
        "structure": response.speaking.structure if response.speaking else None,
        "clarity": response.language.clarity.score if response.language else None,
    }


def activity_score(kind: str, response: AnalysisResponse) -> float | None:
    if kind == "read":
        return round(response.accent.pron_score, 1) if response.accent else None
    return _weighted(speak_components(response), SPEAK_WEIGHTS)


# ---------- recording an attempt ----------
def record_attempt(
    profile_id: int, day: int, activity: ProgramActivity,
    response: AnalysisResponse, session_id: int,
) -> ProgramAttempt:
    """Score one recording against its activity and persist it.

    Too-short recordings aren't counted. Benchmark activities are also written to
    ``benchmark_results``, where only the day's first take sticks.
    """
    if response.pace_fillers.total_words < MIN_WORDS[activity.kind]:
        return ProgramAttempt(
            day=day, activity_id=activity.id, counted=False,
            message="That recording was too short to count — try again.",
        )

    score = activity_score(activity.kind, response)
    storage.record_activity_attempt(profile_id, day, activity.id, score, session_id)

    attempt = ProgramAttempt(day=day, activity_id=activity.id, counted=True, score=score)
    if activity.section == "benchmark":
        part = "read" if activity.kind == "read" else "speak"
        metrics: dict = {"score": score}
        if part == "speak":
            pf = response.pace_fillers
            metrics |= {
                "words_per_minute": pf.words_per_minute,
                "filler_rate_per_min": pf.filler_rate_per_min,
                "long_pauses": pf.long_pauses,
                "confidence": response.speaking.confidence if response.speaking else None,
                "structure": response.speaking.structure if response.speaking else None,
                "clarity": response.language.clarity.score if response.language else None,
            }
        attempt.benchmark_recorded = storage.record_benchmark(
            profile_id, day, part, session_id, metrics
        )
        attempt.message = (
            "Benchmark recorded for today." if attempt.benchmark_recorded
            else "Today's benchmark was already recorded — this retake is practice only."
        )
    return attempt


# ---------- assembling the program view ----------
def get_program(profile_id: int | None = None) -> ProgramResponse:
    results = storage.get_activity_results(profile_id) if profile_id is not None else {}

    days: list[ProgramDay] = []
    for n, d in enumerate(content.DAYS, start=1):
        activities = [
            ProgramActivity(**a, result=results.get((n, a["id"])))
            for a in _day_activities(n)
        ]
        done = all(a.result for a in activities)
        days.append(ProgramDay(
            day=n, week=week_of(n), title=d["title"], goal=d["goal"],
            minutes=sum(a.minutes for a in activities), activities=activities,
            status="completed" if done else "locked",
            completed_at=max(a.result.first_done_at for a in activities) if done else None,
        ))

    summary = None
    if profile_id is not None:
        current = next((d.day for d in days if d.status != "completed"), TOTAL_DAYS)
        for d in days:
            if d.day == current and d.status != "completed":
                d.status = "available"
        today = date.today().isoformat()
        summary = ProgramSummary(
            current_day=current,
            completed_days=sum(d.status == "completed" for d in days),
            total_days=TOTAL_DAYS,
            finished_a_day_today=any(
                d.completed_at and d.completed_at[:10] == today for d in days
            ),
        )
    else:
        for d in days:
            d.status = "available"

    return ProgramResponse(
        title=content.PROGRAM_TITLE,
        description=content.PROGRAM_DESCRIPTION,
        daily_minutes=content.DAILY_MINUTES,
        benchmark_description=content.BENCHMARK_DESCRIPTION,
        weeks=[ProgramWeek(**w) for w in content.WEEKS],
        days=days,
        summary=summary,
    )


def get_benchmarks(profile_id: int) -> BenchmarkHistory:
    by_day: dict[int, dict[str, dict]] = {}
    for row in storage.list_benchmarks(profile_id):
        by_day.setdefault(row["day"], {})[row["part"]] = row

    entries: list[BenchmarkEntry] = []
    for day, parts in sorted(by_day.items()):
        rd, sp = parts.get("read"), parts.get("speak")
        read_score = rd["score"] if rd else None
        speak_score = sp["score"] if sp else None
        first = min(p["created_at"] for p in parts.values())
        entries.append(BenchmarkEntry(
            day=day, week=week_of(day), date=first[:10],
            score=_weighted({"read": read_score, "speak": speak_score}, BENCHMARK_WEIGHTS),
            read_score=read_score, speak_score=speak_score,
            **({k: sp[k] for k in ("words_per_minute", "filler_rate_per_min",
                                   "long_pauses", "confidence", "structure",
                                   "clarity")} if sp else {}),
        ))

    def avg(values) -> float | None:
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    weeks = []
    for w in sorted({e.week for e in entries}):
        es = [e for e in entries if e.week == w]
        weeks.append(BenchmarkWeek(
            week=w, days=len(es),
            avg_score=avg(e.score for e in es),
            avg_read_score=avg(e.read_score for e in es),
            avg_speak_score=avg(e.speak_score for e in es),
            avg_filler_rate_per_min=avg(e.filler_rate_per_min for e in es),
            avg_confidence=avg(e.confidence for e in es),
            avg_structure=avg(e.structure for e in es),
        ))

    scored = [e.score for e in entries if e.score is not None]
    return BenchmarkHistory(
        profile_id=profile_id, entries=entries, weeks=weeks,
        baseline=scored[0] if scored else None,
        latest=scored[-1] if scored else None,
    )
