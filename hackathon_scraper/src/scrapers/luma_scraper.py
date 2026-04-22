"""lu.ma stub — listings are rendered by JS. Enable once Playwright or the
official API key is wired up."""

import logging
from typing import Dict, List

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LumaScraper(BaseScraper):
    platform = "luma"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("luma stub — enable manually once playwright/api is ready")
            return []
        logger.warning("luma scraper is a stub and has no implementation yet")
        return []
