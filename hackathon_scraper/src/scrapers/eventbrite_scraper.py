"""Eventbrite scraper — requires EVENTBRITE_TOKEN. Otherwise no-op."""

import logging
from typing import Dict, List

import config
from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_json

logger = logging.getLogger(__name__)


class EventbriteScraper(BaseScraper):
    platform = "eventbrite"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("eventbrite disabled")
            return []
        if not config.EVENTBRITE_TOKEN:
            logger.warning("eventbrite skipped — EVENTBRITE_TOKEN not set")
            return []

        headers = {"Authorization": f"Bearer {config.EVENTBRITE_TOKEN}"}
        results: List[Dict] = []
        for query in cfg.get("queries", []):
            data = get_json(cfg["api_url"], params={"q": query}, headers=headers)
            if not data:
                continue
            for ev in data.get("events") or []:
                url = ev.get("url") or ""
                title = self._safe((ev.get("name") or {}).get("text"))
                if not url or not title:
                    continue
                rec = self._base_record(url, title=title)
                rec["description"] = self._safe((ev.get("description") or {}).get("text"))
                rec["start_date"] = self._safe((ev.get("start") or {}).get("local"))[:10]
                rec["end_date"] = self._safe((ev.get("end") or {}).get("local"))[:10]
                rec["is_online"] = bool(ev.get("online_event"))
                rec["tags_raw"] = query + " " + title
                results.append(rec)
        logger.info("eventbrite: %d events", len(results))
        return results
