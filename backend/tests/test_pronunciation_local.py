"""Tests for the local pronunciation scorer.

The wav2vec2 model and espeak-ng are replaced with a tiny fake vocabulary and
synthetic per-frame probabilities, so these run fast and offline. They check
the scoring logic (alignment, allowances, omissions, fluency), not the model's
accuracy — that was checked against real speech separately.
"""
import re
from unittest.mock import patch

import numpy as np
import pytest

from app.services import pronunciation_local as pl

BLANK = 0
PHONES = ["ɹ", "ɛ", "d", "k", "æ", "t", "ʌ", "ɑːɹ", "ɑː", "ə", "n", "ð", "ɾ", "w", "ɔː", "ɚ", "ɔ", "eɪ"]
VOCAB = {p: i + 1 for i, p in enumerate(PHONES)}
FAKE_MODEL = pl._Model(
    feature_extractor=None, model=None, token_to_id=VOCAB, blank_id=BLANK, max_token_len=3,
)
ESPEAK_WORDS = {
    "red": "ɹ_ˈɛ_d", "cat": "k_ˈæ_t", "car": "k_ˈɑːɹ", "and": "ˈæ_n_d",
    "the": "ð_ə", "water": "w_ˈɔː_ɾ_ɚ", "on": "ˈɔ_n",
}
FUSED = {"on the": "ɔ_n_ð_ə"}      # espeak writes some word pairs as one chunk


def _fake_espeak(text: str, voice: str) -> str:
    for pair, ipa in FUSED.items():
        text = text.lower().replace(pair, "@")
    return " ".join(
        FUSED["on the"] if w == "@" else ESPEAK_WORDS[w.lower()]
        for w in re.findall(r"[@\w']+", text)
    )


def _log_probs(frames: list[str | None]) -> np.ndarray:
    """One frame per entry: the named phoneme (or blank, for None) gets 0.9."""
    n_vocab = len(VOCAB) + 1
    probs = np.full((len(frames), n_vocab), 0.1 / (n_vocab - 1))
    for f, phone in enumerate(frames):
        probs[f, VOCAB[phone] if phone else BLANK] = 0.9
    return np.log(probs)


def _assess(frames: list[str | None], reference: str):
    with (
        patch.object(pl, "_get_model", return_value=FAKE_MODEL),
        patch.object(pl, "_espeak_ipa", side_effect=_fake_espeak),
        patch.object(pl, "to_pcm_16k", return_value=np.zeros(len(frames) * 320, dtype=np.float32)),
        patch.object(pl, "_log_probs", return_value=_log_probs(frames)),
    ):
        return pl.assess(b"audio", reference)


def _speak(*phones: str, gap: int = 1) -> list[str | None]:
    """Frames for phones spoken in order, each followed by `gap` blank frames."""
    frames: list[str | None] = [None]
    for p in phones:
        frames += [p] + [None] * gap
    return frames


def _problems(report) -> list[tuple[str, str]]:
    return [(w.word, w.error_type) for w in report.problem_words]


# ---------- Building blocks ----------

def test_tokenize_uses_espeak_phoneme_boundaries():
    # "ɑːɹ" stays one token even though "ɑː" also exists; stress marks are dropped.
    assert pl._tokenize_ipa("k_ˈɑːɹ", FAKE_MODEL) == ["k", "ɑːɹ"]
    assert pl._tokenize_ipa("ɹ_ˈɛ_d k_ˈæ_t\n", FAKE_MODEL) == ["ɹ", "ɛ", "d", "k", "æ", "t"]


def test_fused_words_get_their_own_phonemes_back():
    with patch.object(pl, "_espeak_ipa", side_effect=_fake_espeak):
        expected = pl._expected_phonemes(["on", "the", "cat"], FAKE_MODEL)
    by_word = [[e.phoneme for e in expected if e.word == wi] for wi in range(3)]
    assert by_word == [["ɔ", "n"], ["ð", "ə"], ["k", "æ", "t"]]


def test_align_prefers_matches_and_reports_gaps():
    a, b = "kæt", "kt"
    ops = pl._align(3, 2, lambda i, j: float(a[i] != b[j]), lambda i: 1.0)
    assert ops == [(0, 0), (1, None), (2, 1)]


# ---------- End to end (with the fakes) ----------

def test_clean_reading_scores_high_with_no_problem_words():
    report = _assess(_speak("ɹ", "ɛ", "d", "k", "æ", "t"), "Red cat.")
    assert report.accuracy_score > 90
    assert report.completeness_score == 100
    assert report.fluency_score == 100
    assert report.pron_score > 90
    assert report.problem_words == []


def test_wrong_vowel_flags_the_word():
    # "cat" said as "cut": ʌ where æ is expected.
    report = _assess(_speak("ɹ", "ɛ", "d", "k", "ʌ", "t"), "Red cat.")
    assert _problems(report) == [("cat", "Mispronunciation")]
    cat = report.problem_words[0]
    assert [p.phoneme for p in cat.phonemes] == ["k", "æ", "t"]
    assert cat.phonemes[1].accuracy < 25
    assert cat.phonemes[0].accuracy > 90


def test_american_variants_are_accepted():
    # "water" with ɑː (cot–caught merger) and a flapped t is standard American.
    report = _assess(_speak("w", "ɑː", "ɾ", "ɚ", gap=3), "water")
    assert report.problem_words == []


def test_composite_tokens_match_their_parts():
    # espeak's single "ɑːɹ" token vs the model hearing ɑː + ɹ separately.
    report = _assess(_speak("k", "ɑː", "ɹ", gap=4), "car")
    assert report.problem_words == []


def test_weak_form_of_function_word_is_accepted():
    # "red and cat" with "and" reduced to ən (vowel reduced, final d dropped).
    report = _assess(_speak("ɹ", "ɛ", "d", "ə", "n", "k", "æ", "t"), "red and cat")
    assert report.problem_words == []
    assert report.completeness_score == 100


def test_skipped_word_is_an_omission():
    report = _assess(_speak("ɹ", "ɛ", "d") + [None] * 10, "Red cat.")
    assert _problems(report) == [("cat", "Omission")]
    assert report.completeness_score == 50
    assert report.accuracy_score > 90       # accuracy only counts spoken words


def test_long_pause_between_words_lowers_fluency():
    frames = _speak("ɹ", "ɛ", "d") + [None] * 50 + _speak("k", "æ", "t")   # ~1s gap
    report = _assess(frames, "Red cat.")
    assert report.fluency_score < 60
    assert report.problem_words == []


def test_too_short_recording_counts_everything_as_omitted():
    report = _assess([None, "ɹ"], "Red cat.")
    assert report.pron_score == 0
    assert {w.error_type for w in report.problem_words} == {"Omission"}


def test_reference_without_pronounceable_words_is_rejected():
    with pytest.raises(ValueError):
        _assess(_speak("ɹ"), "!!! ...")
