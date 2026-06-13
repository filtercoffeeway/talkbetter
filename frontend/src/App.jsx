import { useState } from "react";
import Recorder from "./components/Recorder.jsx";
import FeedbackReport from "./components/FeedbackReport.jsx";
import ProfilePicker from "./components/ProfilePicker.jsx";
import Dashboard from "./components/Dashboard.jsx";
import { analyzeAudio } from "./lib/api.js";

// Top-level views:
//   "practice" -> record + get feedback (Phases 1-3), scoped to a profile
//   "progress" -> Dashboard of that profile's history over time (Phase 4)
// Within practice, two modes:
//   "free"   -> filler/pace + grammar/clarity on free speech
//   "accent" -> user reads REFERENCE_SENTENCE for pronunciation scoring
export default function App() {
  const [view, setView] = useState("practice");
  const [profile, setProfile] = useState(null);
  const [mode, setMode] = useState("free");
  const [referenceText, setReferenceText] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Bumped after each saved session so the Dashboard reloads its history.
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
      <header>
        <h1>TalkBetter</h1>
        <p className="tagline">Practice speaking. Get feedback on fillers, grammar, clarity, and accent.</p>
      </header>

      <ProfilePicker active={profile} onSelect={setProfile} />

      {!profile ? (
        <p className="status">Pick or create a profile above to begin.</p>
      ) : (
        <>
          <div className="view-switch">
            <button className={view === "practice" ? "active" : ""} onClick={() => setView("practice")}>
              Practice
            </button>
            <button className={view === "progress" ? "active" : ""} onClick={() => setView("progress")}>
              Progress
            </button>
          </div>

          {view === "practice" ? (
            <>
              <div className="mode-switch">
                <button className={mode === "free" ? "active" : ""} onClick={() => setMode("free")}>
                  Free speaking
                </button>
                <button className={mode === "accent" ? "active" : ""} onClick={() => setMode("accent")}>
                  Accent practice
                </button>
              </div>

              {/* Phase 3: in accent mode, show a sentence to read aloud. */}
              {mode === "accent" && (
                <ReferencePicker value={referenceText} onChange={setReferenceText} />
              )}

              <Recorder onRecorded={handleRecorded} disabled={loading} />

              {loading && <p className="status">Analyzing…</p>}
              {error && <p className="error">{error}</p>}
              {report && <FeedbackReport report={report} />}
            </>
          ) : (
            <Dashboard profile={profile} refreshKey={historyKey} />
          )}
        </>
      )}
    </main>
  );
}

// TODO(Phase 3): replace with a real set of practice sentences / categories.
function ReferencePicker({ value, onChange }) {
  return (
    <div className="reference">
      <label>Read this sentence aloud:</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="The quick brown fox jumps over the lazy dog."
      />
    </div>
  );
}
