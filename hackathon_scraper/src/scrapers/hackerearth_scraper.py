"""HackerEarth scraper — uses the public /chrome-ext/events/ JSON endpoint
with an HTML fallback."""

import logging
from typing import Dict, List

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_html, get_json
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)


class HackerEarthScraper(BaseScraper):
    platform = "hackerearth"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("hackerearth disabled")
            return []

        results: List[Dict] = []
        api_url = cfg.get("api_url")
        if api_url:
            data = get_json(api_url)
            if data:
                for section in ("live", "upcoming", "recent", "challenges", "events"):
                    for item in (data.get(section) or []):
                        rec = self._parse_api(item)
                        if rec:
                            results.append(rec)

        if not results:
            html = get_html(cfg.get("listing_url") or "")
            if html:
                results.extend(self._parse_html_listing(html))

        logger.info("hackerearth: %d events", len(results))
        return results

    def _parse_api(self, item: Dict) -> Dict:
        url = item.get("url") or item.get("challenge_url") or ""
        if url and url.startswith("/"):
            url = "https://www.hackerearth.com" + url
        title = self._safe(item.get("title") or item.get("challenge_name") or "")
        if not url or not title:
            return {}
        rec = self._base_record(url, title=title)
        rec["description"] = self._safe(item.get("description") or item.get("desc") or "")
        rec["start_date"] = self._safe(item.get("start_tz") or item.get("start_date") or "")
        rec["end_date"] = self._safe(item.get("end_tz") or item.get("end_date") or "")
        rec["tags_raw"] = title + " " + self._safe(item.get("challenge_type") or "")
        rec["prize_pool"] = self._safe(item.get("prizes") or "")
        return rec

    def _parse_html_listing(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        out: List[Dict] = []
        for card in soup.select(".challenge-card, .challenge-card-modern"):
            link = card.find("a", href=True)
            if not link:
                continue
            url = link["href"]
            if url.startswith("/"):
                url = "https://www.hackerearth.com" + url
            title = collapse(
                (card.select_one(".challenge-name") or link).get_text(" ", strip=True)
            )
            if not title:
                continue
            rec = self._base_record(url, title=title)
            rec["tags_raw"] = title
            rec["description"] = collapse(card.get_text(" ", strip=True))[:800]
            out.append(rec)
        return out
