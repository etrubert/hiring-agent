"""Enrich Devpost hackathons with their submitted projects.

For each hackathon, fetch `{url}/project-gallery`, collect `/software/<slug>`
links, then fetch each project page to extract: title, participants (name +
Devpost profile), GitHub URL, other 'Try it out' links, tagline, built-with.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.utils.http_client import get_html
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)

_PROFILE_RE = re.compile(r"^https?://devpost\.com/[a-zA-Z0-9_-]+/?$")
_SOFTWARE_HREF_RE = re.compile(r"/software/[a-zA-Z0-9-]+$")

MAX_PROJECTS_PER_HACKATHON = 60
WORKER_COUNT = 6

_SOCIAL_PATTERNS = {
    "github": re.compile(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_.-]+/?$", re.IGNORECASE),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:in|pub)/[^\s'\"<>]+", re.IGNORECASE),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/?$", re.IGNORECASE),
}

_PROFILE_CACHE: Dict[str, Dict] = {}


def _gallery_url(hackathon_url: str) -> str:
    if not hackathon_url:
        return ""
    return hackathon_url.rstrip("/") + "/project-gallery"


def _fetch_profile_socials(profile_url: str) -> Dict[str, str]:
    """Return {linkedin, github, twitter, website} for a Devpost profile,
    with in-memory caching."""
    if not profile_url:
        return {}
    if profile_url in _PROFILE_CACHE:
        return _PROFILE_CACHE[profile_url]
    html = get_html(profile_url)
    if not html:
        _PROFILE_CACHE[profile_url] = {}
        return {}
    soup = BeautifulSoup(html, "lxml")
    user_urls: List[str] = []
    for ul in soup.select("ul.inline-list"):
        for a in ul.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and href not in user_urls:
                user_urls.append(href)

    socials: Dict[str, str] = {}
    website = ""
    for u in user_urls:
        low = u.lower()
        if "devpost.com" in low:
            continue
        if _SOCIAL_PATTERNS["github"].match(u) and "github" not in socials:
            socials["github"] = u
        elif _SOCIAL_PATTERNS["linkedin"].match(u) and "linkedin" not in socials:
            socials["linkedin"] = u
        elif _SOCIAL_PATTERNS["twitter"].match(u) and "twitter" not in socials:
            socials["twitter"] = u
        elif not website and not any(x in low for x in ("github.com", "linkedin.com", "twitter.com", "x.com")):
            website = u
    if website:
        socials["website"] = website
    _PROFILE_CACHE[profile_url] = socials
    return socials


def _list_project_urls(gallery_url: str) -> List[str]:
    html = get_html(gallery_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    seen: set = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/software/" not in href:
            continue
        full = href if href.startswith("http") else urljoin("https://devpost.com", href)
        if _SOFTWARE_HREF_RE.search(full) and full not in seen:
            seen.add(full)
            urls.append(full)
    return urls


def _parse_project(url: str, enrich_profiles: bool = False) -> Optional[Dict]:
    html = get_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("h1#app-title") or soup.select_one("h1")
    title = collapse(title_el.get_text(" ", strip=True)) if title_el else ""

    tagline_el = soup.select_one("p.large") or soup.select_one(".software-tagline")
    tagline = collapse(tagline_el.get_text(" ", strip=True)) if tagline_el else ""

    winner_badges = soup.select(".label.winner")
    is_winner = bool(winner_badges)
    winner_labels: List[str] = []
    for b in winner_badges:
        text = collapse(b.get_text(" ", strip=True))
        if text and text not in winner_labels:
            winner_labels.append(text)

    external_links: List[str] = []
    github_url = ""
    for a in soup.select("nav.app-links a[href], ul.app-links a[href]"):
        href = a["href"]
        if not href or href in external_links:
            continue
        external_links.append(href)
        if not github_url and "github.com" in href:
            github_url = href

    if not github_url:
        for a in soup.find_all("a", href=True):
            if "github.com" in a["href"] and "/devpost-" not in a["href"]:
                github_url = a["href"]
                break

    participants: List[Dict] = []
    seen_profiles: set = set()
    for a in soup.select(".user-profile-link, #app-team .user-profile-link"):
        href = a.get("href", "")
        if not _PROFILE_RE.match(href) or href in seen_profiles:
            continue
        seen_profiles.add(href)
        name = collapse(a.get_text(" ", strip=True))
        if not name:
            img = a.find("img")
            if img and img.get("alt"):
                name = img["alt"].strip()
        participants.append({"name": name, "profile_url": href})

    for i, p in enumerate(participants):
        if p["name"]:
            continue
        for a in soup.select(f".user-profile-link[href='{p['profile_url']}']"):
            txt = collapse(a.get_text(" ", strip=True))
            if txt:
                participants[i]["name"] = txt
                break

    built_with: List[str] = []
    for tag in soup.select("#built-with li, .built-with li, #built-with a"):
        t = collapse(tag.get_text(" ", strip=True))
        if t and t not in built_with:
            built_with.append(t)

    if enrich_profiles:
        for p in participants:
            socials = _fetch_profile_socials(p.get("profile_url", ""))
            p["github"] = socials.get("github", "")
            p["linkedin"] = socials.get("linkedin", "")
            p["twitter"] = socials.get("twitter", "")
            p["website"] = socials.get("website", "")

    return {
        "project_url": url,
        "project_title": title,
        "tagline": tagline,
        "github_url": github_url,
        "external_links": external_links,
        "participants": participants,
        "built_with": built_with,
        "is_winner": is_winner,
        "winner_labels": winner_labels,
    }


def fetch_projects_for_hackathon(
    hackathon: Dict,
    max_projects: int = MAX_PROJECTS_PER_HACKATHON,
    enrich_profiles: bool = False,
) -> List[Dict]:
    gallery = _gallery_url(hackathon.get("url") or "")
    if not gallery:
        return []
    all_urls = _list_project_urls(gallery)[:max_projects]
    if not all_urls:
        logger.info("devpost_projects: %s -> 0 projects (gallery empty)", hackathon.get("title"))
        return []

    projects: List[Dict] = []
    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as pool:
        futures = {pool.submit(_parse_project, u, enrich_profiles): u for u in all_urls}
        for fut in as_completed(futures):
            try:
                data = fut.result()
            except Exception as exc:
                logger.warning("devpost_projects: failed %s: %s", futures[fut], exc)
                continue
            if data:
                data["hackathon_id"] = hackathon.get("id") or ""
                data["hackathon_title"] = hackathon.get("title") or ""
                data["hackathon_url"] = hackathon.get("url") or ""
                projects.append(data)

    winners = sum(1 for p in projects if p.get("is_winner"))
    logger.info(
        "devpost_projects: %s -> %d projects (%d winners)",
        hackathon.get("title"),
        len(projects),
        winners,
    )
    return projects


def enrich_with_projects(
    hackathons: List[Dict],
    max_projects: int = MAX_PROJECTS_PER_HACKATHON,
    enrich_profiles: bool = False,
) -> List[Dict]:
    all_projects: List[Dict] = []
    for h in hackathons:
        if h.get("source_platform") != "devpost":
            continue
        all_projects.extend(
            fetch_projects_for_hackathon(h, max_projects=max_projects, enrich_profiles=enrich_profiles)
        )
    total_winners = sum(1 for p in all_projects if p.get("is_winner"))
    logger.info(
        "devpost_projects: TOTAL %d projects (%d winners) across %d hackathons",
        len(all_projects),
        total_winners,
        len(hackathons),
    )
    return all_projects
