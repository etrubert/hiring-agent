"""Major League Hacking scraper — parses the public seasons/events HTML page.

MLH rebuilt its events page with Tailwind (2025+); no semantic classes remain.
The reliable signal is the outbound event link tagged with
`utm_campaign=events`, whose `utm_content` param is the event name.
"""

import logging
import re
from typing import Dict, List
from urllib.parse import unquote

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_html
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)


class MLHScraper(BaseScraper):
    platform = "mlh"

    _UTM_CONTENT_RE = re.compile(r"utm_content=([^&]+)")

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("mlh disabled")
            return []

        urls = [cfg.get("seasons_url")] + list(cfg.get("fallback_urls", []))
        urls = [u for u in urls if u]
        seen: set = set()
        results: List[Dict] = []

        for url in urls:
            html = get_html(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "utm_campaign=events" not in href or href in seen:
                    continue
                seen.add(href)
                rec = self._parse_event(a, href)
                if rec:
                    results.append(rec)

        logger.info("mlh: %d events", len(results))
        return results

    def _parse_event(self, anchor, href: str) -> Dict:
        title = self._extract_title(href, anchor)
        if not title:
            return {}
        rec = self._base_record(href, title=title)
        rec["tags_raw"] = title

        parent = anchor
        for _ in range(5):
            parent = parent.parent
            if parent is None:
                break
        if parent is not None:
            text = collapse(parent.get_text(" ", strip=True))
            rec["description"] = text[:1000]
            loc_text = text.lower()
            rec["is_online"] = "digital" in loc_text or "online" in loc_text
            m_date = re.search(r"[A-Z]{3}\s+\d{1,2}\s*-\s*\d{1,2}", text)
            if m_date:
                rec["start_date"] = m_date.group(0)
            m_loc = re.search(r"(In-Person|Digital|Online|Hybrid)", text, re.IGNORECASE)
            if m_loc:
                rec["location"] = m_loc.group(0)
        return rec

    def _extract_title(self, href: str, anchor) -> str:
        m = self._UTM_CONTENT_RE.search(href)
        if m:
            return unquote(m.group(1).replace("+", " "))
        return collapse(anchor.get_text(" ", strip=True))
