"""Upload a France hackathons JSON (produced by build_france_json.py) into the
Supabase `hackathon_profiles` table.

Source JSON structure:
    {
      "total_hackathons": N,
      "hackathons": [
        {id, title, url, platform, city_fr, location, is_online,
         start_date, end_date, prize_pool, relevance_score,
         ai_keywords_found[], tools_found[], target_roles_found[],
         projects_count, winners_count,
         projects: [...]}
      ]
    }

Usage:
    python scripts/upload_hackathon_profiles.py data/final/report_20260422_france_all.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

TABLE = "hackathon_profiles"


def _row(h: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hackathon_id": h.get("id") or "",
        "title": h.get("title") or "",
        "url": h.get("url") or None,
        "platform": h.get("platform") or None,
        "city_fr": h.get("city_fr") or None,
        "location": h.get("location") or None,
        "is_online": bool(h.get("is_online")),
        "start_date": h.get("start_date") or None,
        "end_date": h.get("end_date") or None,
        "prize_pool": h.get("prize_pool") or None,
        "relevance_score": h.get("relevance_score"),
        "ai_keywords_found": h.get("ai_keywords_found") or [],
        "tools_found": h.get("tools_found") or [],
        "target_roles_found": h.get("target_roles_found") or [],
        "projects_count": h.get("projects_count") or 0,
        "winners_count": h.get("winners_count") or 0,
        "projects": h.get("projects") or [],
    }


def upload(path: Path, dry_run: bool = False) -> None:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    data = json.loads(path.read_text(encoding="utf-8"))
    hackathons = data.get("hackathons") or []
    print(f"loaded {len(hackathons)} hackathons from {path}")

    rows: List[Dict[str, Any]] = [_row(h) for h in hackathons if h.get("id")]
    print(f"built {len(rows)} rows; preview of first row keys:")
    print(f"  {list(rows[0].keys())}")
    print(f"  title: {rows[0]['title']}")
    print(f"  city_fr: {rows[0]['city_fr']}")
    print(f"  projects (len): {len(rows[0]['projects'])}")

    if dry_run:
        print("dry-run: no write performed")
        return

    client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    resp = client.table(TABLE).upsert(rows, on_conflict="hackathon_id").execute()
    inserted = len(resp.data) if getattr(resp, "data", None) else len(rows)
    print(f"upserted {inserted} rows into {TABLE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    upload(args.json_path, dry_run=args.dry_run)
