// Renders the AnalysisResponse. Sections appear as the backend phases come
// online: pace_fillers (Phase 1) always; language (Phase 2) and accent
// (Phase 3) only when present.
export default function FeedbackReport({ report }) {
  const { transcript, pace_fillers, language, accent } = report;

  return (
    <section className="report">
      <div className="report-head">
        <h2>Your feedback</h2>
        <span className="eyebrow">{formatDuration(transcript.duration_sec)}</span>
      </div>

      <div className="card transcript-card">
        <h3>
          <span className="card-icon">📝</span> Transcript
        </h3>
        <p>{transcript.text}</p>
      </div>

      {/* Phase 1 */}
      <div className="card">
        <h3>
          <span className="card-icon">⏱️</span> Pace &amp; filler words
        </h3>
        <div className="metric-row">
          <div className="metric">
            <div className="metric-value">
              {Math.round(pace_fillers.words_per_minute)}
              <span className="unit">wpm</span>
            </div>
            <div className="metric-label">Speaking pace</div>
          </div>
          <div className="metric">
            <div className="metric-value">
              {pace_fillers.filler_total}
              <span className="unit">
                · {pace_fillers.filler_rate_per_min.toFixed(1)}/min
              </span>
            </div>
            <div className="metric-label">Filler words</div>
          </div>
          <div className="metric">
            <div className="metric-value">{pace_fillers.long_pauses}</div>
            <div className="metric-label">Long pauses</div>
          </div>
        </div>
        {pace_fillers.fillers?.length > 0 && (
          <div className="chip-row">
            {pace_fillers.fillers.map((f) => (
              <span className="chip" key={f.word}>
                {f.word} <b>×{f.count}</b>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Phase 2 */}
      {language && (
        <div className="card">
          <h3>
            <span className="card-icon">✨</span> Grammar &amp; clarity
          </h3>
          <div className="score-block">
            <ScoreRing value={language.clarity.score} color="#34d399" />
            <div className="score-text">
              <p>{language.clarity.summary}</p>
            </div>
          </div>

          <div className="corrected">
            <span className="lbl">Corrected</span>
            {language.corrected_text}
          </div>

          {language.grammar_issues?.length > 0 && (
            <ul className="issues">
              {language.grammar_issues.map((g, i) => (
                <li className="issue" key={i}>
                  <div className="issue-line">
                    <span className="issue-old">{g.original}</span>
                    <span className="issue-arrow">→</span>
                    <span className="issue-new">{g.suggestion}</span>
                  </div>
                  <p className="issue-exp">{g.explanation}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Phase 3 */}
      {accent && (
        <div className="card">
          <h3>
            <span className="card-icon">🗣️</span> American accent
          </h3>
          <div className="score-block">
            <ScoreRing value={Math.round(accent.pron_score)} color="#a87bff" />
            <div className="score-text">
              <div className="subscores">
                <SubScore label="Accuracy" value={accent.accuracy_score} />
                <SubScore label="Fluency" value={accent.fluency_score} />
                <SubScore label="Completeness" value={accent.completeness_score} />
              </div>
            </div>
          </div>
          {accent.problem_words?.length > 0 && (
            <div className="chip-row">
              {accent.problem_words.map((w) => (
                <span className="chip" key={w.word}>
                  {w.word}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ScoreRing({ value, color }) {
  return (
    <div
      className="ring"
      style={{ "--val": value, "--ring-color": color }}
      role="img"
      aria-label={`Score ${value} out of 100`}
    >
      <div className="ring-inner">
        <span className="ring-value">{value}</span>
        <span className="ring-max">/ 100</span>
      </div>
    </div>
  );
}

function SubScore({ label, value }) {
  return (
    <div className="subscore">
      <div className="subscore-value">{Math.round(value)}</div>
      <div className="subscore-label">{label}</div>
    </div>
  );
}

function formatDuration(sec) {
  if (sec == null) return "";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
