"""LinkedIn stub — search endpoints require an authenticated session cookie.

Activate only once you have a valid `li_at` cookie in your env and have
implemented a compliant path (or the official Events API).
"""

import logging
from typing import Dict, List

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    platform = "linkedin"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("linkedin stub — enable manually once auth is wired")
            return []
        logger.warning("linkedin scraper is a stub and has no implementation yet")
        return []
