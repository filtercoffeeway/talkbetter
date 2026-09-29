"""Phase 2 — Grammar + clarity feedback via an LLM (Anthropic or OpenAI)."""
from __future__ import annotations

import json

from pydantic import BaseModel

from app.config import settings
from app.models.schemas import (
    ClarityFeedback,
    GrammarIssue,
    LanguageReport,
    PaceFillerReport,
    SpeakingAssessment,
)

_SYSTEM = (
    "You are an ESL speaking coach helping a non-native English speaker improve "
    "toward clear, natural American English. The text below is an automatic "
    "speech-to-text transcript of something they SAID. Judge only what a listener "
    "would hear.\n"
    "Flag only spoken errors: wrong verb tense or form, subject-verb agreement, "
    "missing or wrong articles (a/an/the), wrong prepositions, wrong word order, "
    "wrong or unnatural word choice, plural/singular mistakes, incomplete or "
    "run-on thoughts that confuse the meaning.\n"
    "NEVER flag punctuation, commas, capitalization, spelling, hyphenation, "
    "one-word vs two-word spellings (everyday / every day), or how numbers are "
    "written. The transcription software chose those, not the speaker. Treat "
    "sentence boundaries as unknown. If a word looks like a mis-transcription of a "
    "similar-sounding word, don't correct its meaning — ignore it.\n"
    "If there are no spoken errors, return an empty grammar_issues list. "
    "corrected_text is the transcript with only those spoken errors fixed "
    "(you may add punctuation for readability). The clarity score rates how easy "
    "the message is to follow when heard: a clear point, logical order, concise "
    "wording.\n"
    "Return ONLY a JSON object — no prose, no markdown — with this exact shape:\n"
    '{"corrected_text": "<transcript with spoken errors fixed>", '
    '"grammar_issues": [{"original": "<wrong phrase>", "suggestion": "<correct phrase>", "explanation": "<brief reason>"}], '
    '"clarity": {"score": <0-100>, "summary": "<one sentence>", "suggestions": ["<tip>", ...]}}'
)


# 30-day program: rubric for open-ended answers. Fixed anchors + a schema-enforced
# reply keep scores comparable from day 1 to day 30 — don't loosen them mid-program.
_SPEAKING_SYSTEM = (
    "You are an experienced spoken-English coach assessing a non-native speaker who "
    "wants to sound confident and natural in American English. You get the question "
    "they answered, measured delivery stats, and an automatic transcript (it may lack "
    "punctuation — judge the speaking, not transcription quirks).\n"
    "Score each dimension 0-100 using these anchors:\n"
    "confidence — 90+: direct, committed statements, no hedging, complete sentences, "
    "steady pace, few fillers. 70: mostly direct; some hedges ('I think maybe'), "
    "restarts or fillers. 50: frequent hedging, trailing or abandoned sentences, many "
    "fillers or long pauses. 30 or less: hesitant fragments, gives up mid-answer.\n"
    "structure (the thought process) — 90+: answers the question in the first "
    "sentence, gives a clear reason and a concrete example, logical transitions, a "
    "clean close. 70: clear point but thin support or loose order. 50: the point "
    "appears late or the answer wanders. 30 or less: no discernible point.\n"
    "vocabulary — 90+: precise, natural, idiomatic word choice with good range. 70: "
    "adequate but plain or repetitive. 50: frequent unnatural or wrong word choices. "
    "30 or less: very limited.\n"
    "Return ONLY a JSON object — no prose, no markdown — with this exact shape:\n"
    '{"confidence": <0-100>, "structure": <0-100>, "vocabulary": <0-100>, '
    '"summary": "<one or two sentences>", '
    '"strengths": ["<specific strength>", ...], '
    '"improvements": ["<specific, actionable change>", ...], '
    '"stronger_version": "<their answer rephrased the way a confident, fluent '
    'American speaker would say it, keeping their ideas, similar length>"}'
)


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return text


def _parse(raw: str) -> LanguageReport:
    """Parse model output to LanguageReport, stripping markdown fences."""
    data = json.loads(_strip_fences(raw))
    return LanguageReport(
        corrected_text=data["corrected_text"],
        grammar_issues=[GrammarIssue(**g) for g in data.get("grammar_issues", [])],
        clarity=ClarityFeedback(**data["clarity"]),
    )


def _call_anthropic(text: str, system: str, schema: type[BaseModel]) -> str:
    """Structured output: the reply is validated against ``schema`` by the API/SDK.

    No temperature — current Claude models reject sampling parameters; the fixed
    rubric anchors plus a schema are what keep scores consistent. max_tokens is
    generous because thinking (on by default) counts toward it.
    """
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.parse(
        model=settings.anthropic_model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": text}],
        output_format=schema,
    )
    if msg.stop_reason == "refusal" or msg.parsed_output is None:
        raise ValueError(f"LLM returned no usable output (stop_reason={msg.stop_reason})")
    return msg.parsed_output.model_dump_json()


def _call_openai(text: str, system: str, schema: type[BaseModel]) -> str:
    import openai as _openai
    client = _openai.OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content


def _call(text: str, system: str, schema: type[BaseModel]) -> str:
    """Return the model's JSON reply as a string (schema-enforced on Anthropic)."""
    call = _call_anthropic if settings.llm_provider == "anthropic" else _call_openai
    return call(text, system, schema)


def is_available() -> bool:
    """True when the configured provider has an API key."""
    key = (
        settings.anthropic_api_key
        if settings.llm_provider == "anthropic"
        else settings.openai_api_key
    )
    return bool(key)


def analyze(text: str) -> LanguageReport:
    """Run grammar + clarity analysis on transcript text."""
    try:
        return _parse(_call(text, _SYSTEM, LanguageReport))
    except (json.JSONDecodeError, KeyError):
        # retry once asking model to return only JSON
        return _parse(_call(f"Return ONLY the JSON, no commentary:\n{text}", _SYSTEM, LanguageReport))


def assess_speaking(text: str, prompt: str, pace: PaceFillerReport) -> SpeakingAssessment:
    """Score an open-ended spoken answer for confidence, structure and vocabulary.

    Delivery stats go in alongside the transcript because confidence is heard as
    much as read: fillers, long pauses and pace are strong signals the text alone
    hides.
    """
    fillers = ", ".join(f"{f.word} x{f.count}" for f in pace.fillers) or "none"
    message = (
        f"Question: {prompt}\n"
        f"Delivery: {pace.duration_sec:.0f} s, {pace.words_per_minute:.0f} words/min, "
        f"{pace.filler_total} fillers ({pace.filler_rate_per_min:.1f}/min: {fillers}), "
        f"{pace.long_pauses} pauses over 1.5 s.\n"
        f"Transcript:\n{text}"
    )
    raw = _call(message, _SPEAKING_SYSTEM, SpeakingAssessment)
    try:
        return SpeakingAssessment(**json.loads(_strip_fences(raw)))
    except (json.JSONDecodeError, TypeError, ValueError):
        raw = _call("Return ONLY the JSON, no commentary.\n" + message,
                    _SPEAKING_SYSTEM, SpeakingAssessment)
        return SpeakingAssessment(**json.loads(_strip_fences(raw)))
