import { useState } from "react";
import Recorder from "./components/Recorder.jsx";
import FeedbackReport from "./components/FeedbackReport.jsx";
import ProfilePicker from "./components/ProfilePicker.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Course from "./components/Course.jsx";
import { analyzeAudio } from "./lib/api.js";

// Top-level views:
//   "practice" -> record + get feedback (Phases 1-3), scoped to a profile
//   "progress" -> Dashboard of that profile's history over time (Phase 4)
//   "course"   -> American-accent course: lessons + per-profile progress (Phase 4)
// Within practice, two modes:
//   "free"   -> filler/pace + grammar/clarity on free speech
//   "accent" -> user reads a reference sentence for pronunciation scoring.
//               Lessons started from the Course view land here with `lesson`set.
export default function App() {
  const [view, setView] = useState("practice");
  const [profile, setProfile] = useState(null);
  const [mode, setMode] = useState("free");
  const [referenceText, setReferenceText] = useState("");
  // The course lesson currently being practiced (null for free-form accent
  // practice). When set, analysis advances that lesson's progress.
  const [lesson, setLesson] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Bumped after each saved session so the Dashboard + Course reload progress.
  const [historyKey, setHistoryKey] = useState(0);

  async function handleRecorded(audioBlob) {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeAudio(
        audioBlob,
        mode === "accent" ? referenceText : null,
        profile?.id,
        mode === "accent" ? lesson?.id : null
      );
      setReport(result);
      setHistoryKey((k) => k + 1); // new session persisted -> refresh dashboard/course
    } catch (e) {
      setError(e.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  // Switching mode by hand detaches any course lesson we were tagging.
  function chooseMode(next) {
    setMode(next);
    if (next !== "accent") setLesson(null);
  }

  // Editing the reference sentence by hand means it's no longer the lesson's.
  function editReference(text) {
    setReferenceText(text);
    setLesson(null);
  }

  // Called from the Course view: load a lesson into accent practice and jump there.
  function startLesson(l) {
    setLesson(l);
    setReferenceText(l.reference_text);
    setMode("accent");
    setReport(null);
    setView("practice");
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">🎙️</span>
          <span>
            <span className="brand-name">
              Talk<span className="accent">Better</span>
            </span>
            <span className="brand-sub">Spoken English coach</span>
          </span>
        </div>
      </header>

      <section className="hero">
        <h1>
          Speak with <span className="accent">confidence.</span>
        </h1>
        <p className="tagline">
          Record yourself, then get instant feedback on filler words, pace,
          grammar, clarity, and your American accent.
        </p>
      </section>

      <ProfilePicker active={profile} onSelect={setProfile} />

      {!profile ? (
        <div className="card empty">
          <span className="empty-emoji">👋</span>
          <p className="muted">Pick or create a profile above to begin.</p>
        </div>
      ) : (
        <>
          <div className="segmented full view-switch">
            <button
              className={view === "practice" ? "active" : ""}
              onClick={() => setView("practice")}
            >
              🎤 Practice
            </button>
            <button
              className={view === "course" ? "active" : ""}
              onClick={() => setView("course")}
            >
              📚 Course
            </button>
            <button
              className={view === "progress" ? "active" : ""}
              onClick={() => setView("progress")}
            >
              📈 Progress
            </button>
          </div>

          {view === "practice" && (
            <>
              <div className="segmented full mode-switch">
                <button
                  className={mode === "free" ? "active" : ""}
                  onClick={() => chooseMode("free")}
                >
                  Grammar & clarity
                </button>
                <button
                  className={mode === "accent" ? "active" : ""}
                  onClick={() => chooseMode("accent")}
                >
                  Accent practice
                </button>
              </div>

              {/* When practicing a course lesson, show which one (with a tip). */}
              {mode === "accent" && lesson && (
                <LessonBanner lesson={lesson} onExit={() => setLesson(null)} />
              )}

              {/* Phase 3: in accent mode, show a sentence to read aloud. */}
              {mode === "accent" && (
                <ReferencePicker value={referenceText} onChange={editReference} />
              )}

              <Recorder onRecorded={handleRecorded} disabled={loading} />

              {loading && (
                <div className="analyzing">
                  <span className="spinner" />
                  Analyzing your speech…
                </div>
              )}
              {error && <p className="error">{error}</p>}
              {report && !loading && <FeedbackReport report={report} />}
            </>
          )}

          {view === "course" && (
            <Course
              profile={profile}
              refreshKey={historyKey}
              onStartLesson={startLesson}
            />
          )}

          {view === "progress" && (
            <Dashboard profile={profile} refreshKey={historyKey} />
          )}
        </>
      )}
    </main>
  );
}

// Shown in accent mode when a course lesson is active: what you're drilling and
// a tip, plus a way to detach and free-form practice instead.
function LessonBanner({ lesson, onExit }) {
  return (
    <div className="lesson-banner">
      <div className="lesson-banner-main">
        <span className="lesson-banner-tag">📚 Course lesson</span>
        <span className="lesson-banner-title">{lesson.title}</span>
        <p className="lesson-banner-tip">{lesson.tip}</p>
      </div>
      <button className="lesson-banner-exit" onClick={onExit} title="Practice freely instead">
        ✕
      </button>
    </div>
  );
}

function ReferencePicker({ value, onChange }) {
  return (
    <div className="reference">
      <label>Read this sentence aloud</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="The quick brown fox jumps over the lazy dog."
      />
    </div>
  );
}
