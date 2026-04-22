"""Tavily discovery stub — enables web-search-based hackathon discovery when
TAVILY_API_KEY is set, otherwise no-op."""

import logging
from typing import Dict, List

import config
from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_json

logger = logging.getLogger(__name__)


class TavilyDiscovery(BaseScraper):
    platform = "tavily"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("tavily disabled")
            return []
        if not config.TAVILY_API_KEY:
            logger.warning("tavily skipped — TAVILY_API_KEY not set")
            return []

        results: List[Dict] = []
        for query in cfg.get("queries", []):
            data = get_json(
                "https://api.tavily.com/search",
                params={
                    "api_key": config.TAVILY_API_KEY,
                    "query": query,
                    "max_results": 10,
                    "search_depth": "basic",
                },
            )
            if not data:
                continue
            for r in data.get("results") or []:
                url = r.get("url") or ""
                title = self._safe(r.get("title"))
                if not url or not title:
                    continue
                rec = self._base_record(url, title=title)
                rec["description"] = self._safe(r.get("content"))
                rec["tags_raw"] = query + " " + title
                results.append(rec)
        logger.info("tavily: %d results", len(results))
        return results
