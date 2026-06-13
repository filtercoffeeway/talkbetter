"""Phase 2 — Grammar + clarity feedback via an LLM (Anthropic or OpenAI)."""
from __future__ import annotations

import json

from app.config import settings
from app.models.schemas import ClarityFeedback, GrammarIssue, LanguageReport

_SYSTEM = (
    "You are an ESL speaking coach helping a non-native English speaker improve "
    "toward clear, natural American English. Analyse the spoken transcript below "
    "for grammar mistakes and overall clarity. "
    "Return ONLY a JSON object — no prose, no markdown — with this exact shape:\n"
    '{"corrected_text": "<full corrected transcript>", '
    '"grammar_issues": [{"original": "<wrong phrase>", "suggestion": "<correct phrase>", "explanation": "<brief reason>"}], '
    '"clarity": {"score": <0-100>, "summary": "<one sentence>", "suggestions": ["<tip>", ...]}}'
)


def _parse(raw: str) -> LanguageReport:
    """Parse model output to LanguageReport, stripping markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    data = json.loads(text)
    return LanguageReport(
        corrected_text=data["corrected_text"],
        grammar_issues=[GrammarIssue(**g) for g in data.get("grammar_issues", [])],
        clarity=ClarityFeedback(**data["clarity"]),
    )


def _call_anthropic(text: str) -> str:
    import anthropic as _anthropic
    client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": text}],
    )
    return msg.content[0].text


def _call_openai(text: str) -> str:
    import openai as _openai
    client = _openai.OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content


def analyze(text: str) -> LanguageReport:
    """Run grammar + clarity analysis on transcript text."""
    raw = (
        _call_anthropic(text)
        if settings.llm_provider == "anthropic"
        else _call_openai(text)
    )
    try:
        return _parse(raw)
    except (json.JSONDecodeError, KeyError):
        # retry once asking model to return only JSON
        retry_prompt = f"Return ONLY the JSON, no commentary:\n{text}"
        raw2 = (
            _call_anthropic(retry_prompt)
            if settings.llm_provider == "anthropic"
            else _call_openai(retry_prompt)
        )
        return _parse(raw2)
