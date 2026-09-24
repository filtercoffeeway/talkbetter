"""American-accent training course (Phase 4 — curriculum + progress overlay).

The *curriculum* is static content that ships with the app: an ordered set of
units, each holding ordered lessons. Every lesson is a short reference sentence
plus coaching notes; reading it aloud feeds the existing Phase 3 accent flow
(``POST /api/analyze`` with ``reference_text`` + ``lesson_id``), which scores
pronunciation. A lesson is "completed" once a profile's ``pron_score`` reaches
``TARGET_SCORE``.

Progress is *per profile* and lives in SQLite (see ``services/storage.py`` and
the ``lesson_progress`` table in ``db.py``). This module just defines the
content and assembles the static curriculum together with a profile's progress
into a :class:`CourseResponse`.

Lesson ids are stable slugs — they are the keys progress is stored under, so
renaming one resets that lesson's history. Add new lessons freely; reordering
or retitling is safe as long as the id stays put.
"""
from __future__ import annotations

from app.models.schemas import (
    CourseProgressSummary,
    CourseResponse,
    CourseUnit,
    Lesson,
    LessonProgress,
)
from app.services import storage

COURSE_TITLE = "American Accent Training"
COURSE_DESCRIPTION = (
    "A guided path through the sounds, rhythm, and melody of American English. "
    "Work through it in order — read each sentence aloud in Accent practice and "
    "aim to hit the target pronunciation score to clear a lesson."
)

# pron_score (0-100) a lesson must reach to count as completed.
TARGET_SCORE = 80.0

# Ordered curriculum. Plain dicts so the content reads like data, not code.
CURRICULUM: list[dict] = [
    {
        "id": "unit-vowels",
        "title": "American Vowels",
        "description": "Vowel length and quality that most often give away a non-native accent.",
        "lessons": [
            {
                "id": "vowel-ee-ih",
                "title": "Long /iː/ vs short /ɪ/",
                "focus": "Distinguish 'sheep' from 'ship' — vowel length changes meaning.",
                "tip": "/iː/ is long and tense (smile); /ɪ/ is short and relaxed. Don't merge them.",
                "reference_text": "He will sit on the seat and eat a big sweet treat.",
                "example_words": ["sheep / ship", "seat / sit", "eat / it", "feel / fill"],
            },
            {
                "id": "vowel-ae",
                "title": "The American /æ/",
                "focus": "The bright, open 'a' in cat, trap, and ask.",
                "tip": "Drop your jaw and spread your lips — it's wider than most languages' 'a'.",
                "reference_text": "The happy cat sat on a black mat and grabbed a snack.",
                "example_words": ["cat", "trap", "back", "ask", "hand"],
            },
            {
                "id": "vowel-schwa",
                "title": "The schwa /ə/ — the lazy vowel",
                "focus": "The neutral, unstressed vowel hiding in most multi-syllable words.",
                "tip": "Unstressed syllables collapse toward 'uh'. Don't pronounce them fully.",
                "reference_text": "About a banana, the problem was a common, casual signal.",
                "example_words": ["about", "banana", "common", "signal", "support"],
            },
            {
                "id": "vowel-ah-uh",
                "title": "/ɑ/ vs /ʌ/ — cot vs cut",
                "focus": "Open back 'ah' versus the central 'uh'.",
                "tip": "/ɑ/ is open with a dropped jaw; /ʌ/ is shorter and more central.",
                "reference_text": "My brother got a hot cup of coffee and a couple of nuts.",
                "example_words": ["cot / cut", "hot / hut", "lock / luck", "body / buddy"],
            },
        ],
    },
    {
        "id": "unit-consonants",
        "title": "Tricky Consonants",
        "description": "The consonants non-native speakers most often substitute or drop.",
        "lessons": [
            {
                "id": "cons-r",
                "title": "The American R",
                "focus": "The retroflex, rhotic 'r' — pronounced even at the ends of words.",
                "tip": "Curl the tongue back without touching the roof; Americans keep the r in 'car'.",
                "reference_text": "Robert drove a red car around the corner near the river.",
                "example_words": ["red", "car", "corner", "river", "world"],
            },
            {
                "id": "cons-th",
                "title": "The TH sounds (think / this)",
                "focus": "Voiceless /θ/ and voiced /ð/ — tongue between the teeth.",
                "tip": "Put your tongue tip lightly between your teeth; don't swap in 't', 'd', 's', or 'z'.",
                "reference_text": "Their mother thought these three things were worth the truth.",
                "example_words": ["think", "this", "three", "mother", "worth"],
            },
            {
                "id": "cons-vw",
                "title": "V versus W",
                "focus": "Teeth-on-lip /v/ vs rounded-lips /w/.",
                "tip": "/v/: top teeth touch bottom lip. /w/: lips round, teeth uninvolved.",
                "reference_text": "We were very worried while we waved at the wet van.",
                "example_words": ["vest / west", "vine / wine", "very", "waved", "van"],
            },
            {
                "id": "cons-l",
                "title": "Light L and Dark L",
                "focus": "The clear 'l' before vowels vs the dark 'l' at the end of words.",
                "tip": "End-of-word 'l' (call, well) is darker — pull the back of the tongue up.",
                "reference_text": "Little Bill will likely call all the loyal players well.",
                "example_words": ["little", "call", "well", "all", "loyal"],
            },
        ],
    },
    {
        "id": "unit-t-sounds",
        "title": "The American T",
        "description": "The T changes shape depending on where it sits — a hallmark of the accent.",
        "lessons": [
            {
                "id": "t-flap",
                "title": "The Flap T (water, better)",
                "focus": "A T between vowels becomes a quick 'd'-like flap.",
                "tip": "'water' sounds like 'wadder'; tap the tongue once, don't fully say 't'.",
                "reference_text": "Betty bought a little bit of better butter and water.",
                "example_words": ["water", "better", "city", "letter", "matter"],
            },
            {
                "id": "t-held",
                "title": "The Held / Glottal T (button, kitten)",
                "focus": "T before an 'n' is swallowed into a stop in the throat.",
                "tip": "'button' = 'buh-tn' with a catch in the throat, not a released 't'.",
                "reference_text": "The kitten hit the button and bit a certain cotton mitten.",
                "example_words": ["button", "kitten", "certain", "cotton", "mountain"],
            },
        ],
    },
    {
        "id": "unit-rhythm",
        "title": "Rhythm & Stress",
        "description": "English is stress-timed — which syllables you punch matters more than evenness.",
        "lessons": [
            {
                "id": "stress-word",
                "title": "Word Stress",
                "focus": "Stressing the wrong syllable can change a word's meaning or part of speech.",
                "tip": "Nouns/verbs can differ by stress: REcord (noun) vs reCORD (verb).",
                "reference_text": "I'd like to record a record and present a special present.",
                "example_words": ["REcord / reCORD", "PREsent / preSENT", "OBject / obJECT"],
            },
            {
                "id": "stress-sentence",
                "title": "Sentence Stress",
                "focus": "Punch the content words; flatten the function words.",
                "tip": "Stress nouns, verbs, adjectives; reduce articles, prepositions, pronouns.",
                "reference_text": "I never said she stole my money, I just implied it.",
                "example_words": ["said", "stole", "money", "implied"],
            },
            {
                "id": "reductions",
                "title": "Reductions (gonna, wanna)",
                "focus": "Casual speech blends words together — gonna, wanna, gotta.",
                "tip": "'going to' → 'gonna', 'want to' → 'wanna'. Natural, not lazy.",
                "reference_text": "I'm gonna have to go, but I wanna see what you've got to say.",
                "example_words": ["gonna", "wanna", "gotta", "kinda", "lemme"],
            },
        ],
    },
    {
        "id": "unit-melody",
        "title": "Intonation & Linking",
        "description": "How words connect and how pitch rises and falls give speech its American melody.",
        "lessons": [
            {
                "id": "linking",
                "title": "Linking & Connected Speech",
                "focus": "Words run together; a final consonant links to a starting vowel.",
                "tip": "'pick it up' → 'pi-ki-tup'. Don't stop between words.",
                "reference_text": "Pick it up and turn it on, then take it all in at once.",
                "example_words": ["pick it up", "turn it on", "take it all"],
            },
            {
                "id": "intonation",
                "title": "Rising & Falling Intonation",
                "focus": "Pitch falls on statements, rises on yes/no questions.",
                "tip": "Yes/no questions rise at the end; statements and wh-questions fall.",
                "reference_text": "Are you coming today, or should I just go without you?",
                "example_words": ["rising: question", "falling: statement"],
            },
        ],
    },
]


