"""CLI orchestrator for the hackathon scraper."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml
from tqdm import tqdm

import config
from src.extractors.relevance_scorer import annotate
from src.scrapers.ai_tinkerers_scraper import AITinkerersScraper
from src.scrapers.devpost_projects_scraper import enrich_with_projects
from src.scrapers.devpost_scraper import DevpostScraper
from src.scrapers.eventbrite_scraper import EventbriteScraper
from src.scrapers.hackerearth_scraper import HackerEarthScraper
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.linkedin_scraper import LinkedInScraper
from src.scrapers.luma_scraper import LumaScraper
from src.scrapers.meetup_scraper import MeetupScraper
from src.scrapers.mlh_scraper import MLHScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.tavily_discovery import TavilyDiscovery
from src.storage.csv_writer import write_csvs, write_projects_csv
from src.storage.deduplicator import deduplicate
from src.storage.excel_writer import write_excel
from src.storage.readable_writer import write_readable_report
from src.utils.logger import setup_logging

SCRAPERS = {
    "devpost": DevpostScraper,
    "mlh": MLHScraper,
    "hackerearth": HackerEarthScraper,
    "hackernews": HackerNewsScraper,
    "ai_tinkerers": AITinkerersScraper,
    "luma": LumaScraper,
    "linkedin": LinkedInScraper,
    "eventbrite": EventbriteScraper,
    "meetup": MeetupScraper,
    "reddit": RedditScraper,
    "tavily": TavilyDiscovery,
}


def load_platforms() -> Dict:
    path = config.SOURCES_DIR / "platforms.yaml"
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_scrapers(platforms: List[str], cfg_all: Dict) -> List[Dict]:
    results: List[Dict] = []
    for name in tqdm(platforms, desc="Platforms"):
        cls = SCRAPERS.get(name)
        if not cls:
            logging.warning("unknown platform: %s", name)
            continue
        cfg = cfg_all.get(name) or {}
        try:
            batch = cls().fetch(cfg)
            results.extend(batch)
            logging.info("%s -> %d hackathons", name, len(batch))
        except Exception as exc:
            logging.exception("%s failed: %s", name, exc)
    return results


def save_intermediate(records: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI hackathon scraper")
    p.add_argument(
        "--platforms",
        default="",
        help="Comma list; empty = all enabled in platforms.yaml",
    )
    p.add_argument(
        "--min-score",
        type=int,
        default=config.MIN_RELEVANCE_SCORE,
        help="Drop records below this score after the keep-rule check",
    )
    p.add_argument(
        "--keep-all",
        action="store_true",
        help="Skip the strict keep rule (write every record with its score).",
    )
    p.add_argument("--resume", action="store_true", help="Skip scraping; load last raw snapshot.")
    p.add_argument("--excel", action="store_true", help="Also write Excel workbook.")
    p.add_argument(
        "--projects",
        action="store_true",
        help="For every kept Devpost hackathon, fetch the project gallery and write projects_*.csv.",
    )
    p.add_argument(
        "--max-projects-per-hackathon",
        type=int,
        default=60,
        help="Cap on projects fetched per Devpost hackathon (default 60).",
    )
    p.add_argument(
        "--enrich-profiles",
        action="store_true",
        help="Fetch each participant's Devpost profile to extract LinkedIn/GitHub/Twitter. Slow.",
    )
    p.add_argument("--stem", default=datetime.now().strftime("%Y%m%d_%H%M"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging()

    cfg_all = load_platforms()
    enabled_from_cfg = [name for name, block in cfg_all.items() if block and block.get("enabled")]
    chosen = (
        [p.strip() for p in args.platforms.split(",") if p.strip()]
        if args.platforms
        else enabled_from_cfg
    )
    if not chosen:
        logging.error("no platforms enabled — edit sources/platforms.yaml")
        return 1
    logging.info("platforms: %s", ", ".join(chosen))

    raw_path = config.DATA_RAW / "hackathons_raw.json"
    if args.resume:
        if not raw_path.exists():
            logging.error("--resume but no cache at %s", raw_path)
            return 1
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        logging.info("resumed: %d records", len(raw))
    else:
        raw = run_scrapers(chosen, cfg_all)
        logging.info("raw total: %d", len(raw))
        save_intermediate(raw, raw_path)

    deduped = deduplicate(raw)
    save_intermediate(deduped, config.DATA_FILTERED / "hackathons_deduped.json")

    scored = [annotate(h) for h in deduped]
    save_intermediate(scored, config.DATA_FILTERED / "hackathons_scored.json")

    if args.keep_all:
        kept = scored
    else:
        kept = [h for h in scored if h.get("keep") and (h.get("relevance_score") or 0) >= args.min_score]
    logging.info("kept after filter: %d (min_score=%d)", len(kept), args.min_score)

    kept.sort(key=lambda h: h.get("relevance_score") or 0, reverse=True)

    paths = write_csvs(kept, config.DATA_FINAL, args.stem)

    projects: List[Dict] = []
    if args.projects:
        projects = enrich_with_projects(
            kept,
            max_projects=args.max_projects_per_hackathon,
            enrich_profiles=args.enrich_profiles,
        )
        save_intermediate(projects, config.DATA_FILTERED / "projects_raw.json")
        paths["projects"] = write_projects_csv(projects, config.DATA_FINAL, args.stem)

    report_path = config.DATA_FINAL / f"report_{args.stem}.txt"
    write_readable_report(kept, projects, report_path)
    paths["report"] = report_path

    if args.excel:
        excel_path = config.DATA_FINAL / f"hackathons_{args.stem}.xlsx"
        write_excel(kept, excel_path)
        paths["excel"] = excel_path

    logging.info("done — outputs: %s", {k: str(v) for k, v in paths.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
