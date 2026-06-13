import { useRef, useState } from "react";

// Records mic audio with the browser MediaRecorder API and hands the
// resulting Blob to onRecorded(blob). No external libraries needed.
export default function Recorder({ onRecorded, disabled }) {
  const [recording, setRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

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
    setRecording(true);
  }

  function stop() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  }

  return (
    <div className="recorder">
      {!recording ? (
        <button onClick={start} disabled={disabled}>● Record</button>
      ) : (
        <button onClick={stop} className="stop">■ Stop</button>
      )}
    </div>
  );
}
