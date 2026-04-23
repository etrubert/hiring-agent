"""Rebuild the France report as a structured JSON file.

Reads:
  data/filtered/hackathons_scored.json
  data/filtered/projects_raw.json

Applies the same filter as `main.py --france-only` (city_fr present, keep=True,
relevance_score >= MIN_RELEVANCE_SCORE), groups projects under each hackathon,
and writes a clean JSON to data/final/report_{stem}_france.json.

Usage:
    python scripts/build_france_json.py --stem 20260422
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

MIN_SCORE = config.MIN_RELEVANCE_SCORE


def _clean_prize(raw: str) -> str:
    """Strip HTML tags from the prize pool field (Devpost leaves <span> in)."""
    if not raw:
        return ""
    import re
    return re.sub(r"<[^>]+>", "", raw).strip()


def _participant(p: Dict) -> Dict:
    return {
        "name": p.get("name") or "",
        "github": p.get("github") or "",
        "linkedin": p.get("linkedin") or "",
        "twitter": p.get("twitter") or "",
        "website": p.get("website") or "",
        "devpost_profile": p.get("profile_url") or "",
    }


def _project(p: Dict) -> Dict:
    return {
        "title": p.get("project_title") or "",
        "tagline": p.get("tagline") or "",
        "url": p.get("project_url") or "",
        "github": p.get("github_url") or "",
        "external_links": p.get("external_links") or [],
        "built_with": p.get("built_with") or [],
        "is_winner": bool(p.get("is_winner")),
        "winner_labels": p.get("winner_labels") or [],
        "participants": [_participant(x) for x in p.get("participants") or []],
    }


def _hackathon(h: Dict, projects: List[Dict]) -> Dict:
    winners = [p for p in projects if p.get("is_winner")]
    ordered = winners + [p for p in projects if not p.get("is_winner")]
    return {
        "id": h.get("id"),
        "title": h.get("title") or "",
        "url": h.get("url") or "",
        "platform": h.get("source_platform") or "",
        "city_fr": h.get("city_fr") or "",
        "location": h.get("location") or "",
        "is_online": bool(h.get("is_online")),
        "start_date": h.get("start_date") or "",
        "end_date": h.get("end_date") or "",
        "prize_pool": _clean_prize(h.get("prize_pool") or ""),
        "relevance_score": h.get("relevance_score"),
        "ai_keywords_found": h.get("ai_keywords_found") or [],
        "tools_found": h.get("tools_found") or [],
        "target_roles_found": h.get("target_roles_found") or [],
        "projects_count": len(projects),
        "winners_count": len(winners),
        "projects": [_project(p) for p in ordered],
    }


def build(stem: str, min_score: int, require_keep: bool, suffix: str) -> Path:
    scored = json.loads((config.DATA_FILTERED / "hackathons_scored.json").read_text(encoding="utf-8"))
    projects = json.loads((config.DATA_FILTERED / "projects_raw.json").read_text(encoding="utf-8"))

    kept = [
        h for h in scored
        if h.get("city_fr")
        and (h.get("relevance_score") or 0) >= min_score
        and (h.get("keep") if require_keep else True)
    ]
    kept.sort(key=lambda h: h.get("relevance_score") or 0, reverse=True)

    by_hack: Dict[str, List[Dict]] = defaultdict(list)
    for p in projects:
        by_hack[p.get("hackathon_id") or ""].append(p)

    out = {
        "generated_from": "hackathons_scored.json + projects_raw.json",
        "filter": {"france_only": True, "min_score": min_score, "keep_only": require_keep},
        "total_hackathons": len(kept),
        "hackathons": [_hackathon(h, by_hack.get(h.get("id") or "", [])) for h in kept],
    }

    out_path = config.DATA_FINAL / f"report_{stem}_france{suffix}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", default="20260422")
    ap.add_argument("--min-score", type=int, default=MIN_SCORE)
    ap.add_argument("--no-keep-filter", action="store_true",
                    help="Include hackathons where keep=False (relaxed filter)")
    ap.add_argument("--suffix", default="",
                    help="Extra suffix before .json (e.g. '_all')")
    args = ap.parse_args()
    path = build(args.stem, args.min_score, not args.no_keep_filter, args.suffix)
    print(f"wrote {path}")
