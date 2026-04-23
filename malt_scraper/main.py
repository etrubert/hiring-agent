"""CLI orchestrator for the Malt freelance scraper.

Pipeline:
  1. Legal disclaimer (CGU + RGPD)
  2. Load YAML configs
  3. Playwright stealth session
  4. For each query -> extract profile URLs
  5. For each profile -> scrape full page + missions + reviews
  6. Apply extractors (location, role, skills, experience, competitors, TJM)
  7. Export CSV + Excel + malt-1.json
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

import config
from src.extractors.competitor_detector import detect_competitors
from src.extractors.experience_parser import parse_years
from src.extractors.location_filter import classify_location, is_allowed
from src.extractors.role_matcher import match_role
from src.extractors.skill_matcher import match_skills
from src.extractors.tjm_parser import parse_tjm
from src.scraper.malt_session import MaltSession
from src.scraper.missions_scraper import extract_missions
from src.scraper.profile_scraper import scrape_profile
from src.scraper.reviews_scraper import extract_reviews
from src.scraper.search_scraper import scrape_search
from src.storage.csv_writer import write_freelances, write_missions, write_skills
from src.storage.deduplicator import dedupe
from src.storage.excel_writer import write_excel
from src.storage.json_writer import write_json
from src.utils.anti_detection import sleep_random
from src.utils.logger import setup_logging

DISCLAIMER = """\
======================================================================
 MALT SCRAPER — AVERTISSEMENT LÉGAL
----------------------------------------------------------------------
 - Scraper Malt viole leurs CGU -> risque de ban du compte.
 - Collecte de données personnelles -> RGPD: usage strictement interne
   / démo jury. Pas de revente, pas de prospection sans consentement.
 - Délais 3-8s entre requêtes obligatoires (anti-bot).
 - Si Cloudflare bloque, le scraper s'arrête et log l'incident.
======================================================================
"""


def confirm(yes: bool) -> bool:
    if yes:
        return True
    print(DISCLAIMER)
    r = input("Continuer ? [y/N] ").strip().lower()
    return r in {"y", "yes", "o", "oui"}


def enrich_profile(
    profile: Dict[str, Any],
    roles_cfg: Dict[str, Any],
    skills_cfg: Dict[str, Any],
    locations_cfg: Dict[str, Any],
    competitors_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    html = profile.pop("_raw_html", "") or ""
    profile["missions"] = extract_missions(html) if html else []
    profile["reviews"] = extract_reviews(html) if html else []

    loc = profile.get("location") or ""
    bucket = classify_location(loc, locations_cfg["allowed"])
    profile["city_category"] = bucket
    allowed_loc = is_allowed(loc, locations_cfg["allowed"], locations_cfg["remote_ok"])

    role_key = match_role(profile.get("title", ""), profile.get("bio", ""), roles_cfg)
    profile["matched_role"] = role_key

    matched, _unmatched = match_skills(
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


async def run(args: argparse.Namespace) -> int:
    setup_logging(config.LOG_DIR)
    log = logging.getLogger("main")

    if not confirm(args.yes):
        log.info("user declined — aborting")
        return 1

    roles_cfg = config.load_roles()
    skills_cfg = config.load_skills()
    locations_cfg = config.load_locations()
    competitors_cfg = config.load_competitors()
    search_cfg = config.load_search_queries()

    max_total = min(args.max or search_cfg["max_total"], search_cfg["max_total"])

    session = MaltSession(headless=config.HEADLESS, proxy_url=config.PROXY_URL)
    await session.start()

    all_urls: List[str] = []
    try:
        for q in tqdm(search_cfg["queries"], desc="search queries"):
            if len(all_urls) >= max_total:
                break
            try:
                urls = await scrape_search(
                    session,
                    q["query"],
                    q["location"],
                    search_cfg["max_per_query"],
                    config.DELAY_REQ_MIN,
                    config.DELAY_REQ_MAX,
                )
                for u in urls:
                    if u not in all_urls:
                        all_urls.append(u)
                    if len(all_urls) >= max_total:
                        break
            except Exception as exc:
                log.exception("search failed: %s @ %s: %s", q.get("query"), q.get("location"), exc)
            await sleep_random(config.DELAY_PAGE_MIN, config.DELAY_PAGE_MAX)

        log.info("collected %d profile urls", len(all_urls))

        profiles: List[Dict[str, Any]] = []
        for i, url in enumerate(tqdm(all_urls[:max_total], desc="profiles"), start=1):
            try:
                prof = await scrape_profile(
                    session,
                    url,
                    config.DELAY_PAGE_MIN,
                    config.DELAY_PAGE_MAX,
                    screenshots_dir=config.DATA_SCREENSHOTS,
                    raw_html_dir=config.DATA_RAW,
                )
                prof = enrich_profile(prof, roles_cfg, skills_cfg, locations_cfg, competitors_cfg)
                profiles.append(prof)
                json_path = config.DATA_JSON / f"{prof.get('profile_url', '').split('/')[-1][:60]}.json"
                json_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as exc:
                log.exception("profile failed: %s: %s", url, exc)
            if i % 10 == 0:
                _crash_save(profiles)
            await sleep_random(config.DELAY_PAGE_MIN, config.DELAY_PAGE_MAX)
    finally:
        await session.close()

    profiles = dedupe(profiles)
    log.info("after dedup: %d profiles", len(profiles))

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

    print("\n=== RÉSUMÉ ===")
    print(f"  total profils           : {summary['total_profiles']}")
    print(f"  is_match = True         : {summary['is_match_count']}")
    print(f"  worked_for_competitor   : {summary['worked_for_competitor_count']}")
    print(f"  top skills              : {[s['name'] for s in summary['top_skills'][:5]]}")
    print(f"  top concurrents détectés: {[c['name'] for c in summary['top_competitors'][:3]]}")
    print("\n=== FICHIERS ===")
    print(f"  {json_out}")
    print(f"  {freelances_csv}")
    print(f"  {missions_csv}")
    print(f"  {skills_csv}")
    print(f"  {excel_out}")
    return 0


def _crash_save(profiles: List[Dict[str, Any]]) -> None:
    path = config.DATA_JSON / "_crash_backup.json"
    path.write_text(json.dumps(profiles, ensure_ascii=False, default=str), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Malt freelance scraper (Mirakl sourcing)")
    ap.add_argument("--yes", "-y", action="store_true", help="skip le disclaimer interactif")
    ap.add_argument("--max", type=int, default=None, help="override MAX_PROFILES")
    ap.add_argument("--smoke", action="store_true", help="just load malt.fr + screenshot to test stealth")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(config.LOG_DIR)
    if args.smoke:
        from src.scraper.malt_session import smoke_test
        ok = asyncio.run(smoke_test(config.DATA_SCREENSHOTS))
        print("smoke:", "OK" if ok else "FAIL — check data/screenshots/smoke_homepage.png")
        return 0 if ok else 2
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
