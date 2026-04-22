"""HackerNews scraper — uses the Algolia search API (no key required)."""

import logging
from typing import Dict, List

from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_json

logger = logging.getLogger(__name__)


class HackerNewsScraper(BaseScraper):
    platform = "hackernews"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("hackernews disabled")
            return []

        base = cfg.get("algolia_url") or "https://hn.algolia.com/api/v1/search_by_date"
        results: List[Dict] = []
        seen: set = set()

        for query in cfg.get("queries", []):
            params = {"query": query, "tags": "story", "hitsPerPage": 50}
            data = get_json(base, params=params)
            if not data:
                continue
            for hit in data.get("hits", []):
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                if url in seen:
                    continue
                seen.add(url)
                title = self._safe(hit.get("title") or "")
                if not title:
                    continue
                rec = self._base_record(url, title=title)
                rec["description"] = self._safe(hit.get("story_text") or "")
                rec["tags_raw"] = title + " " + " ".join(hit.get("_tags") or [])
                rec["start_date"] = self._safe(hit.get("created_at") or "")[:10]
                results.append(rec)

        logger.info("hackernews: %d stories", len(results))
        return results
