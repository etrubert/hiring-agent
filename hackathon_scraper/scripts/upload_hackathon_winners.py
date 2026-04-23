"""Flatten winning projects from the France hackathons JSON into the
Supabase `hackathon_winners` table (one row per winning participant).

Reads a JSON produced by `build_france_json.py`, keeps only projects with
is_winner=True, then emits one record per participant so each winner is
directly visible (and filterable) in the Supabase dashboard.

Usage:
    python scripts/upload_hackathon_winners.py data/final/report_20260422_france_all.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

TABLE = "hackathon_winners"


def _row(hack: Dict[str, Any], project: Dict[str, Any], participant: Dict[str, Any]) -> Dict[str, Any]:
    labels = project.get("winner_labels") or []
    return {
        "hackathon_title": hack.get("title") or "",
        "city_fr": hack.get("city_fr") or None,
        "project_title": project.get("title") or "",
        "project_url": project.get("url") or None,
        "project_github": project.get("github") or None,
        "winner_label": ", ".join(labels) if labels else None,
        "participant_name": participant.get("name") or "",
        "participant_github": participant.get("github") or None,
        "participant_linkedin": participant.get("linkedin") or None,
        "participant_twitter": participant.get("twitter") or None,
        "participant_website": participant.get("website") or None,
        "participant_devpost": participant.get("devpost_profile") or None,
    }


def build_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for hack in data.get("hackathons") or []:
        for project in hack.get("projects") or []:
            if not project.get("is_winner"):
                continue
            for participant in project.get("participants") or []:
                if not participant.get("name"):
                    continue
                rows.append(_row(hack, project, participant))
    return rows


def upload(path: Path, dry_run: bool = False) -> None:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    data = json.loads(path.read_text(encoding="utf-8"))
    rows = build_rows(data)
    print(f"built {len(rows)} winner rows from {path}")
    if rows:
        print(f"preview first row: {rows[0]}")

    if dry_run:
        print("dry-run: no write performed")
        return

    client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    titles = list({r["hackathon_title"] for r in rows if r.get("hackathon_title")})
    if titles:
        client.table(TABLE).delete().in_("hackathon_title", titles).execute()
    resp = client.table(TABLE).insert(rows).execute()
    inserted = len(resp.data) if getattr(resp, "data", None) else len(rows)
    print(f"inserted {inserted} rows into {TABLE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    upload(args.json_path, dry_run=args.dry_run)
