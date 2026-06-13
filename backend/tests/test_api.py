"""Integration tests for all TalkBetter API endpoints.

Services that require external resources (Whisper model, LLM keys, Azure) are
mocked so the suite runs anywhere with no downloads or credentials.
A temporary SQLite DB is used for profile/history tests (see conftest.py).

Run from backend/:  pytest
"""
import io
from unittest.mock import patch

import pytest

from tests.conftest import FAKE_LANGUAGE, FAKE_PACE, FAKE_TRANSCRIPT


# ---------- /api/health ----------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------- /api/profiles ----------

def test_list_profiles_empty(client):
    r = client.get("/api/profiles")
    assert r.status_code == 200
    assert r.json() == []


def test_create_profile(client):
    r = client.post("/api/profiles", json={"name": "Mahesh"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Mahesh"
    assert data["id"] == 1
    assert data["session_count"] == 0


def test_create_profile_duplicate_returns_existing(client):
    r1 = client.post("/api/profiles", json={"name": "Mahesh"})
    r2 = client.post("/api/profiles", json={"name": "mahesh"})   # case-insensitive
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_create_profile_blank_name(client):
    r = client.post("/api/profiles", json={"name": "   "})
    assert r.status_code == 400


def test_list_profiles_after_create(client):
    client.post("/api/profiles", json={"name": "Alice"})
    client.post("/api/profiles", json={"name": "Bob"})
    r = client.get("/api/profiles")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Alice" in names
    assert "Bob" in names


# ---------- /api/history ----------

def test_history_unknown_profile_returns_404(client):
    r = client.get("/api/history?profile_id=999")
    assert r.status_code == 404


def test_history_empty_for_new_profile(client):
    client.post("/api/profiles", json={"name": "Mahesh"})
    r = client.get("/api/history?profile_id=1")
    assert r.status_code == 200
    body = r.json()
    assert body["profile_id"] == 1
    assert body["sessions"] == []
    assert body["current_streak"] == 0


# ---------- /api/analyze ----------

def _audio_file(content=b"fake-audio-bytes"):
    return ("recording.webm", io.BytesIO(content), "audio/webm")


def test_analyze_phase1_only(client, mock_transcribe, mock_pace):
    """Phase 1 works; language and accent sections absent when no keys set."""
    r = client.post("/api/analyze", files={"audio": _audio_file()})
    assert r.status_code == 200
    body = r.json()
    assert body["transcript"]["text"] == FAKE_TRANSCRIPT.text
    assert body["pace_fillers"]["filler_total"] == FAKE_PACE.filler_total
    assert body["pace_fillers"]["long_pauses"] == FAKE_PACE.long_pauses
    assert body["language"] is None
    assert body["accent"] is None
    assert body["session_id"] is None


def test_analyze_phase2_with_llm_key(client, mock_transcribe, mock_pace, mock_llm):
    """Phase 2 fires when an API key is configured."""
    with patch("app.routers.analysis.settings") as s:
        s.llm_provider = "anthropic"
        s.anthropic_api_key = "sk-ant-test"
        s.azure_speech_key = ""
        r = client.post("/api/analyze", files={"audio": _audio_file()})
    assert r.status_code == 200
    body = r.json()
    assert body["language"]["clarity"]["score"] == FAKE_LANGUAGE.clarity.score
    assert len(body["language"]["grammar_issues"]) == 1


def test_analyze_persists_session_with_profile(client, mock_transcribe, mock_pace):
    """When profile_id provided, session is saved and session_id returned."""
    client.post("/api/profiles", json={"name": "Mahesh"})
    r = client.post(
        "/api/analyze",
        files={"audio": _audio_file()},
        data={"profile_id": "1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == 1

    hist = client.get("/api/history?profile_id=1").json()
    assert len(hist["sessions"]) == 1
    assert hist["sessions"][0]["total_words"] == FAKE_PACE.total_words


def test_analyze_unknown_profile_returns_404(client, mock_transcribe, mock_pace):
    r = client.post(
        "/api/analyze",
        files={"audio": _audio_file()},
        data={"profile_id": "999"},
    )
    assert r.status_code == 404


def test_analyze_multiple_sessions_updates_profile_count(client, mock_transcribe, mock_pace):
    client.post("/api/profiles", json={"name": "Mahesh"})
    for _ in range(3):
        client.post(
            "/api/analyze",
            files={"audio": _audio_file()},
            data={"profile_id": "1"},
        )
    profiles = client.get("/api/profiles").json()
    assert profiles[0]["session_count"] == 3


# ---------- filler_pace unit tests ----------

from app.models.schemas import Transcript, WordTiming


def _make_transcript():
    return Transcript(
        text="um i think this is like really good",
        words=[
            WordTiming(word="um",     start=0.0, end=0.4),
            WordTiming(word="i",      start=2.0, end=2.2),   # ~1.6s gap -> long pause
            WordTiming(word="think",  start=2.2, end=2.6),
            WordTiming(word="this",   start=2.6, end=2.9),
            WordTiming(word="is",     start=2.9, end=3.1),
            WordTiming(word="like",   start=3.1, end=3.4),
            WordTiming(word="really", start=3.4, end=3.9),
            WordTiming(word="good",   start=3.9, end=4.3),
        ],
        duration_sec=6.0,
    )


def test_filler_pace_counts_fillers():
    from app.services import filler_pace
    r = filler_pace.analyze(_make_transcript())
    assert r.total_words == 8
    assert r.filler_total == 2          # "um" + "like"
    assert r.long_pauses == 1           # ~1.6s gap after "um"
    assert r.words_per_minute == pytest.approx(80.0, abs=1)


def test_filler_pace_multi_word_filler():
    from app.services import filler_pace
    t = Transcript(
        text="you know i mean so",
        words=[
            WordTiming(word="you",  start=0.0, end=0.3),
            WordTiming(word="know", start=0.4, end=0.6),
            WordTiming(word="i",    start=0.7, end=0.8),
            WordTiming(word="mean", start=0.9, end=1.1),
            WordTiming(word="so",   start=1.2, end=1.4),
        ],
        duration_sec=10.0,
    )
    r = filler_pace.analyze(t)
    fillers_map = {f.word: f.count for f in r.fillers}
    assert fillers_map.get("you know") == 1
    assert fillers_map.get("i mean") == 1
    assert fillers_map.get("so") == 1
    assert r.filler_total == 3
