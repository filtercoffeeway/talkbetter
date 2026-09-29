"""30-day, 30-minute spoken-English program — the content.

Every day has the same shape (~30 minutes):

  Daily benchmark (5 min)   — identical difficulty every day, the ground truth:
      1. read the SAME passage aloud              -> pronunciation score
      2. answer a 90-second opinion question     -> fillers, pace, confidence,
         (topic rotates, format never changes)      structure, clarity
  Pronunciation (8 min)     — two sentences drilling that day's sounds
  Speaking practice (17 min)— two open answers practicing a technique
                              (fillers, structure, conversation, confidence)

Weeks build on each other: sounds + filler awareness -> rhythm + structured
thinking -> real conversations -> confidence under pressure. Review days
(7, 14, 21, 28) repeat earlier prompts so you can hear the difference.

Activity ids ("pron-1", "speak-2", ...) and day numbers are the keys progress
is stored under — don't renumber days or rename ids once people have started.
Text can be edited freely. The benchmark passage and prompt format must NOT
change: that would move the denominator the whole trend is measured against.
Keep sentences free of digits (write "thirty", not "30") so the pronunciation
scorer's phonemizer reads them the way a person would.
"""
from __future__ import annotations

PROGRAM_TITLE = "30 Days to Confident English"
PROGRAM_DESCRIPTION = (
    "Thirty minutes a day for thirty days. Every session starts with the same "
    "five-minute benchmark so you can watch your score climb week by week, then "
    "moves on to pronunciation drills and speaking practice that build from clear "
    "sounds to confident, well-structured conversation."
)
DAILY_MINUTES = 30

# ---------------------------------------------------------------------------
# The daily benchmark. FIXED — see module docstring before touching.
# ---------------------------------------------------------------------------
# ~50 words, ~20-25 s aloud (Azure's single-shot assessment caps near 30 s).
# Covers th, v/w, r, dark l, flap t, -ed endings, æ, schwa and word stress.
BENCHMARK_READ_TEXT = (
    "Three weeks ago, my brother Victor visited our office. We walked around the "
    "water tower, talked about better ways to build software, and laughed about "
    "the weather. Honestly, the thirty minute rule really works: practice a little "
    "every day, and the results will follow."
)
BENCHMARK_SPEAK_SECONDS = 90
BENCHMARK_SPEAK_INSTRUCTIONS = (
    "Don't prepare — start within five seconds. Give your answer in the first "
    "sentence, then one reason and one real example, then close. Aim for 90 seconds. "
    "Only your first take of the day counts."
)
BENCHMARK_DESCRIPTION = (
    "Same passage, same 90-second question format, every day. Only your first take "
    "counts, so the score is an honest measure you can compare week to week."
)

# One per day. All the same difficulty: familiar topic, opinion + reason + example.
BENCHMARK_PROMPTS = [
    "Is it better to live in a big city or a small town?",
    "What is the best way to learn a new skill?",
    "Should people work four days a week instead of five?",
    "Is it better to save money or to spend it on experiences?",
    "What makes a good manager?",
    "Are smartphones making people less social?",
    "Should children learn a second language at school?",
    "Is it better to travel alone or with friends?",
    "What is one habit that would improve most people's lives?",
    "Should companies let employees choose where they work from?",
    "Is it more important to be talented or hardworking?",
    "What makes a good friend?",
    "Is online learning as good as learning in a classroom?",
    "Should people change jobs often or stay a long time at one company?",
    "What is the most useful invention of the last fifty years?",
    "Is it better to cook at home or eat out?",
    "Is social media good or bad for society?",
    "What makes a team work well together?",
    "Is it better to plan everything or to be spontaneous?",
    "Should public transport be free?",
    "Is it important to have a hobby outside work?",
    "Should people read more books?",
    "Are big companies better to work for than startups?",
    "What makes a city a good place to live?",
    "Is it better to be a specialist or a generalist?",
    "Should people retire early if they can?",
    "Is failure necessary for success?",
    "What is the most important quality in a leader?",
    "Is it better to rent or buy a home?",
    "What is the best advice you have ever received?",
]

# ---------------------------------------------------------------------------
# Weeks
# ---------------------------------------------------------------------------
WEEKS = [
    {
        "week": 1,
        "title": "Foundations — hear yourself",
        "goal": "Fix the sounds that most often mark a non-native accent, and replace "
                "fillers with silent pauses.",
    },
    {
        "week": 2,
        "title": "Rhythm & structured thinking",
        "goal": "Stress the right words, link them smoothly, and organize answers "
                "(PREP, answer-first, STAR) so your thinking sounds clear.",
    },
    {
        "week": 3,
        "title": "Real conversations",
        "goal": "Small talk, questions, disagreeing politely, meetings — the everyday "
                "situations where natural English matters most.",
    },
    {
        "week": 4,
        "title": "Confidence under pressure",
        "goal": "Impromptu answers, interviews, pitching, and handling questions you "
                "can't fully answer — calm, direct, and without fillers.",
    },
]


