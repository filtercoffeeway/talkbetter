"""Tests for the 30-day program: curriculum, scoring, attempts, benchmark trend."""
import io
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.models.schemas import AccentReport, PaceFillerReport, SpeakingAssessment
from app.services import program, program_content
from tests.conftest import FAKE_LANGUAGE, FAKE_TRANSCRIPT

# A 60-second answer long enough to count (>= 10 words): 140 wpm, 2 fillers/min,
# no long pauses -> fluency 80, pace 100.
LONG_PACE = PaceFillerReport(
    words_per_minute=140.0, total_words=140, duration_sec=60.0, long_pauses=0,
    fillers=[], filler_total=2, filler_rate_per_min=2.0,
)
SHORT_PACE = LONG_PACE.model_copy(update={"total_words": 4})
FAKE_SPEAKING = SpeakingAssessment(
    confidence=70, structure=60, vocabulary=75, summary="Clear but hedged.",
    strengths=["Answered first"], improvements=["Drop 'I think'"],
    stronger_version="Working from home is better for focused work.",
)
FAKE_ACCENT = AccentReport(
    accuracy_score=80.0, fluency_score=90.0, completeness_score=100.0, pron_score=84.0,
)


@contextmanager
def services(pace=LONG_PACE, llm=True, accent=FAKE_ACCENT):
    """Mock every external service; yield the pronunciation.assess mock."""
    with (
        patch("app.services.transcription.transcribe", return_value=FAKE_TRANSCRIPT),
        patch("app.services.filler_pace.analyze", return_value=pace),
        patch("app.services.llm_feedback.is_available", return_value=llm),
        patch("app.services.llm_feedback.analyze", return_value=FAKE_LANGUAGE),
        patch("app.services.llm_feedback.assess_speaking", return_value=FAKE_SPEAKING),
        patch("app.services.pronunciation.is_available", return_value=accent is not None),
        patch("app.services.pronunciation.assess", return_value=accent) as assess,
    ):
        yield assess


@pytest.fixture()
def profile(client):
    return client.post("/api/profiles", json={"name": "Mahesh"}).json()["id"]


def _post(client, profile_id, day, activity_id, **extra):
    return client.post(
        "/api/analyze",
        files={"audio": ("recording.webm", io.BytesIO(b"audio"), "audio/webm")},
        data={"profile_id": str(profile_id), "program_day": str(day),
              "activity_id": activity_id, **extra},
    )


# ---------- content ----------
def test_every_day_has_benchmark_then_practice_and_fits_30_minutes(client):
    body = client.get("/api/program").json()
    assert len(body["days"]) == 30 and len(body["weeks"]) == 4
    for d in body["days"]:
        ids = [a["id"] for a in d["activities"]]
        assert ids[:2] == ["benchmark-read", "benchmark-speak"]
        assert len(ids) == len(set(ids))
        assert d["minutes"] == 30
        assert d["status"] == "available"   # no profile: everything browsable
    assert body["summary"] is None


def test_benchmark_passage_is_identical_every_day(client):
    days = client.get("/api/program").json()["days"]
    passages = {d["activities"][0]["reference_text"] for d in days}
    assert passages == {program_content.BENCHMARK_READ_TEXT}
    prompts = [d["activities"][1]["prompt"] for d in days]
    assert len(set(prompts)) == 30   # topic rotates so it can't be memorized
    assert {d["activities"][1]["target_seconds"] for d in days} == {90}


def test_program_reading_text_has_no_digits():
    """The phonemizer reads digits oddly; content must spell numbers out."""
    texts = [program_content.BENCHMARK_READ_TEXT] + [
        a["reference_text"] for d in program_content.DAYS
        for a in d["activities"] if a["kind"] == "read"
    ]
    assert not any(ch.isdigit() for t in texts for ch in t)


def test_week_of():
    assert [program.week_of(d) for d in (1, 7, 8, 14, 15, 21, 22, 28, 29, 30)] == \
        [1, 1, 2, 2, 3, 3, 4, 4, 4, 4]


# ---------- scoring ----------
def test_fluency_and_pace_scores():
    assert program.fluency_score(LONG_PACE) == 80.0
    assert program.fluency_score(
        LONG_PACE.model_copy(update={"filler_rate_per_min": 0.0, "long_pauses": 2})
    ) == 90.0
    assert program.pace_score(140) == 100.0
    assert program.pace_score(100) == 60.0
    assert program.pace_score(180) == 60.0
    assert program.pace_score(20) == 0.0


def test_weighted_renormalizes_over_present_components():
    w = {"a": 0.25, "b": 0.75}
    assert program._weighted({"a": 80, "b": 40}, w) == 50.0
    assert program._weighted({"a": 80, "b": None}, w) == 80.0
    assert program._weighted({"a": None, "b": None}, w) is None


