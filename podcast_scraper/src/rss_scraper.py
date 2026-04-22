"""RSS feed scraper using feedparser."""

import logging
from typing import List, Dict
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _clean_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)


def fetch_feed(name: str, url: str, max_episodes: int = 50) -> List[Dict]:
    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        logger.warning("feed %s failed: %s", name, parsed.bozo_exception)
        return []

    episodes = []
    for entry in parsed.entries[:max_episodes]:
        title = entry.get("title", "")
        desc_raw = entry.get("summary", "") or entry.get("description", "")
        content_list = entry.get("content", [])
        if content_list and isinstance(content_list, list):
            desc_raw = content_list[0].get("value", desc_raw)
        description = _clean_html(desc_raw)
        link = entry.get("link", "")
        published = entry.get("published", "") or entry.get("updated", "")
        episodes.append({
            "video_id": entry.get("id", link),
            "url": link,
            "title": title,
            "description": description,
            "channel_title": name,
            "published_at": published,
            "source_type": "rss",
        })
    return episodes
