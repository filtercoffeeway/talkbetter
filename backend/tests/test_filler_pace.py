"""Phase 1 unit tests — start here, no API keys required.

Run from backend/:  pytest

These tests are intentionally written against the schema so the dev session
can implement filler_pace.analyze() to make them pass (TDD-friendly).
"""
import pytest

from app.models.schemas import Transcript, WordTiming


def _mk_transcript() -> Transcript:
    # "um i think this is like really good" over ~6s
    words = [
        WordTiming(word="um", start=0.0, end=0.4),
        WordTiming(word="i", start=2.0, end=2.2),     # ~1.6s gap -> long pause
        WordTiming(word="think", start=2.2, end=2.6),
        WordTiming(word="this", start=2.6, end=2.9),
        WordTiming(word="is", start=2.9, end=3.1),
        WordTiming(word="like", start=3.1, end=3.4),
        WordTiming(word="really", start=3.4, end=3.9),
        WordTiming(word="good", start=3.9, end=4.3),
    ]
    return Transcript(text="um i think this is like really good", words=words, duration_sec=6.0)


@pytest.mark.skip(reason="enable once filler_pace.analyze is implemented (Phase 1)")
def test_counts_fillers_and_pace():
    from app.services import filler_pace

    report = filler_pace.analyze(_mk_transcript())
    assert report.total_words == 8
    assert report.filler_total == 2          # "um" + "like"
    assert report.long_pauses == 1           # the ~1.6s gap
    assert report.words_per_minute == pytest.approx(80.0, abs=1)
