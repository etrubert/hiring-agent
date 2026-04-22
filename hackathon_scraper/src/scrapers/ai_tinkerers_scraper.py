"""AI Tinkerers scraper — public city-chapter pages list upcoming events as HTML."""

import logging
from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_html
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)


class AITinkerersScraper(BaseScraper):
    platform = "ai_tinkerers"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("ai_tinkerers disabled")
            return []

        results: List[Dict] = []
        seen: set = set()
        for url in cfg.get("urls", []):
            html = get_html(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select("[data-event], .event, article"):
                link = card.find("a", href=True)
                if not link:
                    continue
                href = urljoin(url, link["href"])
                if href in seen:
                    continue
                seen.add(href)
                title = collapse(
                    (card.select_one("h2, h3, .event-title") or link).get_text(" ", strip=True)
                )
                if not title:
                    continue
                rec = self._base_record(href, title=title)
                rec["location"] = url.split("//")[-1].split(".")[0]
                rec["description"] = collapse(card.get_text(" ", strip=True))[:1500]
                rec["tags_raw"] = title + " AI"
                results.append(rec)

        logger.info("ai_tinkerers: %d events", len(results))
        return results
