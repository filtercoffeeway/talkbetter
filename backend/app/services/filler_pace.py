"""Phase 1 — Filler words + speaking pace + pauses (local, no API key)."""
from __future__ import annotations

from app.models.schemas import FillerStat, PaceFillerReport, Transcript

FILLER_WORDS = [
    "you know", "i mean", "sort of", "kind of",  # multi-word first
    "um", "uh", "er", "ah", "like", "so", "well",
    "basically", "actually", "literally",
]
PAUSE_THRESHOLD_SEC = 1.5


def analyze(transcript: Transcript) -> PaceFillerReport:
    """Compute pace + filler statistics from a Transcript."""
    duration = transcript.duration_sec or 1.0
    words = transcript.words

    total_words = len(words)
    wpm = total_words / (duration / 60.0)

    # Count long pauses between consecutive words
    long_pauses = 0
    for i in range(1, len(words)):
        gap = words[i].start - words[i - 1].end
        if gap > PAUSE_THRESHOLD_SEC:
            long_pauses += 1

    # Filler detection over lowercased token stream
    tokens = [w.word.lower().strip(".,!?;:\"'") for w in words]
    filler_counts: dict[str, int] = {}

    i = 0
    while i < len(tokens):
        matched = False
        for filler in FILLER_WORDS:
            parts = filler.split()
            end = i + len(parts)
            if tokens[i : end] == parts:
                filler_counts[filler] = filler_counts.get(filler, 0) + 1
                i = end
                matched = True
                break
        if not matched:
            i += 1

    filler_total = sum(filler_counts.values())
    filler_rate = filler_total / (duration / 60.0)

    fillers = [
        FillerStat(word=w, count=c)
        for w, c in sorted(filler_counts.items(), key=lambda x: -x[1])
    ]

    return PaceFillerReport(
        words_per_minute=round(wpm, 1),
        total_words=total_words,
        duration_sec=round(duration, 2),
        long_pauses=long_pauses,
        fillers=fillers,
        filler_total=filler_total,
        filler_rate_per_min=round(filler_rate, 2),
    )