# ---------------------------------------------------------------------------
# Activity builders — keep the day list below readable.
# ---------------------------------------------------------------------------
def read(aid: str, title: str, text: str, tip: str, minutes: int = 4) -> dict:
    """Read a sentence aloud; scored for pronunciation."""
    return {
        "id": aid, "kind": "read", "skill": "pronunciation", "title": title,
        "minutes": minutes, "instructions": tip, "reference_text": text,
    }


def speak(aid: str, skill: str, title: str, prompt: str, technique: str,
          seconds: int = 60, minutes: int = 8) -> dict:
    """Answer a prompt freely; scored for fillers, pace, confidence, structure, clarity."""
    return {
        "id": aid, "kind": "speak", "skill": skill, "title": title,
        "minutes": minutes, "instructions": technique, "prompt": prompt,
        "target_seconds": seconds,
    }


SILENT_PAUSE = (
    "Silent-pause drill: every time you feel 'um', 'uh', 'like' or 'so' coming, close "
    "your mouth and pause for a full second instead. Silence sounds thoughtful; "
    "fillers sound unsure. Record twice and beat your filler count."
)
PREP = (
    "PREP: Point (your answer, first sentence) → Reason → Example (real and specific) "
    "→ Point again. It keeps your thinking organized and stops you from wandering."
)
ANSWER_FIRST = (
    "Answer first: say your answer in the first five words, then explain. "
    "Don't warm up with 'So, basically, I think that…'."
)
STAR = (
    "STAR: Situation (one sentence), Task (one sentence), Action (most of your time — "
    "say 'I', not 'we'), Result (a number or a clear outcome)."
)