# ---------- /api/analyze with program fields ----------
def test_program_activity_requires_profile(client):
    with services():
        r = client.post(
            "/api/analyze",
            files={"audio": ("r.webm", io.BytesIO(b"a"), "audio/webm")},
            data={"program_day": "1", "activity_id": "speak-1"},
        )
    assert r.status_code == 400


@pytest.mark.parametrize("day,aid", [(1, "nope"), (31, "speak-1"), (0, "speak-1")])
def test_unknown_program_activity_404(client, profile, day, aid):
    with services():
        assert _post(client, profile, day, aid).status_code == 404


def test_read_activity_scores_its_own_sentence(client, profile):
    with services() as assess:
        r = _post(client, profile, 1, "benchmark-read", reference_text="something else")
    assert r.status_code == 200
    assert assess.call_args.args[1] == program_content.BENCHMARK_READ_TEXT
    prog = r.json()["program"]
    assert prog == {**prog, "counted": True, "score": 84.0, "benchmark_recorded": True}


def test_speak_activity_gets_rubric_and_composite(client, profile):
    with services():
        r = _post(client, profile, 1, "speak-1")
    body = r.json()
    assert body["speaking"]["confidence"] == 70
    # fluency 80*.3 + pace 100*.1 + conf 70*.2 + struct 60*.2 + clarity 72*.2 = 74.4
    assert body["program"]["score"] == 74.4
    assert body["program"]["benchmark_recorded"] is False


def test_speak_without_llm_scores_delivery_only(client, profile):
    with services(llm=False):
        body = _post(client, profile, 1, "speak-1").json()
    assert body["speaking"] is None
    # (80*.3 + 100*.1) / .4 = 85
    assert body["program"]["score"] == 85.0


def test_too_short_recording_is_not_counted(client, profile):
    with services(pace=SHORT_PACE):
        body = _post(client, profile, 1, "speak-1").json()
    assert body["program"]["counted"] is False
    day1 = client.get(f"/api/program?profile_id={profile}").json()["days"][0]
    assert all(a["result"] is None for a in day1["activities"])


def test_only_first_benchmark_take_counts(client, profile):
    with services():
        _post(client, profile, 1, "benchmark-read")
    better = FAKE_ACCENT.model_copy(update={"pron_score": 99.0})
    with services(accent=better):
        second = _post(client, profile, 1, "benchmark-read").json()["program"]
    assert second["benchmark_recorded"] is False and second["score"] == 99.0

    hist = client.get(f"/api/program/benchmarks?profile_id={profile}").json()
    assert [e["read_score"] for e in hist["entries"]] == [84.0]
    # ...while the activity itself keeps the best practice score.
    act = client.get(f"/api/program?profile_id={profile}").json()["days"][0]["activities"][0]
    assert act["result"]["attempts"] == 2 and act["result"]["best_score"] == 99.0


def test_completing_a_day_unlocks_the_next(client, profile):
    body = client.get(f"/api/program?profile_id={profile}").json()
    assert [d["status"] for d in body["days"][:3]] == ["available", "locked", "locked"]

    with services():
        for a in body["days"][0]["activities"]:
            assert _post(client, profile, 1, a["id"]).json()["program"]["counted"]

    body = client.get(f"/api/program?profile_id={profile}").json()
    assert [d["status"] for d in body["days"][:3]] == ["completed", "available", "locked"]
    assert body["summary"]["current_day"] == 2
    assert body["summary"]["completed_days"] == 1
    assert body["summary"]["finished_a_day_today"] is True


def test_benchmark_history_combines_parts_and_averages_weeks(client, profile):
    with services():
        for day in (1, 2, 8):
            _post(client, profile, day, "benchmark-read")
            _post(client, profile, day, "benchmark-speak")
    hist = client.get(f"/api/program/benchmarks?profile_id={profile}").json()
    assert [e["day"] for e in hist["entries"]] == [1, 2, 8]
    e = hist["entries"][0]
    # speak composite 74.4; daily = .4*84 + .6*74.4 = 78.24 -> 78.2
    assert (e["read_score"], e["speak_score"], e["score"]) == (84.0, 74.4, 78.2)
    assert e["filler_rate_per_min"] == 2.0 and e["structure"] == 60
    assert [(w["week"], w["days"]) for w in hist["weeks"]] == [(1, 2), (2, 1)]
    assert hist["baseline"] == hist["latest"] == 78.2


def test_benchmarks_unknown_profile_404(client):
    assert client.get("/api/program/benchmarks?profile_id=999").status_code == 404
    assert client.get("/api/program?profile_id=999").status_code == 404
