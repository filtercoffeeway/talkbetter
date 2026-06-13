"""Shared pytest fixtures for TalkBetter backend tests."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.schemas import (
    ClarityFeedback,
    FillerStat,
    GrammarIssue,
    LanguageReport,
    PaceFillerReport,
    Transcript,
    WordTiming,
)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    """Point the DB at a fresh temp file for every test."""
    db_file = tmp_path / "test.db"
    with patch.object(settings, "db_path", db_file):
        # Re-init schema in the temp DB
        from app import db
        db.init_db()
        yield db_file


@pytest.fixture()
def client(tmp_db):
    """FastAPI TestClient with DB already initialised."""
    from app.main import app
    with TestClient(app) as c:
        yield c


# ---- Canned service return values ----

FAKE_TRANSCRIPT = Transcript(
    text="I went to the store um you know yesterday",
    words=[
        WordTiming(word="I",         start=0.0,  end=0.2),
        WordTiming(word="went",      start=0.3,  end=0.6),
        WordTiming(word="to",        start=0.7,  end=0.8),
        WordTiming(word="the",       start=0.9,  end=1.0),
        WordTiming(word="store",     start=1.1,  end=1.5),
        WordTiming(word="um",        start=1.6,  end=1.8),
        WordTiming(word="you",       start=3.4,  end=3.6),  # 1.6s gap -> long pause
        WordTiming(word="know",      start=3.7,  end=3.9),
        WordTiming(word="yesterday", start=4.0,  end=4.6),
    ],
    duration_sec=5.0,
)

FAKE_PACE = PaceFillerReport(
    words_per_minute=108.0,
    total_words=9,
    duration_sec=5.0,
    long_pauses=1,
    fillers=[FillerStat(word="um", count=1), FillerStat(word="you know", count=1)],
    filler_total=2,
    filler_rate_per_min=24.0,
)

FAKE_LANGUAGE = LanguageReport(
    corrected_text="I went to the store yesterday.",
    grammar_issues=[
        GrammarIssue(
            original="I went to the store um you know yesterday",
            suggestion="I went to the store yesterday",
            explanation="Remove filler words for clarity.",
        )
    ],
    clarity=ClarityFeedback(
        score=72,
        summary="Generally clear but informal.",
        suggestions=["Avoid filler words like 'um' and 'you know'."],
    ),
)


@pytest.fixture()
def mock_transcribe():
    with patch("app.services.transcription.transcribe", return_value=FAKE_TRANSCRIPT) as m:
        yield m


@pytest.fixture()
def mock_pace():
    with patch("app.services.filler_pace.analyze", return_value=FAKE_PACE) as m:
        yield m


@pytest.fixture()
def mock_llm():
    with patch("app.services.llm_feedback.analyze", return_value=FAKE_LANGUAGE) as m:
        yield m
