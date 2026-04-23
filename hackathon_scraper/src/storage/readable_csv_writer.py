"""CSV equivalent of the readable report: one row per project, with all
hackathon + project + participant-social fields inlined.

Rows for hackathons with zero scraped projects are still emitted (single row
with empty project columns) so the CSV mirrors the report's coverage.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

logger = logging.getLogger(__name__)

COLUMNS = [
    "city_fr",
    "hackathon_title",
    "hackathon_url",
    "hackathon_platform",
    "hackathon_location",
    "hackathon_start_date",
    "hackathon_end_date",
    "hackathon_prize_pool",
    "hackathon_score",
    "hackathon_ai_keywords",
    "hackathon_tools",
    "is_winner",
    "winner_labels",
    "project_title",
    "project_url",
    "tagline",
    "project_github",
    "built_with",
    "external_links",
    "participants",
    "participant_githubs",
    "participant_linkedins",
    "participant_twitters",
    "participant_websites",
    "participant_devpost_profiles",
]


def _join(values: Iterable[str], sep: str = ", ") -> str:
    return sep.join(v for v in values if v)


def _row_from_project(h: Dict, p: Dict) -> Dict:
    parts = p.get("participants") or []
    return {
        "city_fr": h.get("city_fr") or "",
        "hackathon_title": h.get("title") or "",
        "hackathon_url": h.get("url") or "",
        "hackathon_platform": h.get("source_platform") or "",
        "hackathon_location": h.get("location") or "",
        "hackathon_start_date": h.get("start_date") or "",
        "hackathon_end_date": h.get("end_date") or "",
        "hackathon_prize_pool": h.get("prize_pool") or "",
        "hackathon_score": h.get("relevance_score"),
        "hackathon_ai_keywords": _join(h.get("ai_keywords_found") or []),
        "hackathon_tools": _join(h.get("tools_found") or []),
        "is_winner": bool(p.get("is_winner")),
        "winner_labels": _join(p.get("winner_labels") or []),
        "project_title": p.get("project_title") or "",
        "project_url": p.get("project_url") or "",
        "tagline": p.get("tagline") or "",
        "project_github": p.get("github_url") or "",
        "built_with": _join(p.get("built_with") or []),
        "external_links": _join(p.get("external_links") or []),
        "participants": _join(x.get("name", "") for x in parts),
        "participant_githubs": _join(x.get("github", "") for x in parts),
        "participant_linkedins": _join(x.get("linkedin", "") for x in parts),
        "participant_twitters": _join(x.get("twitter", "") for x in parts),
        "participant_websites": _join(x.get("website", "") for x in parts),
        "participant_devpost_profiles": _join(x.get("profile_url", "") for x in parts),
    }


def _empty_row(h: Dict) -> Dict:
    return {
        "city_fr": h.get("city_fr") or "",
        "hackathon_title": h.get("title") or "",
        "hackathon_url": h.get("url") or "",
        "hackathon_platform": h.get("source_platform") or "",
        "hackathon_location": h.get("location") or "",
        "hackathon_start_date": h.get("start_date") or "",
        "hackathon_end_date": h.get("end_date") or "",
        "hackathon_prize_pool": h.get("prize_pool") or "",
        "hackathon_score": h.get("relevance_score"),
        "hackathon_ai_keywords": _join(h.get("ai_keywords_found") or []),
        "hackathon_tools": _join(h.get("tools_found") or []),
        "is_winner": "",
        "winner_labels": "",
        "project_title": "",
        "project_url": "",
        "tagline": "",
        "project_github": "",
        "built_with": "",
        "external_links": "",
        "participants": "",
        "participant_githubs": "",
        "participant_linkedins": "",
        "participant_twitters": "",
        "participant_websites": "",
        "participant_devpost_profiles": "",
    }


def write_readable_csv(
    hackathons: List[Dict],
    projects: Iterable[Dict],
    out_path: Path,
    winners_only: bool = False,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    by_hackathon: Dict[str, List[Dict]] = defaultdict(list)
    for p in projects:
        by_hackathon[p.get("hackathon_id") or ""].append(p)

    hackathons_sorted = sorted(
        hackathons,
        key=lambda h: (h.get("relevance_score") or 0, len(by_hackathon.get(h.get("id") or "", []))),
        reverse=True,
    )

    rows: List[Dict] = []
    for h in hackathons_sorted:
        ps = by_hackathon.get(h.get("id") or "", [])
        if winners_only:
            ps = [p for p in ps if p.get("is_winner")]
        else:
            winners = [p for p in ps if p.get("is_winner")]
            if winners:
                ps = winners + [p for p in ps if not p.get("is_winner")]
        if not ps:
            rows.append(_empty_row(h))
            continue
        for p in ps:
            rows.append(_row_from_project(h, p))

    pd.DataFrame(rows, columns=COLUMNS).to_csv(out_path, index=False, encoding="utf-8")
    logger.info("wrote readable CSV (%d rows) to %s", len(rows), out_path)
    return out_path
