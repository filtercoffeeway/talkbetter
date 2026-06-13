import { useEffect, useRef, useState } from "react";
import Chart from "chart.js/auto";
import { getHistory } from "../lib/api.js";

// Progress dashboard for one profile: streak + headline stats + trend charts
// (Chart.js) of the metrics that come online as the backend phases are built.
// `refreshKey` changes whenever a new session is recorded, triggering a reload.
export default function Dashboard({ profile, refreshKey }) {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!profile) return;
    let cancelled = false;
    getHistory(profile.id)
      .then((h) => !cancelled && setHistory(h))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [profile, refreshKey]);

  if (!profile) return null;
  if (error) return <p className="error">{error}</p>;
  if (!history) return <p className="status">Loading progress…</p>;

  const { sessions, current_streak } = history;
  if (sessions.length === 0) {
    return (
      <section className="dashboard">
        <p className="muted">
          No sessions yet for {profile.name}. Record one to start tracking progress.
        </p>
      </section>
    );
  }

  // Oldest -> newest for left-to-right trend lines.
  const ordered = [...sessions].reverse();
  const labels = ordered.map((s) =>
    new Date(s.created_at + "Z").toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    })
  );

  const latest = sessions[0]; // newest first
  const avg = (key) => {
    const vals = sessions.map((s) => s[key]).filter((v) => v != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };

  return (
    <section className="dashboard">
      <div className="stat-grid">
        <Stat label="Streak" value={`${current_streak}🔥`} />
        <Stat label="Sessions" value={sessions.length} />
        <Stat
          label="Latest WPM"
          value={latest.words_per_minute != null ? Math.round(latest.words_per_minute) : "—"}
        />
        <Stat
          label="Avg filler/min"
          value={avg("filler_rate_per_min") != null ? avg("filler_rate_per_min").toFixed(1) : "—"}
        />
      </div>

      <TrendChart
        title="Speaking pace (words/min)"
        labels={labels}
        data={ordered.map((s) => s.words_per_minute)}
        color="#6c8cff"
      />
      <TrendChart
        title="Filler words (per min)"
        labels={labels}
        data={ordered.map((s) => s.filler_rate_per_min)}
        color="#ff9f43"
      />
      {/* Phase 2/3 metrics: only chart them once any session has the data. */}
      {ordered.some((s) => s.clarity_score != null) && (
        <TrendChart
          title="Clarity score"
          labels={labels}
          data={ordered.map((s) => s.clarity_score)}
          color="#26de81"
        />
      )}
      {ordered.some((s) => s.pron_score != null) && (
        <TrendChart
          title="Pronunciation score"
          labels={labels}
          data={ordered.map((s) => s.pron_score)}
          color="#a55eea"
        />
      )}

      <RecentList sessions={sessions.slice(0, 8)} />
    </section>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function TrendChart({ title, labels, data, color }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    const ctx = canvasRef.current.getContext("2d");
    chartRef.current = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: title,
            data,
            borderColor: color,
            backgroundColor: color + "33",
            tension: 0.3,
            fill: true,
            pointRadius: 3,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#9aa0b0" }, grid: { color: "#2a2e3a" } },
          y: { ticks: { color: "#9aa0b0" }, grid: { color: "#2a2e3a" } },
        },
      },
    });
    return () => chartRef.current?.destroy();
  }, [labels, data, color, title]);

  return (
    <div className="card chart-card">
      <h3>{title}</h3>
      <div className="chart-wrap">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}

function RecentList({ sessions }) {
  return (
    <div className="card">
      <h3>Recent sessions</h3>
      <ul className="recent">
        {sessions.map((s) => (
          <li key={s.id}>
            <span className="muted">
              {new Date(s.created_at + "Z").toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
            <span className="recent-tag">{s.mode}</span>
            <span>
              {s.words_per_minute != null ? `${Math.round(s.words_per_minute)} wpm` : ""}
              {s.filler_rate_per_min != null ? ` · ${s.filler_rate_per_min.toFixed(1)} filler/min` : ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
