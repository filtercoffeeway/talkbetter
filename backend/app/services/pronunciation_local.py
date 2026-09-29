"""Phase 3 — American-accent scoring, fully local (no API key).

Selected with PRONUNCIATION_PROVIDER=local (the default). Needs `espeak-ng` on
the host plus torch/transformers; the model (~1.2 GB) downloads on first use.

How it works
  1. Expected pronunciation: espeak-ng turns the reference sentence into
     American English IPA phonemes (`-v en-us`). The whole sentence is done at
     once so connected-speech forms come out right ("a" -> ɐ, "it up" -> ɪɾʌp);
     each phoneme is then assigned to its word by aligning against the
     word-by-word pronunciations.
  2. What was said: a wav2vec2 CTC model (settings.pronunciation_model) trained
     on the same espeak phoneme set emits the phonemes it hears, with a
     probability for every ~20ms frame.
  3. The expected and heard phonemes are edit-aligned. An expected phoneme that
     lines up with an acceptable heard one scores the model's confidence in
     it; a substituted one scores the (low) confidence that it was said anyway;
     a missing one scores 0. Acceptable = the phoneme itself, normal American
     variants (e.g. ɑː for ɔː in "water"), and weak forms of function words
     ("and" -> ən).
  4. A word with no correctly heard phoneme is an Omission; otherwise it is a
     Mispronunciation if its average is low or any one phoneme clearly failed.
  5. Fluency penalises pauses between words beyond a natural gap.

The output is the same AccentReport the Azure provider returns.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from app.config import settings
from app.models.schemas import AccentReport, PhonemeScore, WordPronunciation
from app.services.audio import SAMPLE_RATE, to_pcm_16k

_ACCURACY_THRESHOLD = 60.0     # word cut-off, same as the Azure provider
_PHONEME_FAIL = 25.0           # a single phoneme this low flags its word
_NATURAL_PAUSE_SEC = 0.3       # inter-word gaps shorter than this are free
_MIN_AUDIO_SEC = 0.25
_PAD_SEC = 0.3                 # silence added around the clip so edge sounds aren't clipped
_SEC_PER_FRAME = 0.02          # wav2vec2 emits one frame per 320 samples at 16kHz

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")
_STRESS_MARKS = str.maketrans("", "", "ˈˌ")
_PHONE_SEP = re.compile(r"[_\s-]+")

# Composite tokens are compared as their parts, so "car" matches whether
# espeak or the model writes it as ɑːɹ or as ɑː + ɹ.
_SPLIT: dict[str, tuple[str, ...]] = {
    "ɑːɹ": ("ɑː", "ɹ"), "ɔːɹ": ("ɔː", "ɹ"), "oːɹ": ("oː", "ɹ"), "ɪɹ": ("ɪ", "ɹ"),
    "ɛɹ": ("ɛ", "ɹ"), "ʊɹ": ("ʊ", "ɹ"), "aɪɚ": ("aɪ", "ɚ"), "aɪə": ("aɪ", "ə"),
    "əl": ("ə", "l"), "l̩": ("ə", "l"), "n̩": ("ə", "n"),
}

# Sounds that are interchangeable in General American, so saying either is
# correct. Lesson targets (æ vs ʌ, ɪ vs iː, ...) stay distinct.
_SAME_SOUND: list[set[str]] = [
    {"ɑː", "ɑ", "ɔː", "ɔ"},   # cot–caught merger: most Americans say "water" with ɑ
    {"ə", "ɐ", "ʌ"},          # near-identical in American English
    {"i", "iː"},
    {"u", "uː"},
    {"ɚ", "ɜː", "ɜ"},
    {"oʊ", "o", "oː"},
    {"eɪ", "e", "eː"},
    {"ɔɪ", "oɪ"},
]
# One-way allowances: the expected sound (key) may also be said as these.
_ALSO_ACCEPT: dict[str, set[str]] = {
    "ᵻ": {"ɪ", "ə", "ɐ"},     # espeak's reduced vowel ("record"); an ɪ must not accept ə
    "t": {"ɾ", "ʔ"},          # flapped/held t, including across words ("sit on")
    "d": {"ɾ"},
    # The model can't reliably hear the glottal stop ("kitten", "button"), so a
    # plain t/d is accepted too; an expected flap ɾ still has to be a flap.
    "ʔ": {"t", "d", "ɾ"},
}
for _group in _SAME_SOUND:
    for _p in _group:
        _ALSO_ACCEPT.setdefault(_p, set()).update(_group - {_p})

_VOWELS = {
    "ə", "ɐ", "ʌ", "æ", "ɛ", "ɪ", "i", "iː", "u", "uː", "ʊ", "eɪ", "ɑː", "ɑ",
    "ɔ", "ɔː", "oʊ", "aɪ", "aʊ", "ɔɪ", "ɚ", "ɜː", "ᵻ",
}
# Function words are usually reduced in running speech; any of these vowels is
# fine for them. Keys are lowercase words.
_WEAK_VOWELS: dict[str, set[str]] = {
    "a": {"ə", "ɐ", "ʌ", "eɪ"},
    "an": {"ə", "ɐ", "æ"},
    "and": {"ə", "ɐ", "æ", "ɛ"},
    "as": {"ə", "ɐ", "æ"},
    "at": {"ə", "ɐ", "æ"},
    "can": {"ə", "ɐ", "æ", "ɛ"},
    "just": {"ə", "ɪ", "ʌ"},
    "of": {"ə", "ɐ", "ʌ"},
    "that": {"ə", "ɐ", "æ"},
    "the": {"ə", "ɐ", "i", "iː", "ɪ"},
    "them": {"ə", "ɐ", "ɛ"},
    "to": {"ə", "ɐ", "ʊ", "u", "uː"},
    "was": {"ə", "ɐ", "ʌ", "ɑː"},
    "you": {"ə", "ɐ", "ʊ", "u", "uː"},
}
# Other per-word allowances: expected sound -> also acceptable ("have to" -> hæf tə).
_WORD_ALLOW: dict[str, dict[str, set[str]]] = {"have": {"v": {"f"}}}
# Final consonants commonly dropped in running speech ("and" -> ən).
_OPTIONAL_FINAL: dict[str, str] = {"and": "d", "just": "t"}


@dataclass
class _Model:
    feature_extractor: Any
    model: Any
    token_to_id: dict[str, int]
    blank_id: int
    max_token_len: int

    def ids_containing(self, sounds: frozenset[str]) -> list[int]:
        """Token ids whose sounds include any of `sounds` (e.g. ɹ -> ɹ, ɑːɹ, ɪɹ, ...)."""
        return sorted(
            i for t, i in self.token_to_id.items() if not sounds.isdisjoint(_SPLIT.get(t, (t,)))
        )


@dataclass
class _Expected:
    phoneme: str              # sound, shown to the user
    accept: frozenset[str]    # sounds that count as saying it
    word: int                 # index into the reference words
    optional: bool = False    # may be dropped without penalty


@dataclass
class _Heard:
    sound: str
    start: int                # first frame
    end: int                  # last frame (inclusive)


_model: _Model | None = None


def _get_model() -> _Model:
    global _model
    if _model is None:
        from huggingface_hub import hf_hub_download
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        name = settings.pronunciation_model
        # The model's own tokenizer class needs the `phonemizer` package; we
        # only need its vocabulary, so read vocab.json directly.
        with open(hf_hub_download(name, "vocab.json"), encoding="utf-8") as f:
            vocab: dict[str, int] = json.load(f)
        model = Wav2Vec2ForCTC.from_pretrained(name).eval()
        phonemes = {t: i for t, i in vocab.items() if not t.startswith("<") and t != "|"}
        _model = _Model(
            feature_extractor=Wav2Vec2FeatureExtractor.from_pretrained(name),
            model=model,
            token_to_id=phonemes,
            blank_id=model.config.pad_token_id,
            max_token_len=max(len(t) for t in phonemes),
        )
    return _model


# ---------- Expected pronunciation (espeak-ng) ----------

def _tokenize_ipa(ipa: str, m: _Model) -> list[str]:
    """Split `_`-separated espeak output into phonemes the model knows.

    The model was trained on espeak's own phoneme segmentation, so almost every
    phoneme is a vocab entry as-is. Anything else falls back to greedy
    longest-match within that phoneme.
    """
    phones: list[str] = []
    for phone in _PHONE_SEP.split(ipa.translate(_STRESS_MARKS)):
        if not phone:
            continue
        if phone in m.token_to_id:
            phones.append(phone)
            continue
        i = 0
        while i < len(phone):
            for size in range(min(m.max_token_len, len(phone) - i), 0, -1):
                if phone[i : i + size] in m.token_to_id:
                    phones.append(phone[i : i + size])
                    i += size
                    break
            else:
                i += 1   # symbol the model doesn't know (rare) — skip it
    return phones


@lru_cache(maxsize=4096)
def _espeak_ipa(text: str, voice: str) -> str:
    """American IPA for `text`, phonemes separated by `_`, words by spaces."""
    return subprocess.run(
        ["espeak-ng", "-q", "--ipa", "--sep=_", "-v", voice, text],
        capture_output=True, text=True, check=True,
    ).stdout


def _expected_phonemes(words: list[str], m: _Model) -> list[_Expected]:
    """Connected-speech phonemes for the sentence, each tagged with its word."""
    voice = settings.espeak_voice
    isolated = [(wi, p) for wi, w in enumerate(words) for p in _tokenize_ipa(_espeak_ipa(w, voice), m)]
    connected = _tokenize_ipa(_espeak_ipa(" ".join(words), voice), m)

    # espeak sometimes fuses words ("on the" -> ɔnðə), so recover word
    # ownership by aligning the sentence phonemes to the per-word ones.
    owner: list[int | None] = [None] * len(connected)
    for i, j in _align(
        len(isolated), len(connected),
        sub_cost=lambda i, j: 0.0 if isolated[i][1] == connected[j] else 1.0,
        del_cost=lambda i: 1.0,
    ):
        if i is not None and j is not None:
            owner[j] = isolated[i][0]
    last = next((o for o in owner if o is not None), 0)
    for j, o in enumerate(owner):          # extra sentence phonemes join the previous word
        owner[j] = last = o if o is not None else last

    if set(owner) != {wi for wi, _ in isolated}:
        # A word lost all its phonemes in the merge — use word-by-word instead.
        owner, connected = [wi for wi, _ in isolated], [p for _, p in isolated]

    sounds = [(sound, wi) for phone, wi in zip(connected, owner) for sound in _SPLIT.get(phone, (phone,))]
    expected: list[_Expected] = []
    for j, (sound, wi) in enumerate(sounds):
        word = words[wi].lower()
        accept = {sound} | _ALSO_ACCEPT.get(sound, set()) | _WORD_ALLOW.get(word, {}).get(sound, set())
        if sound in _VOWELS:
            accept |= _WEAK_VOWELS.get(word, set())
        is_last = j + 1 == len(sounds) or sounds[j + 1][1] != wi
        expected.append(
            _Expected(
                phoneme=sound,
                accept=frozenset(accept),
                word=wi,
                optional=is_last and _OPTIONAL_FINAL.get(word) == sound,
            )
        )
    return expected


# ---------- Acoustic model ----------

def _log_probs(wave: np.ndarray, m: _Model) -> np.ndarray:
    """(frames, vocab) log-probabilities from the phoneme model."""
    import torch

    inputs = m.feature_extractor(wave, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    with torch.inference_mode():
        logits = m.model(inputs.input_values).logits[0]
    return torch.log_softmax(logits, dim=-1).numpy()


def _heard_sounds(log_probs: np.ndarray, m: _Model) -> list[_Heard]:
    """Greedy CTC decode: the sounds the model heard, with their frames."""
    id_to_token = {i: t for t, i in m.token_to_id.items()}
    runs: list[tuple[int, int, int]] = []          # (token, start, end)
    prev = m.blank_id
    for f, tok in enumerate(log_probs.argmax(axis=1).tolist()):
        if tok != m.blank_id:
            if tok == prev:
                runs[-1] = (tok, runs[-1][1], f)
            else:
                runs.append((tok, f, f))
        prev = tok
    return [
        _Heard(sound=sound, start=start, end=end)
        for tok, start, end in runs
        if tok in id_to_token
        for sound in _SPLIT.get(id_to_token[tok], (id_to_token[tok],))
    ]


def _confidence(probs: np.ndarray, m: _Model, heard: _Heard, accept: frozenset[str]) -> float:
    """Peak probability (0-1) that an accepted sound was said during `heard`,
    measured among non-blank outputs. The floor on the denominator stops
    near-silent frames from producing spurious highs."""
    frames = probs[heard.start : heard.end + 1]
    said = frames[:, m.ids_containing(accept)].sum(axis=1)
    return float(min(1.0, (said / np.maximum(1.0 - frames[:, m.blank_id], 0.1)).max()))


# ---------- Alignment ----------

def _align(
    n: int, k: int,
    sub_cost: Callable[[int, int], float],
    del_cost: Callable[[int], float],
) -> list[tuple[int | None, int | None]]:
    """Minimum-cost edit alignment of sequences of length n and k (insertions
    cost 1). Returns (i, j) pairs in order: (i, j) paired, (i, None) deleted,
    (None, j) inserted."""
    dist = np.zeros((n + 1, k + 1))
    for i in range(1, n + 1):
        dist[i, 0] = dist[i - 1, 0] + del_cost(i - 1)
    dist[0, 1:] = np.arange(1, k + 1)
    for i in range(1, n + 1):
        for j in range(1, k + 1):
            dist[i, j] = min(
                dist[i - 1, j - 1] + sub_cost(i - 1, j - 1),
                dist[i - 1, j] + del_cost(i - 1),
                dist[i, j - 1] + 1.0,
            )

    ops: list[tuple[int | None, int | None]] = []
    i, j = n, k
    while i > 0 or j > 0:
        if i > 0 and j > 0 and np.isclose(dist[i, j], dist[i - 1, j - 1] + sub_cost(i - 1, j - 1)):
            ops.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and np.isclose(dist[i, j], dist[i - 1, j] + del_cost(i - 1)):
            ops.append((i - 1, None))
            i -= 1
        else:
            ops.append((None, j - 1))
            j -= 1
    return ops[::-1]


# ---------- Public entry point ----------

def assess(audio_bytes: bytes, reference_text: str, src_suffix: str = ".webm") -> AccentReport:
    """Score pronunciation of audio against the reference sentence, locally."""
    m = _get_model()
    words = _WORD_RE.findall(reference_text)
    expected = _expected_phonemes(words, m) if words else []
    if not expected:
        raise ValueError("Reference text has no pronounceable words.")

    wave = to_pcm_16k(audio_bytes, src_suffix)
    if len(wave) < _MIN_AUDIO_SEC * SAMPLE_RATE:
        heard: list[_Heard] = []
        probs = np.zeros((0, 0))
    else:
        pad = np.zeros(int(_PAD_SEC * SAMPLE_RATE), dtype=np.float32)
        log_probs = _log_probs(np.concatenate([pad, wave, pad]), m)
        heard = _heard_sounds(log_probs, m)
        probs = np.exp(log_probs)

    # Pair each expected phoneme with what was heard in its place (or nothing).
    heard_for: dict[int, _Heard] = {}
    for i, j in _align(
        len(expected), len(heard),
        sub_cost=lambda i, j: 0.0 if heard[j].sound in expected[i].accept else 1.0,
        del_cost=lambda i: 0.0 if expected[i].optional else 1.0,
    ):
        if i is not None and j is not None:
            heard_for[i] = heard[j]

    word_results: list[WordPronunciation] = []
    spans: list[tuple[int, int]] = []           # (first, last) frame of spoken words
    for wi, word in enumerate(words):
        scored: list[tuple[str, float]] = []
        frames: list[int] = []
        correct = 0
        for i, e in enumerate(expected):
            if e.word != wi:
                continue
            h = heard_for.get(i)
            if h is None:
                if not e.optional:
                    scored.append((e.phoneme, 0.0))
                continue
            scored.append((e.phoneme, 100.0 * _confidence(probs, m, h, e.accept)))
            frames += [h.start, h.end]
            correct += h.sound in e.accept

        if not scored and not frames:
            continue   # espeak had no phonemes for this word (e.g. a symbol)
        scores = [s for _, s in scored]
        if correct == 0:
            error_type, accuracy = "Omission", 0.0
        else:
            accuracy = float(np.mean(scores))
            spans.append((min(frames), max(frames)))
            # One clearly wrong sound (e.g. "cat" said as "cut") is worth
            # flagging even when the word's average still looks passable.
            bad = accuracy < _ACCURACY_THRESHOLD or min(scores) < _PHONEME_FAIL
            error_type = "Mispronunciation" if bad else None
        word_results.append(
            WordPronunciation(
                word=word,
                accuracy=round(accuracy, 1),
                error_type=error_type,
                phonemes=[PhonemeScore(phoneme=p, accuracy=round(s, 1)) for p, s in scored],
            )
        )

    spoken = [w for w in word_results if w.error_type != "Omission"]
    accuracy_score = float(np.mean([w.accuracy for w in spoken])) if spoken else 0.0
    completeness_score = 100.0 * len(spoken) / len(word_results)

    if spans:
        spans.sort()
        total = (spans[-1][1] - spans[0][0] + 1) * _SEC_PER_FRAME
        excess = sum(
            max(0.0, (nxt[0] - cur[1] - 1) * _SEC_PER_FRAME - _NATURAL_PAUSE_SEC)
            for cur, nxt in zip(spans, spans[1:])
        )
        fluency_score = max(0.0, 100.0 * (1.0 - excess / total))
    else:
        fluency_score = 0.0

    # Share of words with no problem at all. Averaging accuracy alone lets easy
    # words (the, a, and) hide a handful of clearly non-American ones, and
    # completeness is ~100 for anyone reading a script — together they squeezed
    # a US voice (93) and a clearly accented reader (86) into the same band.
    # Omissions count as not clean, so completeness needs no separate weight.
    clean_pct = 100.0 * sum(w.error_type is None for w in word_results) / len(word_results)
    pron_score = 0.45 * accuracy_score + 0.45 * clean_pct + 0.10 * fluency_score

    return AccentReport(
        accuracy_score=round(accuracy_score, 1),
        fluency_score=round(fluency_score, 1),
        completeness_score=round(completeness_score, 1),
        pron_score=round(pron_score, 1),
        problem_words=[w for w in word_results if w.error_type is not None],
    )
