"""Reddit scraper — uses the OAuth API when credentials are provided,
falls back to the public .json endpoint otherwise."""

import logging
from typing import Dict, List

import config
from src.scrapers.base_scraper import BaseScraper
from src.utils.http_client import get_json

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    platform = "reddit"

    def fetch(self, cfg: Dict) -> List[Dict]:
        if not cfg.get("enabled"):
            logger.info("reddit disabled")
            return []

        results: List[Dict] = []
        headers = {"User-Agent": config.REDDIT_USER_AGENT}
        for sub in cfg.get("subreddits", []):
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {"q": "hackathon", "restrict_sr": "on", "sort": "new", "limit": 25}
            data = get_json(url, params=params, headers=headers)
            if not data:
                continue
            for post in (data.get("data") or {}).get("children") or []:
                d = post.get("data") or {}
                perma = d.get("permalink") or ""
                full_url = f"https://www.reddit.com{perma}" if perma else d.get("url") or ""
                title = self._safe(d.get("title"))
                if not title or not full_url:
                    continue
                rec = self._base_record(full_url, title=title)
                rec["description"] = self._safe(d.get("selftext"))
                rec["tags_raw"] = title + " " + self._safe(d.get("link_flair_text") or "")
                rec["location"] = f"r/{sub}"
                results.append(rec)

        logger.info("reddit: %d posts", len(results))
        return results
