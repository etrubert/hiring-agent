"""Build malt-2.json from all fallback sources (Wayback + search snippets).

Combines data recovered for the 20 Cloudflare-blocked URLs via:
  - Wayback Machine snapshots (full HTML parse via OG/meta fallback)
  - DuckDuckGo + Brave search result snippets (name + title only)

Outputs data/final/malt-2.json with the same schema as malt-1.json.
"""

import html as html_lib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src.extractors.competitor_detector import detect_competitors  # noqa: E402
from src.extractors.experience_parser import parse_years  # noqa: E402
from src.extractors.location_filter import classify_location, is_allowed  # noqa: E402
from src.extractors.role_matcher import match_role  # noqa: E402
from src.extractors.skill_matcher import match_skills  # noqa: E402
from src.extractors.tjm_parser import parse_tjm  # noqa: E402
from src.scraper.missions_scraper import extract_missions  # noqa: E402
from src.scraper.profile_scraper import (  # noqa: E402
    _availability,
    _bio_from_html,
    _external_links,
    _rating_from_html,
    _years_experience,
    parse_profile,
)
from src.scraper.reviews_scraper import extract_reviews  # noqa: E402
from src.storage.deduplicator import dedupe  # noqa: E402
from src.storage.json_writer import write_json  # noqa: E402


def parse_wayback(html: str, url: str) -> Dict[str, Any]:
    """Parse a Wayback-archived Malt profile page (no JSON-LD, uses OG/meta)."""
    # Try JSON-LD first in case it's a recent snapshot
    base = parse_profile(html, url)
    if base.get("name") or base.get("title"):
        return base

    soup = BeautifulSoup(html, "lxml")

    def meta(name: str, prop: bool = False) -> str:
        attr = "property" if prop else "name"
        m = soup.find("meta", attrs={attr: name})
        return (m.get("content") or "").strip() if m else ""

    og_title = meta("og:title", prop=True) or meta("twitter:title")
    og_desc = meta("og:description", prop=True) or meta("twitter:description")

    raw = re.sub(
        r"^(Découvrez le profil freelance de\s+|Voir le profil freelance de\s+)",
        "",
        og_title,
        flags=re.I,
    ).strip()
    raw = re.sub(r"\s*[-|]\s*Malt\s*$", "", raw, flags=re.I)
    parts = re.split(r",\s*", raw, maxsplit=1)
    name = html_lib.unescape(parts[0]) if parts else ""
    title = html_lib.unescape(parts[1]) if len(parts) > 1 else ""

    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(" ", strip=True)

    bio = _bio_from_html(soup) or (html_lib.unescape(og_desc) if og_desc else "")

    skills: List[str] = []
    for sel in ['[class*="skill"]', '[data-testid*="skill"]', '[class*="tag"]']:
        try:
            for el in soup.select(sel):
                txt = el.get_text(" ", strip=True)
                if 1 < len(txt) < 40 and not any(c in txt for c in "{}()"):
                    if txt not in skills:
                        skills.append(txt)
        except Exception:
            pass
    skills = skills[:30]

    text = soup.get_text(" ", strip=True)
    location = ""
    for city in ["Paris", "Bordeaux", "Lyon", "Marseille", "Toulouse", "Nantes", "Lille", "Nice"]:
        if re.search(rf"\b{city}\b", text):
            location = city
            break

    ext = _external_links(soup)
    r = _rating_from_html(soup)

    return {
        "profile_url": url,
        "name": name,
        "title": title,
        "location": location,
        "postal_code": "",
        "years_experience": _years_experience(soup, bio),
        "skills": skills,
        "tjm": "",
        "bio": bio,
        "availability": _availability(soup),
        "rating": r["rating"],
        "reviews_count": r["reviews_count"],
        "languages": [],
        "github_url": ext["github"],
        "kaggle_url": ext["kaggle"],
        "stackoverflow_url": ext["stackoverflow"],
        "linkedin_url": ext["linkedin"],
        "twitter_url": ext["twitter"],
        "certifications": ext["certifications"],
        "other_links": ext["other"],
    }


def minimal_profile(url: str, name: str, title: str, desc: str) -> Dict[str, Any]:
    """Shell profile from search-result snippet (name + title only)."""
    return {
        "profile_url": url,
        "name": name,
        "title": title,
        "location": "",
        "postal_code": "",
        "years_experience": None,
        "skills": [],
        "tjm": "",
        "bio": desc,
        "availability": "",
        "rating": None,
        "reviews_count": None,
        "languages": [],
        "github_url": "",
        "kaggle_url": "",
        "stackoverflow_url": "",
        "linkedin_url": "",
        "twitter_url": "",
        "certifications": [],
        "other_links": [],
    }


