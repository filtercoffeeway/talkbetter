"""Phase 1 — Filler words + speaking pace + pauses (local, no API key).

Pure-Python analysis over the Transcript. No external calls, so this is the
first thing to get working end to end.

IMPLEMENTATION NOTES (for the dev session):
  - words_per_minute = total_words / (duration_sec / 60).
  - Fillers: count occurrences of FILLER_WORDS (case-insensitive). Multi-word
    fillers ("you know", "i mean", "sort of", "kind of") need phrase matching
    over the token stream, not just single-word counts.
  - long_pauses: walk consecutive word timings; if next.start - prev.end >
    PAUSE_THRESHOLD_SEC, increment.
  - filler_rate_per_min normalizes fillers by duration so clips are comparable.
"""
from app.models.schemas import FillerStat, PaceFillerReport, Transcript

FILLER_WORDS = [
    "um", "uh", "er", "ah", "like", "so", "well",
    "you know", "i mean", "sort of", "kind of", "basically", "actually", "literally",
]
PAUSE_THRESHOLD_SEC = 1.5


def analyze(transcript: Transcript) -> PaceFillerReport:
    """Compute pace + filler statistics from a Transcript.

    TODO(Phase 1): implement. Replace the stub below.
    """
    raise NotImplementedError(
        "Implement filler/pace analysis. See docstring + docs/spec.html (Phase 1)."
    )
