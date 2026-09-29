// API client for the TalkBetter backend.
// Dev server proxies /api -> http://127.0.0.1:8000 (see vite.config.js).

async function asJson(res, label) {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${label} failed (${res.status}): ${detail}`);
  }
  return res.json();
}

// `programActivity` = { day, activityId } scores the recording against a 30-day
// program activity (the backend then uses that activity's own sentence/prompt).
export async function analyzeAudio(audioBlob, referenceText, profileId, programActivity) {
  const form = new FormData();
  // Filename extension hints the backend at the container; webm is what
  // MediaRecorder produces by default in Chrome/Edge.
  form.append("audio", audioBlob, "recording.webm");
  if (referenceText) form.append("reference_text", referenceText);
  if (profileId != null) form.append("profile_id", String(profileId));
  if (programActivity) {
    form.append("program_day", String(programActivity.day));
    form.append("activity_id", programActivity.activityId);
  }

  const res = await fetch("/api/analyze", { method: "POST", body: form });
  return asJson(res, "Analyze"); // shape = AnalysisResponse (see backend schemas.py)
}

// ---------- Phase 4: profiles + progress ----------
export async function getProfiles() {
  return asJson(await fetch("/api/profiles"), "Load profiles");
}

export async function createProfile(name) {
  const res = await fetch("/api/profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return asJson(res, "Create profile");
}

export async function getHistory(profileId) {
  const res = await fetch(`/api/history?profile_id=${encodeURIComponent(profileId)}`);
  return asJson(res, "Load history"); // shape = HistoryResponse
}

// ---------- 30-day program ----------
export async function getProgram(profileId) {
  const res = await fetch(`/api/program?profile_id=${encodeURIComponent(profileId)}`);
  return asJson(res, "Load program"); // shape = ProgramResponse
}

export async function getBenchmarks(profileId) {
  const res = await fetch(`/api/program/benchmarks?profile_id=${encodeURIComponent(profileId)}`);
  return asJson(res, "Load benchmarks"); // shape = BenchmarkHistory
}
