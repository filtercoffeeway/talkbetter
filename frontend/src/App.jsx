import { useState } from "react";
import Recorder from "./components/Recorder.jsx";
import FeedbackReport from "./components/FeedbackReport.jsx";
import ProfilePicker from "./components/ProfilePicker.jsx";
import Dashboard from "./components/Dashboard.jsx";
import Program from "./components/Program.jsx";
import { analyzeAudio } from "./lib/api.js";

// Top-level views:
//   "program"  -> the 30-day, 30-minute program with its daily benchmark (default)
//   "practice" -> record + get feedback (Phases 1-3), scoped to a profile
//   "progress" -> Dashboard of that profile's history over time (Phase 4)
// Within practice, two modes:
//   "free"   -> filler/pace + grammar/clarity on free speech
//   "accent" -> user reads a reference sentence for pronunciation scoring.
export default function App() {
  const [view, setView] = useState("program");
  const [profile, setProfile] = useState(null);
  const [mode, setMode] = useState("free");
  const [referenceText, setReferenceText] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Bumped after each saved session so the Dashboard reloads progress.
  const [historyKey, setHistoryKey] = useState(0);

  async function handleRecorded(audioBlob) {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeAudio(
        audioBlob,
        mode === "accent" ? referenceText : null,
        profile?.id
      );
      setReport(result);
      setHistoryKey((k) => k + 1); // new session persisted -> refresh dashboard
    } catch (e) {
      setError(e.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
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
              className={view === "program" ? "active" : ""}
              onClick={() => setView("program")}
            >
              📅 30 Days
            </button>
            <button
              className={view === "practice" ? "active" : ""}
              onClick={() => setView("practice")}
            >
              🎤 Practice
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
                  onClick={() => setMode("free")}
                >
                  Grammar & clarity
                </button>
                <button
                  className={mode === "accent" ? "active" : ""}
                  onClick={() => setMode("accent")}
                >
                  Accent practice
                </button>
              </div>

              {/* Phase 3: in accent mode, show a sentence to read aloud. */}
              {mode === "accent" && (
                <ReferencePicker value={referenceText} onChange={setReferenceText} />
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

          {view === "program" && (
            <Program profile={profile} onSaved={() => setHistoryKey((k) => k + 1)} />
          )}

          {view === "progress" && (
            <Dashboard profile={profile} refreshKey={historyKey} />
          )}
        </>
      )}
    </main>
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
