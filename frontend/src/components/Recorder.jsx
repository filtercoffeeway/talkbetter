import { useEffect, useRef, useState } from "react";

// Records mic audio with the browser MediaRecorder API and hands the
// resulting Blob to onRecorded(blob). No external libraries needed.
// Optional `targetSeconds` shows a "0:42 / 1:30" goal and auto-stops 30 s past it.
export default function Recorder({ onRecorded, disabled, targetSeconds }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  // Tick the elapsed-time counter while recording.
  useEffect(() => {
    if (recording) {
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [recording]);

  useEffect(() => {
    if (recording && targetSeconds && elapsed >= targetSeconds + 30) stop();
  }, [recording, elapsed, targetSeconds]);

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mr = new MediaRecorder(stream);
    chunksRef.current = [];
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    mr.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      stream.getTracks().forEach((t) => t.stop());
      onRecorded(blob);
    };
    mr.start();
    mediaRecorderRef.current = mr;
    setElapsed(0);
    setRecording(true);
  }

  function stop() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  return (
    <div className="recorder">
      <button
        onClick={recording ? stop : start}
        disabled={disabled}
        className={`mic-btn ${recording ? "recording" : ""}`}
        aria-label={recording ? "Stop recording" : "Start recording"}
      >
        {recording ? "■" : "🎙️"}
      </button>

      {recording ? (
        <span className="recorder-timer">
          <span className="rec-dot" />
          {formatTime(elapsed)}
          {targetSeconds ? (
            <span className={elapsed >= targetSeconds ? "recorder-goal met" : "recorder-goal"}>
              / {formatTime(targetSeconds)}
            </span>
          ) : null}
        </span>
      ) : (
        <span className="recorder-label">
          {disabled
            ? "Please wait…"
            : targetSeconds
            ? `Tap to start · aim for ${formatTime(targetSeconds)}`
            : "Tap to start recording"}
        </span>
      )}
    </div>
  );
}

function formatTime(total) {
  const m = String(Math.floor(total / 60)).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return `${m}:${s}`;
}