def lesson_index() -> dict[str, dict]:
    """Flat ``{lesson_id: lesson_dict}`` map across every unit."""
    return {
        lesson["id"]: lesson
        for unit in CURRICULUM
        for lesson in unit["lessons"]
    }


def get_lesson(lesson_id: str) -> dict | None:
    """Return the static lesson dict for ``lesson_id``, or None if unknown."""
    return lesson_index().get(lesson_id)


def get_course(profile_id: int | None = None) -> CourseResponse:
    """Assemble the curriculum, overlaying ``profile_id``'s progress if given.

    Without a profile this is pure static content (every lesson's ``progress``
    is None and ``summary`` is omitted). With one, each lesson is annotated with
    that profile's standing and a course-level completion summary is included.
    """
    progress_map: dict[str, LessonProgress] = (
        storage.get_lesson_progress(profile_id) if profile_id is not None else {}
    )

    units: list[CourseUnit] = []
    total = completed = attempted = 0
    for unit in CURRICULUM:
        lessons: list[Lesson] = []
        for lesson in unit["lessons"]:
            total += 1
            prog = progress_map.get(lesson["id"])
            if prog is not None:
                if prog.status == "completed":
                    completed += 1
                elif prog.status == "attempted":
                    attempted += 1
            lessons.append(Lesson(**lesson, progress=prog))
        units.append(
            CourseUnit(
                id=unit["id"],
                title=unit["title"],
                description=unit["description"],
                lessons=lessons,
            )
        )

    summary: CourseProgressSummary | None = None
    if profile_id is not None:
        summary = CourseProgressSummary(
            total_lessons=total,
            completed_lessons=completed,
            attempted_lessons=attempted,
            percent_complete=round(100 * completed / total, 1) if total else 0.0,
            target_score=TARGET_SCORE,
        )

    return CourseResponse(
        title=COURSE_TITLE,
        description=COURSE_DESCRIPTION,
        target_score=TARGET_SCORE,
        units=units,
        summary=summary,
    )
