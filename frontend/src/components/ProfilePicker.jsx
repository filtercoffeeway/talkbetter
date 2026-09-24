import { useEffect, useState } from "react";
import { getProfiles, createProfile } from "../lib/api.js";

// Lets the user pick who's practicing (or create a new profile). No passwords —
// this is a local, trusted, multi-person app. Calls onSelect(profile) when a
// profile is chosen so the parent can scope recordings + history to that person.
export default function ProfilePicker({ active, onSelect }) {
  const [profiles, setProfiles] = useState([]);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setProfiles(await getProfiles());
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      const profile = await createProfile(name);
      setNewName("");
      await refresh();
      onSelect(profile);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="profile-picker">
      <span className="profile-label">Profile</span>
      <div className="profile-list">
        {profiles.map((p) => (
          <button
            key={p.id}
            className={`profile-chip ${active?.id === p.id ? "active" : ""}`}
            onClick={() => onSelect(p)}
          >
            <span className="profile-avatar">{initials(p.name)}</span>
            {p.name}
          </button>
        ))}
        {profiles.length === 0 && (
          <span className="muted">No profiles yet — add one to start.</span>
        )}
      </div>

      <form className="profile-add" onSubmit={handleCreate}>
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New profile…"
          maxLength={40}
        />
        <button type="submit" className="btn-primary" disabled={busy || !newName.trim()}>
          Add
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

// First letters of the name (up to two) for the avatar bubble.
function initials(name) {
  const parts = name.trim().split(/\s+/);
  const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
  return letters.join("") || "?";
}
