"""CLI orchestrator for the podcast guest scraper."""

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
from src import rss_scraper
from src.youtube_scraper import YouTubeScraper
from src.extractor import extract_all
from src.classifier import Classifier
from src.deduplicator import deduplicate
from src.exporter import export_csv, export_json, export_excel, export_readable, save_intermediate
from src.lang_filter import filter_french


def setup_logging() -> None:
    log_path = config.LOG_DIR / f"scraper_{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def load_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_youtube(max_per_channel: int, max_per_query: int) -> List[Dict]:
    cfg = load_yaml(config.SOURCES_DIR / "youtube_channels.yaml")
    scraper = YouTubeScraper()
    episodes: List[Dict] = []

    for ch in tqdm(cfg.get("channels", []), desc="YouTube channels"):
        handle = ch.get("handle")
        if not handle:
            continue
        try:
            batch = scraper.fetch_channel(handle, max_per_channel)
            episodes.extend(batch)
            logging.info("channel %s -> %d videos", ch["name"], len(batch))
        except Exception as exc:
            logging.exception("channel %s failed: %s", ch["name"], exc)

    for q in tqdm(cfg.get("search_queries", []), desc="YouTube queries"):
        try:
            batch = scraper.search(q, max_per_query)
            episodes.extend(batch)
            logging.info("query %r -> %d videos", q, len(batch))
        except Exception as exc:
            logging.exception("query %r failed: %s", q, exc)

    return episodes


def run_rss(max_per_feed: int) -> List[Dict]:
    cfg = load_yaml(config.SOURCES_DIR / "rss_feeds.yaml")
    episodes: List[Dict] = []
    for feed in tqdm(cfg.get("feeds", []), desc="RSS feeds"):
        try:
            batch = rss_scraper.fetch_feed(feed["name"], feed["url"], max_per_feed)
            episodes.extend(batch)
            logging.info("feed %s -> %d episodes", feed["name"], len(batch))
        except Exception as exc:
            logging.exception("feed %s failed: %s", feed.get("name"), exc)
    return episodes


def enrich(episodes: List[Dict]) -> List[Dict]:
    return [extract_all(ep) for ep in episodes]


def classify_all(episodes: List[Dict], intermediate_path: Path) -> List[Dict]:
    provider = config.LLM_PROVIDER
    if provider == "anthropic" and not config.ANTHROPIC_API_KEY:
        logging.warning("ANTHROPIC_API_KEY not set — skipping classification")
        for ep in episodes:
            ep.setdefault("is_ai_guest", None)
            ep.setdefault("role_detected", "")
            ep.setdefault("confidence", None)
            ep.setdefault("reasoning", "")
        return episodes

    logging.info("classification provider: %s", provider)
    classifier = Classifier(
        provider=provider,
        anthropic_api_key=config.ANTHROPIC_API_KEY,
        claude_model=config.CLAUDE_MODEL,
        ollama_model=config.OLLAMA_MODEL,
    )
    for idx, ep in enumerate(tqdm(episodes, desc="Classifying")):
        try:
            result = classifier.classify(
                title=ep.get("title", ""),
                description=ep.get("description", ""),
                channel=ep.get("channel_title", ""),
            )
            if result:
                ep["is_ai_guest"] = result.is_ai_guest
                ep["role_detected"] = result.role_detected
                ep["confidence"] = result.confidence
                ep["reasoning"] = result.reasoning
                if result.guest_name and not ep.get("guest_name"):
                    ep["guest_name"] = result.guest_name
            else:
                ep.setdefault("is_ai_guest", None)
                ep.setdefault("role_detected", "")
                ep.setdefault("confidence", None)
                ep.setdefault("reasoning", "")
        except Exception as exc:
            logging.exception("classify failed for %s: %s", ep.get("url"), exc)
            ep.setdefault("is_ai_guest", None)
            ep.setdefault("role_detected", "")
            ep.setdefault("confidence", None)
            ep.setdefault("reasoning", str(exc))
        if (idx + 1) % config.SAVE_EVERY_N == 0:
            save_intermediate(episodes, intermediate_path)
            logging.info("intermediate save at %d episodes", idx + 1)
    return episodes


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI podcast guest scraper")
    p.add_argument("--sources", default="youtube,rss", help="Comma list: youtube,rss")
    p.add_argument("--max-per-channel", type=int, default=config.MAX_PER_CHANNEL)
    p.add_argument("--max-per-query", type=int, default=config.MAX_PER_QUERY)
    p.add_argument("--max-per-feed", type=int, default=config.MAX_PER_CHANNEL)
    p.add_argument("--classify", action="store_true", help="Run classification (uses LLM_PROVIDER)")
    p.add_argument("--resume", action="store_true", help="Skip scraping; load episodes_enriched.json from cache")
    p.add_argument("--ai-only", action="store_true", help="Keep only is_ai_guest=True rows in final export")
    p.add_argument("--fr-only", action="store_true", help="Keep only French-language episodes (heuristic language filter).")
    p.add_argument("--output", default=str(config.DATA_FINAL / "podcasts.csv"))
    p.add_argument("--excel", action="store_true", help="Also write Excel file with per-role tabs")
    p.add_argument("--json", action="store_true", help="Also write JSON file")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging()

    cache_path = config.DATA_PROCESSED / "episodes_enriched.json"
    if args.resume:
        if not cache_path.exists():
            logging.error("--resume requested but cache %s does not exist", cache_path)
            return 1
        deduped = json.loads(cache_path.read_text(encoding="utf-8"))
        logging.info("resumed from cache: %d episodes", len(deduped))
    else:
        sources = {s.strip() for s in args.sources.split(",") if s.strip()}
        raw_episodes: List[Dict] = []

        if "youtube" in sources:
            raw_episodes.extend(run_youtube(args.max_per_channel, args.max_per_query))
        if "rss" in sources:
            raw_episodes.extend(run_rss(args.max_per_feed))

        logging.info("raw episodes: %d", len(raw_episodes))
        save_intermediate(raw_episodes, config.DATA_RAW / "episodes_raw.json")

        enriched = enrich(raw_episodes)
        deduped = deduplicate(enriched)
        logging.info("after dedup: %d", len(deduped))
        save_intermediate(deduped, cache_path)

    if args.classify:
        deduped = classify_all(deduped, config.DATA_PROCESSED / "episodes_classified.json")
        save_intermediate(deduped, config.DATA_PROCESSED / "episodes_classified.json")

    final = deduped
    if args.fr_only:
        before = len(final)
        final = filter_french(final)
        logging.info("fr-only filter: %d -> %d rows kept", before, len(final))
    if args.ai_only:
        final = [ep for ep in final if ep.get("is_ai_guest")]
        logging.info("ai-only filter: %d rows kept", len(final))

    out_path = Path(args.output)
    export_csv(final, out_path)
    export_readable(final, out_path.with_suffix(".txt"))
    if args.json:
        export_json(final, out_path.with_suffix(".json"))
    if args.excel:
        export_excel(final, out_path.with_suffix(".xlsx"))

    logging.info("done — final rows: %d", len(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
