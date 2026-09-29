"""Erase a profile's results so you can start over (the profile name is kept).

From backend/:

    .venv/bin/python -m scripts.reset_profile Mahesh                 # everything: sessions + 30-day program
    .venv/bin/python -m scripts.reset_profile Mahesh --program-only  # just the 30-day program (back to Day 1)
    .venv/bin/python -m scripts.reset_profile Mahesh -y              # skip the confirmation

Saved audio in data/recordings/ is left alone.
"""
from __future__ import annotations

import argparse

from app import db

PROGRAM_TABLES = ("program_activity_results", "benchmark_results")
ALL_TABLES = ("sessions", *PROGRAM_TABLES)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="profile name (case-insensitive)")
    ap.add_argument("--program-only", action="store_true", help="only reset the 30-day program")
    ap.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    args = ap.parse_args()

    db.init_db()
    tables = PROGRAM_TABLES if args.program_only else ALL_TABLES
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT id, name FROM profiles WHERE name = ? COLLATE NOCASE", (args.name,)
        ).fetchone()
        if row is None:
            raise SystemExit(f"No profile named {args.name!r}.")
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t} WHERE profile_id = ?", (row["id"],)).fetchone()[0]
            for t in tables
        }
        print(f"Profile {row['name']} (id {row['id']}): " + ", ".join(f"{t} {n}" for t, n in counts.items()))
        if not any(counts.values()):
            print("Nothing to erase.")
            return
        if not args.yes and input("Erase these rows? [y/N] ").strip().lower() != "y":
            print("Cancelled.")
            return
        for t in tables:
            conn.execute(f"DELETE FROM {t} WHERE profile_id = ?", (row["id"],))
    print("Done — reload the app and you're back on Day 1.")


if __name__ == "__main__":
    main()
