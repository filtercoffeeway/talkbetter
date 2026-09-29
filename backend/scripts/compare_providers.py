"""Score saved accent recordings with both pronunciation providers, side by side.

Record with SAVE_RECORDINGS=true in .env, then from backend/:

    .venv/bin/python -m scripts.compare_providers            # all recordings
    .venv/bin/python -m scripts.compare_providers --latest 5

Azure is skipped when AZURE_SPEECH_KEY/REGION aren't set.
"""
from __future__ import annotations

import argparse

from app.config import settings
from app.models.schemas import AccentReport
from app.services import pronunciation_azure, pronunciation_local


def _summary(report: AccentReport) -> str:
    problems = ", ".join(
        f"{w.word}({'omitted' if w.error_type == 'Omission' else f'{w.accuracy:.0f}'})"
        for w in report.problem_words
    )
    return (
        f"pron {report.pron_score:5.1f}  acc {report.accuracy_score:5.1f}  "
        f"flu {report.fluency_score:5.1f}  comp {report.completeness_score:5.1f}  | {problems or '-'}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--latest", type=int, help="only the N most recent recordings")
    args = parser.parse_args()

    texts = sorted(settings.recordings_dir.glob("*.txt"))
    if args.latest:
        texts = texts[-args.latest:]
    if not texts:
        print(f"No recordings in {settings.recordings_dir} — set SAVE_RECORDINGS=true and record some.")
        return

    providers = [("local", pronunciation_local)]
    if settings.azure_speech_key and settings.azure_speech_region:
        providers.append(("azure", pronunciation_azure))

    for text_path in texts:
        audio = next((p for p in text_path.parent.glob(text_path.stem + ".*") if p.suffix != ".txt"), None)
        if audio is None:
            continue
        reference = text_path.read_text(encoding="utf-8")
        print(f"\n{audio.name}\n  \"{reference}\"")
        for name, provider in providers:
            try:
                print(f"  {name:6} {_summary(provider.assess(audio.read_bytes(), reference, audio.suffix))}")
            except Exception as exc:   # keep going; one bad clip shouldn't stop the comparison
                print(f"  {name:6} failed: {exc}")


if __name__ == "__main__":
    main()
