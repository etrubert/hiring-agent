"""Meetup stub — GraphQL requires login. Enable manually once auth is wired."""

import logging
from typing import Dict, List

from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MeetupScraper(BaseScraper):
    platform = "meetup"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("meetup stub — enable manually once auth is wired")
            return []
        logger.warning("meetup scraper is a stub and has no implementation yet")
        return []
