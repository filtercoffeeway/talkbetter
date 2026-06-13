// Renders the AnalysisResponse. Sections appear as the backend phases come
// online: pace_fillers (Phase 1) always; language (Phase 2) and accent
// (Phase 3) only when present.
export default function FeedbackReport({ report }) {
  const { transcript, pace_fillers, language, accent } = report;

  return (
    <section className="report">
      <h2>Your feedback</h2>

      <div className="card">
        <h3>Transcript</h3>
        <p>{transcript.text}</p>
      </div>

      {/* Phase 1 */}
      <div className="card">
        <h3>Pace & filler words</h3>
        <ul>
          <li>{Math.round(pace_fillers.words_per_minute)} words/min</li>
          <li>{pace_fillers.filler_total} filler words ({pace_fillers.filler_rate_per_min.toFixed(1)}/min)</li>
          <li>{pace_fillers.long_pauses} long pauses</li>
        </ul>
        {pace_fillers.fillers?.length > 0 && (
          <p className="muted">
            {pace_fillers.fillers.map((f) => `${f.word} ×${f.count}`).join(", ")}
          </p>
        )}
      </div>

      {/* Phase 2 */}
      {language && (
        <div className="card">
          <h3>Grammar & clarity</h3>
          <p><strong>Clarity:</strong> {language.clarity.score}/100 — {language.clarity.summary}</p>
          <p><strong>Corrected:</strong> {language.corrected_text}</p>
          {language.grammar_issues?.length > 0 && (
            <ul>
              {language.grammar_issues.map((g, i) => (
                <li key={i}>
                  <s>{g.original}</s> → <strong>{g.suggestion}</strong> — {g.explanation}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Phase 3 */}
      {accent && (
        <div className="card">
          <h3>Accent</h3>
          <ul>
            <li>Overall pronunciation: {accent.pron_score}/100</li>
            <li>Accuracy: {accent.accuracy_score} · Fluency: {accent.fluency_score} · Completeness: {accent.completeness_score}</li>
          </ul>
          {accent.problem_words?.length > 0 && (
            <p className="muted">
              Work on: {accent.problem_words.map((w) => w.word).join(", ")}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
