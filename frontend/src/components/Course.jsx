import { useEffect, useState } from "react";
import { getCourse } from "../lib/api.js";

// American-accent training course for one profile: an ordered set of units, each
// with lessons (a reference sentence + coaching). Shows the profile's progress
// overlaid (status badge + best score) and a course-wide completion bar.
// Clicking "Practice" hands the lesson up to App, which loads it into accent mode.
// `refreshKey` bumps after each analyzed session so progress reloads.
export default function Course({ profile, refreshKey, onStartLesson }) {
  const [course, setCourse] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!profile) return;
    let cancelled = false;
    setError(null);
    getCourse(profile.id)
      .then((c) => !cancelled && setCourse(c))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [profile, refreshKey]);

  if (!profile) return null;
  if (error) return <p className="error">{error}</p>;
  if (!course)
    return (
      <div className="analyzing">
        <span className="spinner" /> Loading course…
      </div>
    );

  const s = course.summary;

  return (
    <section className="course">
      <div className="card course-head">
        <h3>
          <span className="card-icon">📚</span> {course.title}
        </h3>
        <p className="muted">{course.description}</p>
        {s && (
          <>
            <div className="course-progress-row">
              <span className="course-progress-label">
                {s.completed_lessons} of {s.total_lessons} lessons completed
                {s.attempted_lessons > 0 && ` · ${s.attempted_lessons} in progress`}
              </span>
              <span className="course-progress-pct">{Math.round(s.percent_complete)}%</span>
            </div>
            <div className="course-bar">
              <div
                className="course-bar-fill"
                style={{ width: `${s.percent_complete}%` }}
              />
            </div>
            <p className="course-target muted">
              🎯 Reach a pronunciation score of {Math.round(s.target_score)} to clear a lesson.
            </p>
          </>
        )}
      </div>

      {course.units.map((unit, i) => (
        <Unit key={unit.id} unit={unit} index={i + 1} onStartLesson={onStartLesson} />
      ))}
    </section>
  );
}

function Unit({ unit, index, onStartLesson }) {
  const done = unit.lessons.filter((l) => l.progress?.status === "completed").length;
  return (
    <div className="card course-unit">
      <h3>
        <span className="unit-index">{index}</span>
        {unit.title}
        <span className="unit-count">
          {done}/{unit.lessons.length}
        </span>
      </h3>
      <p className="muted unit-desc">{unit.description}</p>
      <ul className="lesson-list">
        {unit.lessons.map((lesson) => (
          <Lesson key={lesson.id} lesson={lesson} onStartLesson={onStartLesson} />
        ))}
      </ul>
    </div>
  );
}

function Lesson({ lesson, onStartLesson }) {
  const status = lesson.progress?.status ?? "not_started";
  const best = lesson.progress?.best_score;
  return (
    <li className={`lesson lesson-${status}`}>
      <span className="lesson-icon">{STATUS_ICON[status]}</span>
      <div className="lesson-body">
        <div className="lesson-title-row">
          <span className="lesson-title">{lesson.title}</span>
          <Badge status={status} best={best} />
        </div>
        <p className="lesson-focus muted">{lesson.focus}</p>
        <p className="lesson-tip">
          <span className="lesson-tip-label">Tip</span> {lesson.tip}
        </p>
        <p className="lesson-sentence">“{lesson.reference_text}”</p>
        {lesson.example_words?.length > 0 && (
          <div className="lesson-words">
            {lesson.example_words.map((w) => (
              <span key={w} className="lesson-word">
                {w}
              </span>
            ))}
          </div>
        )}
      </div>
      <button className="btn-primary lesson-practice" onClick={() => onStartLesson(lesson)}>
        {status === "not_started" ? "Practice" : "Practice again"}
      </button>
    </li>
  );
}

function Badge({ status, best }) {
  if (status === "completed")
    return (
      <span className="lesson-badge done">
        ✓ Completed{best != null ? ` · ${Math.round(best)}` : ""}
      </span>
    );
  if (status === "attempted")
    return (
      <span className="lesson-badge attempted">
        In progress{best != null ? ` · best ${Math.round(best)}` : ""}
      </span>
    );
  return <span className="lesson-badge todo">Not started</span>;
}

const STATUS_ICON = {
  completed: "✅",
  attempted: "🔄",
  not_started: "⚪️",
};
