// API client for the TalkBetter backend.
// Dev server proxies /api -> http://127.0.0.1:8000 (see vite.config.js).

async function asJson(res, label) {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${label} failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function analyzeAudio(audioBlob, referenceText, profileId) {
  const form = new FormData();
  // Filename extension hints the backend at the container; webm is what
  // MediaRecorder produces by default in Chrome/Edge.
  form.append("audio", audioBlob, "recording.webm");
  if (referenceText) form.append("reference_text", referenceText);
  if (profileId != null) form.append("profile_id", String(profileId));

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
