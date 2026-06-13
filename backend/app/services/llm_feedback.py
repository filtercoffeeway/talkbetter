"""Phase 2 — Grammar + clarity feedback via an LLM.

Provider is pluggable (settings.llm_provider): "anthropic" (default) or "openai".
Send the transcript text, get back structured corrections + a clarity rating.

IMPLEMENTATION NOTES (for the dev session):
  - Prompt the model to return STRICT JSON matching LanguageReport:
        { "corrected_text": str,
          "grammar_issues": [{ "original", "suggestion", "explanation" }],
          "clarity": { "score": 0-100, "summary", "suggestions": [str] } }
    Use a system prompt that frames the model as an ESL speaking coach for a
    non-native speaker aiming at clear, natural American English.
  - Parse JSON defensively; if parsing fails, retry once asking for JSON only.
  - Keep the provider behind a small dispatch so swapping is one setting.
"""
from app.config import settings
from app.models.schemas import LanguageReport


def analyze(text: str) -> LanguageReport:
    """Run grammar + clarity analysis on transcript text.

    TODO(Phase 2): implement. Dispatch on settings.llm_provider.
    """
    raise NotImplementedError(
        "Implement LLM grammar/clarity analysis. See docstring + docs/spec.html (Phase 2)."
    )
