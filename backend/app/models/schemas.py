"""Pydantic response models — the API contract shared with the frontend.

These define the JSON shape returned by POST /api/analyze. Build them out
phase by phase; fields for later phases can be Optional so early phases
return partial objects. Keep this file in sync with docs/spec.html.
"""
from pydantic import BaseModel


# ---------- Phase 1: transcription + pace + fillers ----------
class WordTiming(BaseModel):
    word: str
    start: float      # seconds
    end: float


class Transcript(BaseModel):
    text: str
    words: list[WordTiming] = []
    duration_sec: float


class FillerStat(BaseModel):
    word: str
    count: int


class PaceFillerReport(BaseModel):
    words_per_minute: float
    total_words: int
    duration_sec: float
    long_pauses: int                 # pauses longer than threshold (e.g. >1.5s)
    fillers: list[FillerStat] = []
    filler_total: int
    filler_rate_per_min: float


# ---------- Phase 2: grammar + clarity (LLM) ----------
class GrammarIssue(BaseModel):
    original: str
    suggestion: str
    explanation: str


class ClarityFeedback(BaseModel):
    score: int                       # 0-100
    summary: str
    suggestions: list[str] = []


class LanguageReport(BaseModel):
    corrected_text: str
    grammar_issues: list[GrammarIssue] = []
    clarity: ClarityFeedback


# ---------- Phase 3: accent (Azure) ----------
class PhonemeScore(BaseModel):
    phoneme: str
    accuracy: float


class WordPronunciation(BaseModel):
    word: str
    accuracy: float
    error_type: str | None = None    # None | "Mispronunciation" | "Omission" | "Insertion"
    phonemes: list[PhonemeScore] = []


class AccentReport(BaseModel):
    accuracy_score: float            # 0-100
    fluency_score: float
    completeness_score: float
    pron_score: float                # overall
    problem_words: list[WordPronunciation] = []


# ---------- Top-level response ----------
class AnalysisResponse(BaseModel):
    transcript: Transcript
    pace_fillers: PaceFillerReport
    language: LanguageReport | None = None     # Phase 2
    accent: AccentReport | None = None         # Phase 3
    session_id: int | None = None              # Phase 4: id of the persisted session
    speaking: "SpeakingAssessment | None" = None   # 30-day program: open-answer rubric (LLM)
    program: "ProgramAttempt | None" = None        # 30-day program: what this attempt recorded


# ---------- Phase 4: profiles + progress tracking ----------
class Profile(BaseModel):
    id: int
    name: str
    created_at: str
    session_count: int = 0


class ProfileCreate(BaseModel):
    name: str


class SessionSummary(BaseModel):
    """One past session, as shown in history lists and trend charts."""
    id: int
    profile_id: int
    created_at: str
    mode: str
    duration_sec: float
    transcript: str
    words_per_minute: float | None = None
    total_words: int | None = None
    long_pauses: int | None = None
    filler_total: int | None = None
    filler_rate_per_min: float | None = None
    clarity_score: int | None = None
    pron_score: float | None = None


class HistoryResponse(BaseModel):
    profile_id: int
    current_streak: int                        # consecutive days practiced (incl. today)
    sessions: list[SessionSummary] = []        # newest first


# ---------- 30-day program: LLM speaking assessment ----------
class SpeakingAssessment(BaseModel):
    """Rubric scores for an open-ended spoken answer (LLM). Anchored rubric +
    a schema-enforced reply keep scores comparable day to day."""
    confidence: int                            # 0-100: direct, committed, no hedging
    structure: int                             # 0-100: thought process — point first, support, close
    vocabulary: int                            # 0-100: range + naturalness of word choice
    summary: str
    strengths: list[str] = []
    improvements: list[str] = []
    stronger_version: str = ""                 # the same answer, said the way a fluent speaker would


class ProgramAttempt(BaseModel):
    """What an /api/analyze call did to the 30-day program (set when program_day was sent)."""
    day: int
    activity_id: str
    counted: bool                              # False if the recording was too short to count
    score: float | None = None                 # this attempt's activity score (0-100)
    benchmark_recorded: bool = False           # True if this was today's first benchmark take
    message: str = ""


# ---------- 30-day program: curriculum + per-profile progress ----------
class ActivityResult(BaseModel):
    attempts: int = 0
    best_score: float | None = None
    last_score: float | None = None
    first_done_at: str | None = None
    last_done_at: str | None = None


class ProgramActivity(BaseModel):
    id: str                                    # stable within its day: the progress key
    section: str                               # "benchmark" | "practice"
    kind: str                                  # "read" (pronunciation-scored) | "speak" (open answer)
    skill: str                                 # "pronunciation" | "fillers" | "structure" | "conversation" | "confidence"
    title: str
    minutes: int
    instructions: str
    reference_text: str | None = None          # kind == "read"
    prompt: str | None = None                  # kind == "speak"
    target_seconds: int | None = None          # kind == "speak"
    result: ActivityResult | None = None       # filled when ?profile_id= is supplied


class ProgramDay(BaseModel):
    day: int                                   # 1-30
    week: int                                  # 1-4 (days 29-30 belong to week 4)
    title: str
    goal: str
    minutes: int
    activities: list[ProgramActivity] = []
    status: str = "locked"                     # "locked" | "available" | "completed"
    completed_at: str | None = None


class ProgramWeek(BaseModel):
    week: int
    title: str
    goal: str


class ProgramSummary(BaseModel):
    current_day: int                           # first day not yet completed (30 when all done)
    completed_days: int
    total_days: int
    finished_a_day_today: bool                 # nudge: next day is best left for tomorrow


class ProgramResponse(BaseModel):
    title: str
    description: str
    daily_minutes: int
    benchmark_description: str
    weeks: list[ProgramWeek] = []
    days: list[ProgramDay] = []
    summary: ProgramSummary | None = None      # present only when profile_id given


class BenchmarkEntry(BaseModel):
    """One program day's benchmark — the first take of each part counts."""
    day: int
    week: int
    date: str                                  # date of the first take that day
    score: float | None = None                 # 0.4 * read + 0.6 * speak (whatever is present)
    read_score: float | None = None            # pron_score on the fixed passage
    speak_score: float | None = None           # speaking composite on the 90-second prompt
    words_per_minute: float | None = None      # speak part
    filler_rate_per_min: float | None = None   # speak part
    long_pauses: int | None = None             # speak part
    confidence: int | None = None
    structure: int | None = None
    clarity: int | None = None


class BenchmarkWeek(BaseModel):
    week: int
    days: int                                  # benchmark days recorded that week
    avg_score: float | None = None
    avg_read_score: float | None = None
    avg_speak_score: float | None = None
    avg_filler_rate_per_min: float | None = None
    avg_confidence: float | None = None
    avg_structure: float | None = None


class BenchmarkHistory(BaseModel):
    profile_id: int
    entries: list[BenchmarkEntry] = []         # oldest first
    weeks: list[BenchmarkWeek] = []
    baseline: float | None = None              # day-1 (first recorded) score
    latest: float | None = None


AnalysisResponse.model_rebuild()
