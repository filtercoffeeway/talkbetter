import { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";
import Recorder from "./Recorder.jsx";
import FeedbackReport from "./FeedbackReport.jsx";
import { analyzeAudio, getBenchmarks, getProgram } from "../lib/api.js";

// The 30-day, 30-minute program for one profile:
//   - benchmark trend (the fixed daily exercise — the ground truth for progress)
//   - a 30-day map (completed / today / locked)
//   - the selected day: benchmark first, then practice, each recordable inline.
// `onSaved` is called after every analyzed recording so other views refresh.
export default function Program({ profile, onSaved }) {
  const [program, setProgram] = useState(null);
  const [bench, setBench] = useState(null);
  const [day, setDay] = useState(null);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([getProgram(profile.id), getBenchmarks(profile.id)])
      .then(([p, b]) => {
        if (cancelled) return;
        setProgram(p);
        setBench(b);
        setDay((d) => d ?? p.summary.current_day);
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [profile, reloadKey]);

  if (error) return <p className="error">{error}</p>;
  if (!program || day == null)
    return (
      <div className="analyzing">
        <span className="spinner" /> Loading your program…
      </div>
    );

  const s = program.summary;
  const selected = program.days[day - 1];
  const week = program.weeks[selected.week - 1];

  function recorded() {
    setReloadKey((k) => k + 1);
    onSaved?.();
  }

  return (
    <section className="program">
      <div className="card program-head">
        <h3>
          <span className="card-icon">📅</span> {program.title}
        </h3>
        <p className="muted">{program.description}</p>
        <div className="program-progress-row">
          <span className="program-progress-label">
            Day {s.current_day} of {s.total_days} · {s.completed_days} completed
          </span>
          <span className="program-progress-pct">
            {Math.round((s.completed_days / s.total_days) * 100)}%
          </span>
        </div>
        <div className="program-bar">
          <div
            className="program-bar-fill"
            style={{ width: `${(s.completed_days / s.total_days) * 100}%` }}
          />
        </div>
      </div>

      <BenchmarkTrend bench={bench} description={program.benchmark_description} />

      <DayMap
        days={program.days}
        weeks={program.weeks}
        selected={day}
        current={s.current_day}
        onSelect={setDay}
      />

      <div className="card day-card">
        <div className="day-head">
          <span className="day-num">Day {selected.day}</span>
          <span className="day-week">
            Week {week.week} · {week.title}
          </span>
        </div>
        <h3 className="day-title">{selected.title}</h3>
        <p className="muted">{selected.goal}</p>
        {selected.status === "locked" && (
          <p className="day-note">🔒 Finish Day {s.current_day} first — you can preview this day.</p>
        )}
        {selected.status === "available" && s.finished_a_day_today && (
          <p className="day-note">
            ✅ You already finished a day today. Progress sticks best one day at a time — this one
            is ideal for tomorrow.
          </p>
        )}
        {selected.status === "completed" && (
          <p className="day-note done">✓ Completed. Replays count as practice; the benchmark keeps your first take.</p>
        )}
      </div>

      <Section
        title="Daily benchmark"
        subtitle="Same difficulty every day — your ground truth"
        activities={selected.activities.filter((a) => a.section === "benchmark")}
        day={selected}
        profile={profile}
        onRecorded={recorded}
      />
      <Section
        title="Practice"
        subtitle="Today's lesson"
        activities={selected.activities.filter((a) => a.section === "practice")}
        day={selected}
        profile={profile}
        onRecorded={recorded}
      />
    </section>
  );
}

// ---------- benchmark trend ----------
function BenchmarkTrend({ bench, description }) {
  const entries = bench?.entries ?? [];
  if (entries.length === 0)
    return (
      <div className="card">
        <h3>
          <span className="card-icon">🎯</span> Benchmark trend
        </h3>
        <p className="muted">
          {description} Your first benchmark becomes the baseline everything is compared to.
        </p>
      </div>
    );

  const change =
    bench.baseline != null && bench.latest != null ? bench.latest - bench.baseline : null;
  const w1 = bench.weeks[0];

  return (
    <div className="card">
      <h3>
        <span className="card-icon">🎯</span> Benchmark trend
      </h3>
      <div className="stat-grid bench-stats">
        <Stat label="Baseline" value={fmt(bench.baseline)} />
        <Stat label="Latest" value={fmt(bench.latest)} />
        <Stat
          label="Change"
          value={change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(1)}`}
          tone={change == null ? "" : change >= 0 ? "up" : "down"}
        />
        <Stat label="Days measured" value={entries.length} />
      </div>
      <BenchmarkChart entries={entries} />
      <div className="table-wrap">
        <table className="bench-table">
          <thead>
            <tr>
              <th>Week</th>
              <th>Score</th>
              <th>Pronunciation</th>
              <th>Speaking</th>
              <th>Fillers/min</th>
              <th>Confidence</th>
              <th>Structure</th>
            </tr>
          </thead>
          <tbody>
            {bench.weeks.map((w) => (
              <tr key={w.week}>
                <td>
                  Week {w.week} <span className="muted">({w.days}d)</span>
                </td>
                <td>
                  <b>{fmt(w.avg_score)}</b>
                  {w.week > 1 && <Delta now={w.avg_score} then={w1.avg_score} />}
                </td>
                <td>{fmt(w.avg_read_score)}</td>
                <td>{fmt(w.avg_speak_score)}</td>
                <td>
                  {fmt(w.avg_filler_rate_per_min)}
                  {w.week > 1 && (
                    <Delta now={w.avg_filler_rate_per_min} then={w1.avg_filler_rate_per_min} lowerIsBetter />
                  )}
                </td>
                <td>{fmt(w.avg_confidence)}</td>
                <td>{fmt(w.avg_structure)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BenchmarkChart({ entries }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const series = (key, label, color, width = 2, dash = []) => ({
      label,
      data: entries.map((e) => e[key]),
      borderColor: color,
      backgroundColor: color,
      borderWidth: width,
      borderDash: dash,
      tension: 0.3,
      pointRadius: 3,
      spanGaps: true,
    });
    const axis = {
      ticks: { color: "#6b7488" },
      grid: { color: "rgba(255,255,255,0.05)" },
      border: { display: false },
    };
    const chart = new Chart(canvasRef.current.getContext("2d"), {
      type: "line",
      data: {
        labels: entries.map((e) => `Day ${e.day}`),
        datasets: [
          series("score", "Benchmark score", "#7c8cff", 3),
          series("read_score", "Pronunciation", "#a87bff", 1.5, [4, 4]),
          series("speak_score", "Speaking", "#34d399", 1.5, [4, 4]),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#97a0b5", boxWidth: 12 } },
          tooltip: { backgroundColor: "#141826", titleColor: "#eef1f9", bodyColor: "#97a0b5" },
        },
        scales: { x: axis, y: { ...axis, suggestedMin: 0, suggestedMax: 100 } },
      },
    });
    return () => chart.destroy();
  }, [entries]);

  return (
    <div className="chart-wrap">
      <canvas ref={canvasRef} />
    </div>
  );
}

// ---------- 30-day map ----------
function DayMap({ days, weeks, selected, current, onSelect }) {
  return (
    <div className="card day-map">
      {weeks.map((w) => (
        <div className="day-map-week" key={w.week}>
          <span className="day-map-label">W{w.week}</span>
          <div className="day-map-row">
            {days
              .filter((d) => d.week === w.week)
              .map((d) => (
                <button
                  key={d.day}
                  className={[
                    "day-dot",
                    d.status,
                    d.day === current ? "current" : "",
                    d.day === selected ? "selected" : "",
                  ].join(" ")}
                  onClick={() => onSelect(d.day)}
                  title={`Day ${d.day}: ${d.title}`}
                >
                  {d.status === "completed" ? "✓" : d.day}
                </button>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------- activities ----------
function Section({ title, subtitle, activities, day, profile, onRecorded }) {
  const minutes = activities.reduce((n, a) => n + a.minutes, 0);
  return (
    <div className="program-section">
      <div className="program-section-head">
        <h3>{title}</h3>
        <span className="muted">
          {subtitle} · {minutes} min
        </span>
      </div>
      {activities.map((a) => (
        <Activity
          key={`${day.day}-${a.id}`}
          activity={a}
          day={day}
          profile={profile}
          onRecorded={onRecorded}
        />
      ))}
    </div>
  );
}

function Activity({ activity: a, day, profile, onRecorded }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const locked = day.status === "locked";
  const done = a.result != null;

  async function handleRecorded(blob) {
    setLoading(true);
    setError(null);
    try {
      const r = await analyzeAudio(blob, a.reference_text, profile.id, {
        day: day.day,
        activityId: a.id,
      });
      setReport(r);
      onRecorded();
    } catch (e) {
      setError(e.message ?? "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`card activity ${done ? "done" : ""}`}>
      <button className="activity-row" onClick={() => setOpen((o) => !o)}>
        <span className="activity-icon">{done ? "✅" : a.kind === "read" ? "🗣️" : "💬"}</span>
        <span className="activity-main">
          <span className="activity-title">{a.title}</span>
          <span className="activity-meta">
            <span className={`skill-tag ${a.skill}`}>{SKILL_LABEL[a.skill]}</span>
            {a.minutes} min
            {done && a.result.best_score != null && ` · best ${Math.round(a.result.best_score)}`}
            {done && ` · ${a.result.attempts} ${a.result.attempts === 1 ? "take" : "takes"}`}
          </span>
        </span>
        <span className="activity-chevron">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div className="activity-body">
          <p className="activity-tip">
            <span className="activity-tip-label">{a.kind === "read" ? "Tip" : "Technique"}</span>{" "}
            {a.instructions}
          </p>
          {a.kind === "read" ? (
            <div className="activity-text">
              <p className="activity-sentence">“{a.reference_text}”</p>
              <ListenButton text={a.reference_text} />
            </div>
          ) : (
            <p className="activity-prompt">{a.prompt}</p>
          )}

          {locked ? (
            <p className="day-note">🔒 This day unlocks after the one before it.</p>
          ) : (
            <Recorder
              onRecorded={handleRecorded}
              disabled={loading}
              targetSeconds={a.target_seconds}
            />
          )}

          {loading && (
            <div className="analyzing">
              <span className="spinner" /> Analyzing your speech…
            </div>
          )}
          {error && <p className="error">{error}</p>}
          {report && !loading && (
            <>
              <AttemptBanner attempt={report.program} />
              <FeedbackReport report={report} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function AttemptBanner({ attempt }) {
  if (!attempt) return null;
  return (
    <div className={`attempt-banner ${attempt.counted ? "" : "warn"}`}>
      {attempt.score != null && (
        <span className="attempt-score">{Math.round(attempt.score)}</span>
      )}
      <span>
        {attempt.counted ? "Activity score" : ""}
        {attempt.message && <span className="muted"> {attempt.message}</span>}
      </span>
    </div>
  );
}

// Plays the sentence with the browser's American English voice — listen, then repeat.
function ListenButton({ text }) {
  if (!("speechSynthesis" in window)) return null;
  function play() {
    const u = new SpeechSynthesisUtterance(text);
    const voice = speechSynthesis.getVoices().find((v) => v.lang === "en-US");
    if (voice) u.voice = voice;
    u.lang = "en-US";
    u.rate = 0.9;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }
  return (
    <button className="listen-btn" onClick={play} title="Hear it in American English">
      🔊 Listen
    </button>
  );
}

function Stat({ label, value, tone = "" }) {
  return (
    <div className="stat">
      <div className={`stat-value ${tone}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function Delta({ now, then, lowerIsBetter = false }) {
  if (now == null || then == null) return null;
  const d = now - then;
  const good = lowerIsBetter ? d <= 0 : d >= 0;
  return (
    <span className={`delta ${good ? "up" : "down"}`}>
      {d >= 0 ? "+" : ""}
      {d.toFixed(1)}
    </span>
  );
}

const fmt = (v) => (v == null ? "—" : Number(v).toFixed(v >= 10 ? 0 : 1));

const SKILL_LABEL = {
  pronunciation: "Pronunciation",
  fillers: "Fillers",
  structure: "Thinking",
  conversation: "Conversation",
  confidence: "Confidence",
};