def enrich(
    prof: Dict[str, Any],
    html: Optional[str],
    roles_cfg,
    skills_cfg,
    locations_cfg,
    competitors_cfg,
    source: str,
) -> Dict[str, Any]:
    prof["missions"] = extract_missions(html) if html else []
    prof["reviews"] = extract_reviews(html) if html else []

    loc = prof.get("location") or ""
    prof["city_category"] = classify_location(loc, locations_cfg["allowed"])
    allowed_loc = is_allowed(loc, locations_cfg["allowed"], locations_cfg["remote_ok"])

    prof["matched_role"] = match_role(prof.get("title", ""), prof.get("bio", ""), roles_cfg)
    matched, _ = match_skills(
        prof.get("skills") or [],
        prof.get("bio") or "",
        skills_cfg["by_category"],
    )
    prof["matched_skills"] = matched

    prof["years_experience"] = prof.get("years_experience") or parse_years(prof.get("bio", ""))
    prof["tjm_eur"] = parse_tjm(prof.get("tjm", ""))
    prof["competitors_detected"] = detect_competitors(
        prof["missions"], prof.get("bio") or "", competitors_cfg
    )
    prof["is_match"] = bool(
        allowed_loc
        and prof["matched_role"] is not None
        and len(matched) >= skills_cfg["min_match"]
    )
    prof["scraped_at"] = datetime.now(timezone.utc).isoformat()
    prof["source"] = source
    return prof


def main() -> int:
    roles_cfg = config.load_roles()
    skills_cfg = config.load_skills()
    locations_cfg = config.load_locations()
    competitors_cfg = config.load_competitors()

    blocked_urls = Path(config.DATA_FINAL / "blocked_urls.txt").read_text().strip().split("\n")
    blocked_by_slug = {u.rstrip("/").split("/")[-1]: u for u in blocked_urls}

    # --- Source 1: Wayback HTMLs
    wb_dir = config.DATA_RAW.parent / "raw_wayback"
    wb_profiles: Dict[str, Dict[str, Any]] = {}
    if wb_dir.exists():
        for p in sorted(wb_dir.glob("*.html")):
            slug = p.stem
            url = blocked_by_slug.get(slug) or f"https://www.malt.fr/profile/{slug}"
            html = p.read_text(encoding="utf-8", errors="ignore")
            prof = parse_wayback(html, url)
            if prof.get("name") or prof.get("title"):
                prof = enrich(prof, html, roles_cfg, skills_cfg, locations_cfg, competitors_cfg, "wayback_machine")
                wb_profiles[slug] = prof
                print(f"  WB  {slug:30s} name={prof['name']!r}  role={prof['matched_role']}  match={prof['is_match']}")
            else:
                print(f"  WB  {slug:30s} (JSON-LD absent et OG vide — rejected)")

    # --- Source 2: DDG/Brave snippets
    ddg_path = Path("/tmp/ddg_results.json")
    snippet_profiles: Dict[str, Dict[str, Any]] = {}
    if ddg_path.exists():
        snippets = json.loads(ddg_path.read_text())
        for s in snippets:
            slug = s["slug"]
            if not s.get("name") or slug in wb_profiles:
                continue
            prof = minimal_profile(s["url"], s["name"], s.get("title", ""), s.get("desc", ""))
            prof = enrich(prof, None, roles_cfg, skills_cfg, locations_cfg, competitors_cfg, "search_snippet")
            snippet_profiles[slug] = prof
            print(f"  SN  {slug:30s} name={prof['name']!r}  role={prof['matched_role']}  match={prof['is_match']}")

    # Combine
    profiles = list(wb_profiles.values()) + list(snippet_profiles.values())
    profiles = dedupe(profiles)

    # Build recovery-status report
    recovered_slugs = {
        **{k: "wayback_machine" for k in wb_profiles},
        **{k: "search_snippet" for k in snippet_profiles},
    }
    missing = [u for slug, u in blocked_by_slug.items() if slug not in recovered_slugs]

    out_path = config.DATA_FINAL / "malt-2.json"
    summary = write_json(profiles, out_path)

    # Augment JSON with recovery metadata
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    payload["recovery"] = {
        "total_blocked": len(blocked_urls),
        "recovered": len(profiles),
        "not_recovered": len(missing),
        "sources": {
            "wayback_machine": len(wb_profiles),
            "search_snippet": len(snippet_profiles),
        },
        "not_recovered_urls": missing,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== RÉSUMÉ malt-2.json ===")
    print(f"  profils récupérés    : {len(profiles)}/{len(blocked_urls)}")
    print(f"  via Wayback          : {len(wb_profiles)}")
    print(f"  via snippet recherche: {len(snippet_profiles)}")
    print(f"  is_match = True      : {summary['is_match_count']}")
    print(f"  non récupérables     : {len(missing)}")
    print(f"\n  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
