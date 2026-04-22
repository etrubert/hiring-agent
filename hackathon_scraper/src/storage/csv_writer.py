"""Write the three CSVs: hackathons, people, companies."""

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.extractors.role_matcher import match_role

logger = logging.getLogger(__name__)

HACKATHON_COLUMNS = [
    "id",
    "title",
    "url",
    "source_platform",
    "sources",
    "location",
    "is_online",
    "start_date",
    "end_date",
    "prize_pool",
    "relevance_score",
    "theme_is_ai",
    "has_target_role",
    "has_specific_tool",
    "target_roles_found",
    "tools_found",
    "ai_keywords_found",
    "match_reasons",
    "description_snippet",
]

PEOPLE_COLUMNS = [
    "hackathon_id",
    "hackathon_title",
    "name",
    "title",
    "target_role",
    "context_role",
    "company",
    "linkedin",
    "twitter",
]

COMPANY_COLUMNS = [
    "hackathon_id",
    "hackathon_title",
    "name",
    "role",
    "website",
]

PROJECT_COLUMNS = [
    "hackathon_id",
    "hackathon_title",
    "hackathon_url",
    "is_winner",
    "winner_labels",
    "project_title",
    "project_url",
    "tagline",
    "github_url",
    "participants",
    "participant_profiles",
    "participant_githubs",
    "participant_linkedins",
    "participant_twitters",
    "participant_websites",
    "built_with",
    "external_links",
]


def _project_row(p: Dict) -> Dict:
    participants = p.get("participants") or []
    return {
        "hackathon_id": p.get("hackathon_id") or "",
        "hackathon_title": p.get("hackathon_title") or "",
        "hackathon_url": p.get("hackathon_url") or "",
        "is_winner": bool(p.get("is_winner")),
        "winner_labels": ", ".join(p.get("winner_labels") or []),
        "project_title": p.get("project_title") or "",
        "project_url": p.get("project_url") or "",
        "tagline": p.get("tagline") or "",
        "github_url": p.get("github_url") or "",
        "participants": ", ".join(x.get("name", "") for x in participants if x.get("name")),
        "participant_profiles": ", ".join(x.get("profile_url", "") for x in participants if x.get("profile_url")),
        "participant_githubs": ", ".join(x.get("github", "") for x in participants if x.get("github")),
        "participant_linkedins": ", ".join(x.get("linkedin", "") for x in participants if x.get("linkedin")),
        "participant_twitters": ", ".join(x.get("twitter", "") for x in participants if x.get("twitter")),
        "participant_websites": ", ".join(x.get("website", "") for x in participants if x.get("website")),
        "built_with": ", ".join(p.get("built_with") or []),
        "external_links": ", ".join(p.get("external_links") or []),
    }


def write_projects_csv(projects: List[Dict], out_dir: Path, stem: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"projects_{stem}.csv"
    pd.DataFrame([_project_row(p) for p in projects], columns=PROJECT_COLUMNS).to_csv(
        path, index=False, encoding="utf-8"
    )
    logger.info("wrote %d projects to %s", len(projects), path)
    return path


def _hackathon_row(h: Dict) -> Dict:
    desc = (h.get("description") or "").replace("\n", " ")
    return {
        "id": h.get("id") or "",
        "title": h.get("title") or "",
        "url": h.get("url") or "",
        "source_platform": h.get("source_platform") or "",
        "sources": ", ".join(h.get("sources") or [h.get("source_platform") or ""]),
        "location": h.get("location") or "",
        "is_online": h.get("is_online"),
        "start_date": h.get("start_date") or "",
        "end_date": h.get("end_date") or "",
        "prize_pool": h.get("prize_pool") or "",
        "relevance_score": h.get("relevance_score"),
        "theme_is_ai": bool(h.get("ai_keywords_found")),
        "has_target_role": bool(h.get("target_roles_found")),
        "has_specific_tool": bool(h.get("tools_found")),
        "target_roles_found": ", ".join(h.get("target_roles_found") or []),
        "tools_found": ", ".join(h.get("tools_found") or []),
        "ai_keywords_found": ", ".join(h.get("ai_keywords_found") or []),
        "match_reasons": " | ".join(h.get("match_reasons") or []),
        "description_snippet": desc[:400],
    }


def _people_rows(hackathons: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for h in hackathons:
        for p in h.get("people") or []:
            rows.append(
                {
                    "hackathon_id": h.get("id") or "",
                    "hackathon_title": h.get("title") or "",
                    "name": p.get("name") or "",
                    "title": p.get("title") or "",
                    "target_role": match_role(p.get("title") or "") or "",
                    "context_role": p.get("context_role") or "",
                    "company": p.get("company") or "",
                    "linkedin": p.get("linkedin") or "",
                    "twitter": p.get("twitter") or "",
                }
            )
    return rows


def _company_rows(hackathons: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for h in hackathons:
        for c in h.get("companies") or []:
            rows.append(
                {
                    "hackathon_id": h.get("id") or "",
                    "hackathon_title": h.get("title") or "",
                    "name": c.get("name") or "",
                    "role": c.get("role") or "",
                    "website": c.get("website") or "",
                }
            )
    return rows


def write_csvs(hackathons: List[Dict], out_dir: Path, stem: str) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "hackathons": out_dir / f"hackathons_{stem}.csv",
        "people": out_dir / f"people_{stem}.csv",
        "companies": out_dir / f"companies_{stem}.csv",
    }

    pd.DataFrame([_hackathon_row(h) for h in hackathons], columns=HACKATHON_COLUMNS).to_csv(
        paths["hackathons"], index=False, encoding="utf-8"
    )
    pd.DataFrame(_people_rows(hackathons), columns=PEOPLE_COLUMNS).to_csv(
        paths["people"], index=False, encoding="utf-8"
    )
    pd.DataFrame(_company_rows(hackathons), columns=COMPANY_COLUMNS).to_csv(
        paths["companies"], index=False, encoding="utf-8"
    )

    logger.info(
        "wrote %d hackathons / %d people / %d companies",
        len(hackathons),
        sum(len(h.get("people") or []) for h in hackathons),
        sum(len(h.get("companies") or []) for h in hackathons),
    )
    return paths
