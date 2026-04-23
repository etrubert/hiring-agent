"""Upload podcast episodes from a JSON file into the Supabase
`podcasts_profiles` table.

Source JSON is a list of episodes as produced by `main.py --json`:
    video_id, url, title, description, channel_title, published_at,
    source_type, guest_name, linkedin, twitter, github, website,
    (optional) is_ai_guest, role_detected, confidence, reasoning

Mapping to the Supabase schema:
  podcast_source      <- channel_title
  episode_title       <- title
  episode_url         <- url
  description_snippet <- description[:300] (newlines replaced by space)
  others (guest_name, role_detected, confidence, is_ai_guest,
          published_at, linkedin, twitter, github, website,
          source_type, reasoning) map 1:1.

Usage:
    python scripts/upload_podcasts_profiles.py data/final/podcasts-1.json
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

TABLE = "podcasts_profiles"


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _text(v: Any) -> Optional[str]:
    if _is_blank(v):
        return None
    return str(v).strip()


def _float(v: Any) -> Optional[float]:
    if _is_blank(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "1", "yes", "oui"}:
            return True
        if s in {"false", "0", "no", "non"}:
            return False
    return None


def _snippet(v: Any, limit: int = 300) -> Optional[str]:
    if _is_blank(v):
        return None
    return str(v)[:limit].replace("\n", " ").strip()


def episode_to_record(ep: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "guest_name": _text(ep.get("guest_name")),
        "role_detected": _text(ep.get("role_detected")),
        "confidence": _float(ep.get("confidence")),
        "is_ai_guest": _bool(ep.get("is_ai_guest")),
        "podcast_source": _text(ep.get("channel_title")),
        "episode_title": _text(ep.get("title")),
        "episode_url": _text(ep.get("url")),
        "published_at": _text(ep.get("published_at")),
        "linkedin": _text(ep.get("linkedin")),
        "twitter": _text(ep.get("twitter")),
        "github": _text(ep.get("github")),
        "website": _text(ep.get("website")),
        "source_type": _text(ep.get("source_type")),
        "description_snippet": _snippet(ep.get("description")),
        "reasoning": _text(ep.get("reasoning")),
    }


def upload(path: Path, dry_run: bool = False) -> None:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"loaded {len(data)} episodes from {path}")

    records: List[Dict[str, Any]] = []
    for ep in data:
        if not ep.get("url"):
            print(f"skip (no url): {ep.get('title')!r}")
            continue
        records.append(episode_to_record(ep))
    print(f"built {len(records)} records; preview of first:")
    for k, v in records[0].items():
        print(f"  {k}: {v!r}")

    if dry_run:
        print("dry-run: no write performed")
        return

    client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    # No unique constraint on episode_url → use plain insert. To avoid
    # creating duplicates when re-running, delete rows whose episode_url
    # is about to be re-inserted first.
    urls = [r["episode_url"] for r in records if r.get("episode_url")]
    if urls:
        client.table(TABLE).delete().in_("episode_url", urls).execute()
    resp = client.table(TABLE).insert(records).execute()
    inserted = len(resp.data) if getattr(resp, "data", None) else len(records)
    print(f"inserted {inserted} rows into {TABLE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    upload(args.json_path, dry_run=args.dry_run)