# ---------------------------------------------------------------------------
# The 30 days. Day number = position in this list (1-based).
# ---------------------------------------------------------------------------
DAYS: list[dict] = [
    # ======================= Week 1 — Foundations =======================
    {
        "title": "Baseline day",
        "goal": "Record your first benchmark — the starting line for the whole program. "
                "Then meet two sounds that change meaning, and introduce yourself.",
        "activities": [
            read("pron-1", "Long EE vs short I",
                 "He will sit on the seat and eat a big sweet treat.",
                 "EE (seat, eat, sweet) is long with a smile. I (sit, will, big) is short "
                 "and relaxed. Merging them turns 'sheep' into 'ship'."),
            read("pron-2", "The TH sounds",
                 "Their mother thought these three things were worth the truth.",
                 "Put the tip of your tongue lightly between your teeth and push air. "
                 "Not 'd' (dese) and not 't' (tree for three)."),
            speak("speak-1", "confidence", "Introduce yourself",
                  "Introduce yourself to a new teammate: who you are, what you work on, "
                  "and one thing you enjoy outside work.",
                  "Short sentences, one idea each. When you feel a filler coming, pause "
                  "instead. Finish each sentence with your voice going down."),
            speak("speak-2", "structure", "Explain your job to a ten-year-old",
                  "Explain what you do at work to a ten-year-old.",
                  "No jargon. Start with one everyday comparison ('It's like being the "
                  "plumber for a big building…'), then one concrete example.",
                  minutes=9),
        ],
    },
    {
        "title": "Pause, don't fill",
        "goal": "V and W, the bright American A — and the single most useful habit: "
                "silent pauses instead of fillers.",
        "activities": [
            read("pron-1", "V versus W",
                 "We were very worried while we waved at the wet van.",
                 "V: top teeth touch your lower lip and buzz. W: round your lips like "
                 "'oo', no teeth at all. 'Very' and 'worried' should feel different."),
            read("pron-2", "The American A (cat, black)",
                 "The happy cat sat on a black mat and grabbed a snack.",
                 "Drop your jaw and spread your lips — wider than you think. 'Cat' is not "
                 "'ket' and not 'cut'."),
            speak("speak-1", "fillers", "Your morning routine",
                  "Walk me through your morning routine, from waking up to starting work.",
                  SILENT_PAUSE),
            speak("speak-2", "fillers", "Your favorite meal",
                  "Describe your favorite meal and how it is made.",
                  SILENT_PAUSE, minutes=9),
        ],
    },
    {
        "title": "The American R and past-tense stories",
        "goal": "A real American R, clean -ed endings, and telling a story in order.",
        "activities": [
            read("pron-1", "The American R",
                 "Robert drove a red car around the corner near the river.",
                 "Pull your tongue back and don't let it tap the roof of your mouth. "
                 "Americans say the R after vowels too: car, corner, river."),
            read("pron-2", "-ED endings",
                 "I walked, talked, and laughed, then waited and wanted more.",
                 "Three sounds: T after voiceless sounds (walked = walkt), D after voiced "
                 "(played), and an extra syllable only after T or D (wait-ed, want-ed)."),
            speak("speak-1", "conversation", "Last weekend",
                  "What did you do last weekend?",
                  "Tell it in order with past-tense verbs (went, saw, tried). Land every "
                  "sentence with a falling tone so it sounds finished, not unsure."),
            speak("speak-2", "fillers", "A trip you remember",
                  "Tell me about a trip you remember well.",
                  "When you move to the next part of the story, pause instead of saying "
                  "'and then, um…'. " + SILENT_PAUSE, seconds=90, minutes=9),
        ],
    },
    {
        "title": "The flap T",
        "goal": "The soft American T in 'water' and 'better', and describing things "
                "with concrete details.",
        "activities": [
            read("pron-1", "Flap T inside words",
                 "Betty bought a little bit of better butter and water.",
                 "A T between vowels becomes a quick tap, almost a soft D: "
                 "wa-der, be-der, li-dle."),
            read("pron-2", "Flap T across words",
                 "Get a lot of it at the city market, and put it in the water.",
                 "It happens between words too: 'get a' = 'geda', 'lot of' = 'lodda', "
                 "'put it in' = 'pudidin'."),
            speak("speak-1", "conversation", "A place you love",
                  "Describe a place you love to someone who has never been there.",
                  "Paint a picture: one thing you see, one thing you hear, one thing you "
                  "feel. Concrete details make you sound fluent."),
            speak("speak-2", "structure", "Recommend something",
                  "Recommend a movie, book, or show to a friend.",
                  "Recommendation first, then two reasons, then who would enjoy it most.",
                  minutes=9),
        ],
    },
    {
        "title": "Stress, schwa & PREP",
        "goal": "The lazy vowel and stressed syllables that give English its rhythm — "
                "and PREP, the structure you'll use for the rest of the program.",
        "activities": [
            read("pron-1", "The schwa (uh)",
                 "A banana and a lemon cost about a dollar at the market today.",
                 "Unstressed syllables collapse to a quick 'uh': b-uh-NA-n-uh, "
                 "LEM-uhn, uh-BOUT, DOL-er. Don't pronounce every vowel fully."),
            read("pron-2", "Stress changes meaning",
                 "I'd like to record a record and present a special present.",
                 "Nouns stress the first syllable (a REC-ord, a PRES-ent); verbs stress "
                 "the second (to re-CORD, to pre-SENT)."),
            speak("speak-1", "structure", "PREP: home or office?",
                  "Is working from home better than working in the office?",
                  PREP, seconds=90),
            speak("speak-2", "structure", "PREP: should everyone code?",
                  "Should everyone learn to code?", PREP, minutes=9),
        ],
    },
    {
        "title": "L sounds & signposting",
        "goal": "Light and dark L, voiced S endings, and signposts that give your "
                "listener a map.",
        "activities": [
            read("pron-1", "Light L and dark L",
                 "Little Bill will likely call all the loyal players well.",
                 "At the start of a word the L is light (little, likely). At the end it's "
                 "dark — the back of the tongue rises: Bill, call, all, well."),
            read("pron-2", "Z endings",
                 "She loves dogs, cars, and games, and he always plays his songs.",
                 "After a voiced sound, a final S is really a buzzing Z: dogz, carz, "
                 "gamez, playz. A hissing S sounds foreign here."),
            speak("speak-1", "structure", "Make your favorite drink",
                  "Explain how to make your favorite drink.",
                  "Signposts: First… Next… After that… Finally. They guide your listener "
                  "and give you thinking time without fillers."),
            speak("speak-2", "structure", "How your team ships work",
                  "Explain how your team takes a piece of work from idea to done.",
                  "Signposts again, and one sentence per step.", seconds=90, minutes=9),
        ],
    },
    {
        "title": "Week 1 review",
        "goal": "Mix the week's sounds, then re-record Day 1's introduction and hear the "
                "difference.",
        "activities": [
            read("pron-1", "Review: V, W, TH, R, flap T",
                 "Victor thought the weather was better, so we walked to the river.",
                 "Check each sound from this week: V-ictor, TH-ought, wea-TH-er, "
                 "be-d-er (flap), walk-t, R-iver."),
            read("pron-2", "Review: L, TH, flap T",
                 "The little bottle of water was worth thirty dollars.",
                 "Dark L at the end of little and bottle, flap T in water and thirty, "
                 "TH in worth and thirty."),
            speak("speak-1", "confidence", "Rematch: introduce yourself",
                  "Introduce yourself to a new teammate: who you are, what you work on, "
                  "and one thing you enjoy outside work.",
                  "Same prompt as Day 1. Compare fillers and pace with that recording in "
                  "the Progress tab."),
            speak("speak-2", "confidence", "What you noticed",
                  "What did you notice about your own speaking this week?",
                  "Use direct 'I' statements without hedging: 'I noticed…', not "
                  "'I think maybe I kind of noticed…'.", minutes=9),
        ],
    },
    # ================== Week 2 — Rhythm & structured thinking ==================
    {
        "title": "Sentence stress & answer-first",
        "goal": "Stress the words that carry meaning, and put your answer first.",
        "activities": [
            read("pron-1", "Content words carry the stress",
                 "The manager wants the report on her desk by Friday morning.",
                 "Stress nouns, main verbs and adjectives (MANager, WANTS, rePORT, DESK, "
                 "FRIday, MORNing). Squash the small words: the, on, her, by."),
            read("pron-2", "Stress shifts meaning",
                 "I never said she stole my money, I just implied it.",
                 "Put the strongest stress on NEVER, then on imPLIED. Same words, "
                 "different stress, different meaning."),
            speak("speak-1", "structure", "Answer first: your most useful skill",
                  "What is the most useful skill you have?", ANSWER_FIRST),
            speak("speak-2", "structure", "Answer first: an extra hour",
                  "What would you do with an extra hour every day?", ANSWER_FIRST,
                  minutes=9),
        ],
    },
    {
        "title": "Linking & small talk",
        "goal": "Connect words the way native speakers do, and never give a one-word "
                "answer in small talk.",
        "activities": [
            read("pron-1", "Consonant to vowel linking",
                 "Pick it up and turn it on, then take it all in at once.",
                 "A final consonant jumps onto the next vowel: pi-ki-tup, tur-ni-ton, "
                 "ta-ki-tall-in. It should sound like one smooth line."),
            read("pron-2", "Linking in everyday phrases",
                 "Put it on the table and leave it alone for an hour.",
                 "pu-di-ton (flap T + linking), lea-vi-ta-lone, for-an-hour."),
            speak("speak-1", "conversation", "How's your week going?",
                  "A colleague asks: how's your week going?",
                  "Answer + one detail + a question back: 'Busy but good — we finally "
                  "launched the new feature. How about yours?'"),
            speak("speak-2", "structure", "A recent decision",
                  "Explain a decision you made recently and why you made it.",
                  "Situation → the options you had → what you chose → why.",
                  seconds=90, minutes=9),
        ],
    },
    {
        "title": "Reductions & contractions",
        "goal": "Sound relaxed, not textbook: gonna, wanna, I'll, we're.",
        "activities": [
            read("pron-1", "Reductions",
                 "I'm gonna have to go, but I wanna see what you've got to say.",
                 "In casual speech 'going to' becomes gonna and 'want to' becomes wanna. "
                 "Using them in conversation sounds natural, not lazy."),
            read("pron-2", "Contractions",
                 "Let me know if you need anything, and I'll get back to you.",
                 "I'll, you'll, we're, it's — full forms like 'I will' sound stiff and "
                 "formal in conversation."),
            speak("speak-1", "conversation", "Weekend plans",
                  "Tell a friend about your plans for this weekend.",
                  "Use contractions and reductions on purpose: I'm, I'll, we're gonna, "
                  "I wanna."),
            speak("speak-2", "fillers", "Your hobby",
                  "Talk about a hobby or interest you have.",
                  "Target: fewer than three fillers per minute. " + SILENT_PAUSE,
                  seconds=90, minutes=9),
        ],
    },
    {
        "title": "Questions & intonation",
        "goal": "Rising and falling tones, and asking questions that keep a "
                "conversation alive.",
        "activities": [
            read("pron-1", "Yes/no vs either/or",
                 "Are you coming today, or should I just go without you?",
                 "'Are you coming today' rises; the final choice 'without you' falls."),
            read("pron-2", "WH-questions fall",
                 "Where did you grow up, and what do you miss about it?",
                 "Questions starting with where/what/why/how usually FALL at the end. "
                 "Rising sounds unsure."),
            speak("speak-1", "conversation", "Meet a new colleague",
                  "You meet a new colleague. Ask them three good questions, with a short "
                  "comment before each one.",
                  "Open questions (what, how, why) start conversations; yes/no questions "
                  "end them. Comment first: 'I heard you moved from Austin — what's "
                  "the biggest difference?'"),
            speak("speak-2", "conversation", "Your hometown",
                  "Describe your hometown to someone who has never been there.",
                  "One surprising fact, one thing you miss, one thing you'd recommend.",
                  minutes=9),
        ],
    },
    {
        "title": "STAR stories",
        "goal": "The held T, and telling work stories that show what YOU did.",
        "activities": [
            read("pron-1", "The held T (button, kitten)",
                 "The kitten hit the button and bit a certain cotton mitten.",
                 "Before an 'n' sound, Americans stop the air and release through the "
                 "nose: bu'n, ki'n, cer'n. Don't pronounce a full T."),
            read("pron-2", "-ED endings in context",
                 "I started the project in August, and we shipped it right on time.",
                 "start-ed (extra syllable after T), ship-t (voiceless), "
                 "and link 'shipped it' = ship-tit."),
            speak("speak-1", "structure", "STAR: a hard problem",
                  "Tell me about a time you solved a hard problem at work.",
                  STAR, seconds=120),
            speak("speak-2", "confidence", "The same story in 60 seconds",
                  "Tell the same story again in 60 seconds.",
                  "Cut everything that isn't Action or Result. Shorter sounds more "
                  "confident.", minutes=9),
        ],
    },
    {
        "title": "Comparing & contrasting",
        "goal": "Hard TH clusters, stress in long words, and comparing two options "
                "clearly.",
        "activities": [
            read("pron-1", "TH workout",
                 "Thirty thousand people gathered there on Thursday to thank the author.",
                 "Voiceless TH (thirty, thousand, Thursday, thank, author) and voiced TH "
                 "(gathered, there, the). Tongue between the teeth every time."),
            read("pron-2", "Stress in long words",
                 "Honestly, the development of this technology is particularly important.",
                 "de-VEL-op-ment, tech-NOL-o-gy, par-TIC-u-lar-ly, im-POR-tant. "
                 "Wrong stress makes long words hard to recognize."),
            speak("speak-1", "structure", "City vs small town",
                  "Compare living in a city with living in a small town.",
                  "Contrast words: 'On one hand… on the other hand', 'while', 'however'. "
                  "Finish with which you prefer and why.", seconds=90),
            speak("speak-2", "conversation", "Two tools you've used",
                  "Compare two phones, laptops, or apps you have used.",
                  "Pick three points of comparison and keep the same order for both.",
                  minutes=9),
        ],
    },
    {
        "title": "Week 2 review",
        "goal": "Rematch Day 5's PREP question, and explain something technical simply.",
        "activities": [
            read("pron-1", "Review: stress + flap T",
                 "Honestly, I thought the little meeting went better than we expected.",
                 "HON-est-ly, li-dle, be-der, ex-PECT-ed. Squash 'than we'."),
            read("pron-2", "Review: reductions + linking",
                 "We're gonna need a bigger budget, but it's worth it.",
                 "we're-gonna, nee-da, bu-dit's (linking), wor-thit."),
            speak("speak-1", "structure", "Rematch: home or office?",
                  "Is working from home better than working in the office?",
                  "Same prompt as Day 5. " + PREP, seconds=90),
            speak("speak-2", "structure", "Explain a technical idea simply",
                  "Explain a technical concept from your work to a non-technical friend.",
                  "Analogy first, then the real definition, then one example of where "
                  "it's used.", seconds=90, minutes=9),
        ],
    },
    # ======================= Week 3 — Real conversations =======================
    {
        "title": "Thought groups",
        "goal": "Speak in chunks with short pauses — it sounds calm and gives you time "
                "to think.",
        "activities": [
            read("pron-1", "Chunking a long sentence",
                 "When I moved to a new city, I didn't know anyone, so I joined a "
                 "running club.",
                 "Three chunks: 'When I moved to a new city' / 'I didn't know anyone' / "
                 "'so I joined a running club'. Tiny pause between, no fillers."),
            read("pron-2", "A polite request in chunks",
                 "If you have a minute after lunch, could you look at my notes for "
                 "the meeting?",
                 "Two chunks. Rise gently on 'lunch', then a smooth question."),
            speak("speak-1", "conversation", "Coffee-machine small talk",
                  "You bump into a colleague at the coffee machine. Make small talk: "
                  "the weekend, the weather, and one follow-up question.",
                  "Comment, share, ask — at least three turns. Keep it light."),
            speak("speak-2", "conversation", "Something in the news",
                  "Talk about a recent news story or trend that caught your attention.",
                  "What happened, why it caught your eye, what you think will happen "
                  "next.", seconds=90, minutes=9),
        ],
    },
    {
        "title": "Numbers & data",
        "goal": "Say numbers so nobody asks 'thirteen or thirty?', and talk about data "
                "with confidence.",
        "activities": [
            read("pron-1", "Teen vs ty",
                 "Thirteen is not thirty, and fifteen is not fifty.",
                 "-TEEN is stressed and long: thir-TEEN. -TY is stressed on the first "
                 "part, with a flap T: THIR-dy, FIF-dy."),
            read("pron-2", "Numbers in a sentence",
                 "Our revenue grew by eighteen percent to almost four million dollars.",
                 "REV-e-nue, eigh-TEEN, per-CENT, MIL-lion."),
            speak("speak-1", "structure", "Describe a trend",
                  "Describe something that changed over the past year, with numbers: "
                  "your spending, your time, or your work.",
                  "Big number first, then what it means: 'Up twenty percent — our best "
                  "quarter so far.'"),
            speak("speak-2", "confidence", "A project status update",
                  "Give a status update on a project you are working on.",
                  "Where it stands, what's next, any risk. Short statements that end "
                  "with a falling tone.", minutes=9),
        ],
    },
    {
        "title": "Disagreeing politely",
        "goal": "Push back without sounding rude — or apologizing too much.",
        "activities": [
            read("pron-1", "Softened disagreement",
                 "I see your point, but I'd look at it a little differently.",
                 "Warm tone on 'I see your point', slight stress on DIFFerently."),
            read("pron-2", "Honest and calm",
                 "That's a fair question, and honestly, I'm not sure we're there yet.",
                 "Calm and steady. Link 'fair question' and 'not sure'."),
            speak("speak-1", "conversation", "Disagree: meetings",
                  "A colleague says: 'Meetings are a waste of time.' Disagree politely.",
                  "Acknowledge → your view → your reason → invite a reply. 'I see why "
                  "you'd say that, but…'"),
            speak("speak-2", "confidence", "Push back on a deadline",
                  "Your manager asks for something by Friday that will take two weeks. "
                  "Push back.",
                  "Stay calm, state facts, offer an alternative. Don't over-apologize — "
                  "one 'I understand' is enough.", minutes=9),
        ],
    },
    {
        "title": "Warm, clear tone",
        "goal": "Deliver bad news and say no without sounding cold or unsure.",
        "activities": [
            read("pron-1", "Empathy",
                 "I'm really sorry to hear that. Let me know how I can help.",
                 "Slower and a little softer. Stress REALly and HELP."),
            read("pron-2", "No, plus an alternative",
                 "Unfortunately, we can't approve it this month, but here's what we can do.",
                 "American 'can't' has the bright A and a held T: kæn't. Stress CAN'T "
                 "and CAN to show the contrast."),
            speak("speak-1", "conversation", "Say no nicely",
                  "Decline an invitation to a weekend event from a coworker.",
                  "Thanks → no → brief reason → something positive. No long excuses."),
            speak("speak-2", "conversation", "Deliver bad news",
                  "Tell your team that a launch is delayed by two weeks.",
                  "News first, reason second, next step third.", minutes=9),
        ],
    },
    {
        "title": "Phrasal verbs",
        "goal": "The everyday verbs native speakers actually use — and the linking that "
                "comes with them.",
        "activities": [
            read("pron-1", "Phrasal verbs at work",
                 "Let's figure it out, look into it, and follow up on Monday.",
                 "figu-ri-dout, loo-kin-to-it, follo-wup. The particle (out, into, up) "
                 "gets the stress."),
            read("pron-2", "Phrasal verbs in a story",
                 "I ran into an old friend and we caught up over coffee.",
                 "ra-nin-to-an-old, caugh-dup (flap T). Stress UP."),
            speak("speak-1", "conversation", "Three phrasal verbs",
                  "Tell a short story about a problem you solved, using 'figure out', "
                  "'run into', and 'come up with'.",
                  "Phrasal verbs sound more natural than 'resolve', 'encounter', "
                  "'devise' in conversation."),
            speak("speak-2", "conversation", "Gave up or took up",
                  "What is something you gave up or took up recently, and why?",
                  "Answer first, then the story behind it.", minutes=9),
        ],
    },
    {
        "title": "Meetings",
        "goal": "Clarify, ask for detail, and give crisp updates in meetings.",
        "activities": [
            read("pron-1", "Clarifying",
                 "Just to clarify, are we shipping on Tuesday or Thursday?",
                 "Rise on Tuesday, fall on Thursday (either/or). TH in Thursday."),
            read("pron-2", "Asking for detail",
                 "Could you walk me through the numbers one more time?",
                 "'Could you' = cou-ju. Silent L in walk. Falling tone at the end — "
                 "it's a polite request."),
            speak("speak-1", "confidence", "Stand-up update",
                  "Give your stand-up update: yesterday, today, and any blockers.",
                  "Three parts, one or two sentences each. No 'so basically'."),
            speak("speak-2", "conversation", "Ask for clarity",
                  "Your manager gave you vague instructions for a task. Ask for "
                  "clarification.",
                  "Paraphrase what you understood, then ask one precise question.",
                  minutes=9),
        ],
    },
    {
        "title": "Week 3 review",
        "goal": "A two-minute monologue, and a rematch of Day 8's answer-first question.",
        "activities": [
            read("pron-1", "Review: numbers + phrasal verbs",
                 "Thirteen people showed up, so we figured it out together over lunch.",
                 "thir-TEEN, show-dup, figu-ri-dout, to-GETH-er."),
            read("pron-2", "Review: disagreement + request",
                 "I see your point, but could you walk me through it one more time?",
                 "Warm on the first half, cou-ju, silent L in walk."),
            speak("speak-1", "conversation", "Someone who influenced you",
                  "Talk about a person who influenced you and what you learned from them.",
                  "Story, then lesson. Pauses — not fillers — between the parts.",
                  seconds=120),
            speak("speak-2", "structure", "Rematch: your most useful skill",
                  "What is the most useful skill you have?",
                  "Same prompt as Day 8. " + ANSWER_FIRST, minutes=9),
        ],
    },
    # ================== Week 4 — Confidence under pressure ==================
    {
        "title": "Impromptu speaking",
        "goal": "Start talking within three seconds and trust your structure.",
        "activities": [
            read("pron-1", "Emphasis",
                 "This is the most important thing we'll do all year.",
                 "Hit MOST and imPORtant hard; everything else light. Emphasis is "
                 "confidence you can hear."),
            read("pron-2", "Contrastive emphasis",
                 "We didn't just meet the goal, we beat it by a mile.",
                 "Contrast MEET with BEAT. Flap T in 'beat it'."),
            speak("speak-1", "confidence", "Impromptu: change your city",
                  "What would you change about your city?",
                  "Start within three seconds. First sentence = your answer. Then PREP."),
            speak("speak-2", "confidence", "Impromptu: advice you disagree with",
                  "What is a common piece of advice you disagree with?",
                  "Start within three seconds. State it plainly — no 'I'm not sure, but "
                  "maybe…'.", minutes=9),
        ],
    },
    {
        "title": "Tell me about yourself",
        "goal": "Statements that end low (no uptalk), and the interview opener "
                "you'll use for years.",
        "activities": [
            read("pron-1", "Statements end low",
                 "I lead the platform team, and I love solving hard problems.",
                 "Let your voice fall at the end. Rising at the end of a statement "
                 "(uptalk) makes it sound like a question."),
            read("pron-2", "Experience, stated plainly",
                 "I have about ten years of experience building reliable software systems.",
                 "ex-PE-ri-ence, re-LI-a-ble, SOFT-ware, SYS-tems. Fall on 'systems'."),
            speak("speak-1", "confidence", "Tell me about yourself",
                  "Tell me about yourself. (Interview)",
                  "Present → past → future: what you do now, how you got here, why this "
                  "next step. Under 90 seconds.", seconds=90),
            speak("speak-2", "confidence", "Your greatest strength",
                  "What is your greatest strength? Give proof.",
                  "Name it in one sentence, then one specific example with a result.",
                  minutes=9),
        ],
    },
    {
        "title": "Explaining your work",
        "goal": "Pronounce the long words of your job correctly, and tell your best "
                "project story.",
        "activities": [
            read("pron-1", "Technical words",
                 "Our architecture is specifically designed for reliability and scalability.",
                 "AR-chi-tec-ture, spe-CIF-i-cal-ly, re-li-a-BIL-i-ty, "
                 "sca-la-BIL-i-ty."),
            read("pron-2", "Action verbs in the past",
                 "We analyzed the data, identified the issue, and deployed a fix within "
                 "an hour.",
                 "analyzed (-d), identified (-d), deployed (-d) — voiced endings, no "
                 "extra syllable."),
            speak("speak-1", "structure", "A project you're proud of",
                  "Tell me about a project you are proud of.", STAR, seconds=120),
            speak("speak-2", "structure", "A trade-off",
                  "Tell me about a time you had to choose between speed and quality.",
                  "The two options, what you chose, why, and what you'd do differently.",
                  seconds=90, minutes=9),
        ],
    },
    {
        "title": "Pace & persuasion",
        "goal": "Slow down on what matters, and pitch an idea people say yes to.",
        "activities": [
            read("pron-1", "Slow down for the key point",
                 "Here is the key point. Slow down, pause, and let it land.",
                 "Read it slower than feels natural. Pause after 'point'."),
            read("pron-2", "List intonation",
                 "If we start now, we'll save time, money, and a lot of stress.",
                 "Lists go up, up, down: time ↗, money ↗, a lot of stress ↘."),
            speak("speak-1", "confidence", "Pitch an idea",
                  "Pitch an idea to improve something at your work.",
                  "Problem → idea → benefit → ask. Slow down on the benefit."),
            speak("speak-2", "confidence", "Convince a friend",
                  "Convince a friend to try your favorite hobby.",
                  "Lead with what THEY get out of it, not what you like about it.",
                  minutes=9),
        ],
    },
    {
        "title": "Buying time without fillers",
        "goal": "Phrases that give you thinking time, and answering honestly when you "
                "don't know.",
        "activities": [
            read("pron-1", "Thinking phrase",
                 "That's a great question. Let me think about that for a second.",
                 "Say it calmly and slowly — it replaces a string of 'um's and sounds "
                 "in control."),
            read("pron-2", "Honest 'I don't know'",
                 "I don't know the exact number, but I can find out by tomorrow.",
                 "Fall on 'number', then a confident rise into the offer."),
            speak("speak-1", "confidence", "A tough interview question",
                  "Why should we hire you over someone with more experience?",
                  "Open with a thinking phrase instead of 'um' ('That's a fair "
                  "question…'), then PREP.", seconds=90),
            speak("speak-2", "confidence", "Partly know the answer",
                  "Explain how interest rates affect the housing market.",
                  "Say what you know, admit what you don't, say how you'd find out. "
                  "Honesty sounds confident; bluffing doesn't.", minutes=9),
        ],
    },
    {
        "title": "Storytelling",
        "goal": "Vary your pace and tone so people want to keep listening.",
        "activities": [
            read("pron-1", "Building tension",
                 "It was late, it was raining, and suddenly the lights went out.",
                 "Slow and low for the setting, then speed up on 'suddenly'."),
            read("pron-2", "The twist",
                 "Believe it or not, that small mistake turned out to be the best thing "
                 "that happened.",
                 "be-lie-vi-dor-not (linking + flap), tur-ne-dout. Stress BEST."),
            speak("speak-1", "conversation", "A memorable story",
                  "Tell a funny or memorable story from your life.",
                  "Hook, setting, problem, twist, ending. Slow for tension, faster for "
                  "action.", seconds=120),
            speak("speak-2", "confidence", "The same story, shorter",
                  "Tell the same story in 45 seconds.",
                  "Keep the hook and the twist; cut the rest.", seconds=45, minutes=9),
        ],
    },
    {
        "title": "Week 4 review",
        "goal": "Rematch Day 1 and Day 5 — the clearest proof of how far you've come.",
        "activities": [
            read("pron-1", "Rematch: Day 7 sentence",
                 "Victor thought the weather was better, so we walked to the river.",
                 "Same as Day 7 — compare your score."),
            read("pron-2", "Review: thinking phrase + linking",
                 "That's a great question, and honestly, I think we can figure it out "
                 "together.",
                 "Calm pace, figu-ri-dout, to-GETH-er."),
            speak("speak-1", "confidence", "Rematch: introduce yourself",
                  "Introduce yourself to a new teammate: who you are, what you work on, "
                  "and one thing you enjoy outside work.",
                  "Same prompt as Day 1 and Day 7. Compare all three."),
            speak("speak-2", "structure", "Rematch: should everyone code?",
                  "Should everyone learn to code?",
                  "Same prompt as Day 5. " + PREP, minutes=9),
        ],
    },
    {
        "title": "Mock interview",
        "goal": "Put it all together under realistic pressure.",
        "activities": [
            read("pron-1", "Closing warmly",
                 "It's been a pleasure talking with you, and I'm looking forward to "
                 "working together.",
                 "Warm tone, link 'looking forward to', fall at the end."),
            read("pron-2", "A good question to ask",
                 "Could you tell me a little more about the team and the role?",
                 "cou-ju, li-dle (flap), falling tone for a polite request."),
            speak("speak-1", "confidence", "Mock: disagreeing with a manager",
                  "Tell me about a time you disagreed with your manager.",
                  STAR + " Show respect and a clear outcome.", seconds=90),
            speak("speak-2", "confidence", "Mock: a project falling behind",
                  "What do you do when a project is falling behind?",
                  "Answer first, then a real example. Thinking phrase if you need time.",
                  seconds=90, minutes=9),
        ],
    },
    {
        "title": "Graduation",
        "goal": "Your final benchmark, and a plan to keep improving after day 30.",
        "activities": [
            read("pron-1", "Looking back",
                 "Thirty days ago I started, and today I speak with more confidence.",
                 "THIR-dy (flap), con-fi-dence. Let it fall with pride at the end."),
            read("pron-2", "Keep going",
                 "Practice a little every day, and the results will follow.",
                 "PRAC-tice, re-SULTS (Z ending), FOL-low."),
            speak("speak-1", "confidence", "What I learned in thirty days",
                  "What did you learn about your English in the last thirty days?",
                  "Specific changes, with examples. Direct 'I' statements.", seconds=120),
            speak("speak-2", "structure", "My plan from here",
                  "What is your plan to keep improving your English?",
                  "Answer first, then three concrete habits.", minutes=9),
        ],
    },
]

assert len(DAYS) == 30 and len(BENCHMARK_PROMPTS) == 30
