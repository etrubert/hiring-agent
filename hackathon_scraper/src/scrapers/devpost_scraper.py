"""Devpost scraper — uses the public JSON search endpoint."""

import logging
from typing import Dict, List

from src.extractors.people_extractor import extract_people
from src.extractors.company_extractor import extract_companies
from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_json, get_html
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)


class DevpostScraper(BaseScraper):
    platform = "devpost"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("devpost disabled")
            return []

        max_pages = int(cfg.get("max_pages", 3))
        seen_urls: set = set()
        results: List[Dict] = []

        for base_url in cfg.get("search_urls", []):
            for page in range(1, max_pages + 1):
                sep = "&" if "?" in base_url else "?"
                url = f"{base_url}{sep}page={page}"
                payload = get_json(url)
                if not payload:
                    break
                hackathons = payload.get("hackathons") or []
                if not hackathons:
                    break
                for h in hackathons:
                    record = self._parse_entry(h)
                    if not record or record["url"] in seen_urls:
                        continue
                    seen_urls.add(record["url"])
                    results.append(record)

        self._enrich(results)
        logger.info("devpost: %d hackathons", len(results))
        return results

    def _parse_entry(self, h: Dict) -> Dict:
        url = h.get("url") or ""
        if url and url.startswith("//"):
            url = "https:" + url
        record = self._base_record(url, title=self._safe(h.get("title")))
        record["description"] = collapse(h.get("description") or "")
        themes = h.get("themes") or []
        record["tags_raw"] = ", ".join(
            t.get("name") if isinstance(t, dict) else str(t) for t in themes
        )
        record["start_date"] = self._safe(h.get("submission_period_dates"))
        record["prize_pool"] = self._safe(h.get("prize_amount"))
        location = h.get("displayed_location") or {}
        if isinstance(location, dict):
            record["location"] = self._safe(location.get("location"))
        record["is_online"] = "online" in (record["location"] or "").lower()
        return record

    def _enrich(self, records: List[Dict]) -> None:
        for rec in records[:40]:
            html = get_html(rec["url"])
            if not html:
                continue
            rec["people"] = extract_people(html)
            rec["companies"] = extract_companies(html)
            if not rec["description"]:
                rec["description"] = collapse(html)[:2000]
