"""Re-parse all cached HTML files in data/raw/ and regenerate malt-1.json
(and the 3 CSVs + Excel). No network scraping.

Usage:
    python scripts/reparse_cached.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src.extractors.competitor_detector import detect_competitors  # noqa: E402
from src.extractors.experience_parser import parse_years  # noqa: E402
from src.extractors.location_filter import classify_location, is_allowed  # noqa: E402
from src.extractors.role_matcher import match_role  # noqa: E402
from src.extractors.skill_matcher import match_skills  # noqa: E402
from src.extractors.tjm_parser import parse_tjm  # noqa: E402
from src.scraper.missions_scraper import extract_missions  # noqa: E402
from src.scraper.profile_scraper import parse_profile  # noqa: E402
from src.scraper.reviews_scraper import extract_reviews  # noqa: E402
from src.storage.csv_writer import write_freelances, write_missions, write_skills  # noqa: E402
from src.storage.deduplicator import dedupe  # noqa: E402
from src.storage.excel_writer import write_excel  # noqa: E402
from src.storage.json_writer import write_json  # noqa: E402


def enrich(
    profile: Dict[str, Any],
    html: str,
    roles_cfg,
    skills_cfg,
    locations_cfg,
    competitors_cfg,
) -> Dict[str, Any]:
    profile["missions"] = extract_missions(html)
    profile["reviews"] = extract_reviews(html)

    loc = profile.get("location") or ""
    bucket = classify_location(loc, locations_cfg["allowed"])
    profile["city_category"] = bucket
    allowed_loc = is_allowed(loc, locations_cfg["allowed"], locations_cfg["remote_ok"])

    role_key = match_role(profile.get("title", ""), profile.get("bio", ""), roles_cfg)
    profile["matched_role"] = role_key

    matched, _ = match_skills(
        profile.get("skills") or [],
        profile.get("bio") or "",
        skills_cfg["by_category"],
    )
    profile["matched_skills"] = matched

    years = profile.get("years_experience") or parse_years(profile.get("bio", ""))
    profile["years_experience"] = years

    profile["tjm_eur"] = parse_tjm(profile.get("tjm", ""))

    comp = detect_competitors(profile["missions"], profile.get("bio") or "", competitors_cfg)
    profile["competitors_detected"] = comp

    profile["is_match"] = (
        allowed_loc
        and role_key is not None
        and len(matched) >= skills_cfg["min_match"]
    )
    profile["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return profile


def main() -> int:
    roles_cfg = config.load_roles()
    skills_cfg = config.load_skills()
    locations_cfg = config.load_locations()
    competitors_cfg = config.load_competitors()

    html_files = sorted(config.DATA_RAW.glob("*.html"))
    print(f"found {len(html_files)} cached HTML files")

    profiles: List[Dict[str, Any]] = []
    blocked: List[str] = []
    for path in html_files:
        slug = path.stem
        if slug == "freelancer-signup":
            continue
        url = f"https://www.malt.fr/profile/{slug}"
        html = path.read_text(encoding="utf-8")
        if "error code: 1015" in html.lower() or "access denied" in html.lower()[:2000]:
            blocked.append(url)
            continue
        try:
            profile = parse_profile(html, url)
        except Exception as exc:
            print(f"  ! parse failed for {slug}: {exc}")
            continue
        if not profile.get("name") and not profile.get("title"):
            blocked.append(url)
            continue
        profile = enrich(profile, html, roles_cfg, skills_cfg, locations_cfg, competitors_cfg)
        profiles.append(profile)
        print(
            f"  - {slug}: name={profile['name']!r} title={profile['title']!r} "
            f"loc={profile['city_category']} role={profile['matched_role']} "
            f"skills={len(profile['matched_skills'])} match={profile['is_match']}"
        )

    profiles = dedupe(profiles)

    key_skill_set = {
        s.lower()
        for skills in skills_cfg["by_category"].values()
        for s in skills
    }

    freelances_csv = config.DATA_FINAL / "freelances.csv"
    missions_csv = config.DATA_FINAL / "missions.csv"
    skills_csv = config.DATA_FINAL / "skills.csv"
    excel_out = config.DATA_FINAL / "malt_sourcing_mirakl.xlsx"
    json_out = config.DATA_FINAL / "malt-1.json"

    write_freelances(profiles, freelances_csv)
    write_missions(profiles, missions_csv)
    write_skills(profiles, skills_csv, key_skill_set)
    write_excel(profiles, freelances_csv, missions_csv, skills_csv, excel_out)
    summary = write_json(profiles, json_out)

    blocked_path = config.DATA_FINAL / "blocked_urls.txt"
    blocked_path.write_text("\n".join(blocked), encoding="utf-8")

    print("\n=== RÉSUMÉ ===")
    print(f"  total profils OK        : {summary['total_profiles']}")
    print(f"  blocked by Cloudflare   : {len(blocked)}")
    print(f"  is_match = True         : {summary['is_match_count']}")
    print(f"  worked_for_competitor   : {summary['worked_for_competitor_count']}")
    print(f"  top skills              : {[s['name'] for s in summary['top_skills'][:5]]}")
    print(f"  top concurrents détectés: {[c['name'] for c in summary['top_competitors'][:3]]}")
    print(f"\n  wrote {json_out}")
    print(f"  wrote {blocked_path} ({len(blocked)} urls to re-scrape)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
