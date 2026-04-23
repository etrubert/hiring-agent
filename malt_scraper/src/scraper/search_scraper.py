"""Extract profile URLs from Malt search result pages."""

import logging
import urllib.parse
from typing import List

from bs4 import BeautifulSoup

from src.scraper.malt_session import MaltSession
from src.utils.anti_detection import human_scroll, sleep_random

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.malt.fr/s"


def _build_url(query: str, location: str) -> str:
    params = {"q": query, "location": location}
    return f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"


def _extract_profile_urls(html: str) -> List[str]:
    """Parse search HTML and return absolute profile URLs.

    Malt profile URLs look like https://www.malt.fr/profile/<slug>. We match
    any <a href> whose path starts with /profile/.
    """
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    seen: set = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/profile/" not in href:
            continue
        if href.startswith("/"):
            href = "https://www.malt.fr" + href
        base = href.split("?")[0].split("#")[0]
        if base in seen or "/profile/" not in base:
            continue
        seen.add(base)
        urls.append(base)
    return urls


async def scrape_search(
    session: MaltSession,
    query: str,
    location: str,
    max_profiles: int,
    delay_min: float,
    delay_max: float,
) -> List[str]:
    url = _build_url(query, location)
    logger.info("search: %s", url)
    async with session.new_page() as page:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await sleep_random(delay_min, delay_max)
        await session.accept_cookies(page)
        await human_scroll(page, total_steps=8)
        await sleep_random(delay_min, delay_max)
        html = await page.content()
    urls = _extract_profile_urls(html)
    logger.info("search %r @ %s -> %d urls", query, location, len(urls))
    return urls[:max_profiles]
