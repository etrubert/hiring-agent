"""Scrape a single Malt profile page into a structured dict.

Primary data source is the JSON-LD `ProfilePage` block that Malt embeds in
every profile page — it contains name, jobTitle, skills, address, price,
languages. Falls back to HTML scraping for fields not in JSON-LD (bio,
rating, availability, years).
"""

import html as html_lib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from src.scraper.malt_session import MaltSession
from src.utils.anti_detection import human_scroll, sleep_random
from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _text(el) -> str:
    return normalize(el.get_text(" ", strip=True)) if el else ""


def _load_jsonld_profile(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Return the ProfilePage JSON-LD dict or None."""
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(s.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "ProfilePage":
                    return item
        elif isinstance(data, dict) and data.get("@type") == "ProfilePage":
            return data
    return None


def _format_location(addr: Dict[str, Any]) -> str:
    parts = []
    for k in ("addressLocality", "postalCode", "addressRegion", "addressCountry"):
        v = addr.get(k)
        if v:
            parts.append(str(v))
    return ", ".join(parts)


def _years_experience(soup: BeautifulSoup, bio: str) -> Optional[int]:
    candidates = [bio, soup.get_text(" ", strip=True)]
    for txt in candidates:
        if not txt:
            continue
        t = txt.lower()
        m = re.search(r"(\d{1,2})\s*\+?\s*(?:ans|années|year|years|yrs?)\s*(?:d[e']|d['’]?\s*exp|of\s*exp)", t)
        if m:
            try:
                v = int(m.group(1))
                if 0 < v < 60:
                    return v
            except ValueError:
                continue
    return None


def _availability(soup: BeautifulSoup) -> str:
    txt = soup.get_text(" ", strip=True).lower()
    if "disponible" in txt:
        m = re.search(r"(disponible[^.]{0,80})", txt)
        if m:
            return normalize(m.group(1))
    return ""


def _rating_from_html(soup: BeautifulSoup) -> Dict[str, Any]:
    out: Dict[str, Any] = {"rating": None, "reviews_count": None}
    txt = soup.get_text(" ", strip=True)
    m = re.search(r"(\d[.,]\d)\s*(?:/\s*5)?\s*\((\d+)\s*(?:avis|reviews)\)", txt, re.I)
    if m:
        try:
            out["rating"] = float(m.group(1).replace(",", "."))
            out["reviews_count"] = int(m.group(2))
        except (ValueError, IndexError):
            pass
    return out


def _bio_from_html(soup: BeautifulSoup) -> str:
    for sel in [
        "[data-testid='profile-description']",
        "[class*='description']",
        "section[class*='about']",
        "section[class*='About']",
        "section:has(h2:-soup-contains('Description'))",
    ]:
        try:
            el = soup.select_one(sel)
        except NotImplementedError:
            continue
        if el:
            t = _text(el)
            if t and len(t) > 50:
                return t
    for h in soup.find_all(["h2", "h3"]):
        if "description" in h.get_text(strip=True).lower():
            nxt = h.find_next(["p", "div", "section"])
            if nxt:
                t = _text(nxt)
                if t and len(t) > 50:
                    return t
    return ""


def _map_language(code: str) -> str:
    m = {
        "fr": "Français",
        "en": "Anglais",
        "es": "Espagnol",
        "de": "Allemand",
        "it": "Italien",
        "pt": "Portugais",
        "ar": "Arabe",
        "zh": "Chinois",
        "ja": "Japonais",
        "ru": "Russe",
        "nl": "Néerlandais",
    }
    return m.get(code.lower(), code)


def parse_profile(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    ld = _load_jsonld_profile(soup) or {}
    person = ld.get("mainEntity") if isinstance(ld.get("mainEntity"), dict) else {}

    name = html_lib.unescape(person.get("name", "") or "")
    title = html_lib.unescape(person.get("jobTitle", "") or ld.get("name", "") or "")
    skills = [html_lib.unescape(s) for s in (person.get("skills") or []) if isinstance(s, str)]

    addr = person.get("address") or {}
    location = _format_location(addr) if isinstance(addr, dict) else ""

    offer = person.get("makesOffer") or {}
    price = offer.get("price") if isinstance(offer, dict) else None
    tjm_str = f"{int(price)} €/j" if isinstance(price, (int, float)) else ""

    langs_raw = person.get("knowsLanguage") or []
    languages = [_map_language(l) for l in langs_raw if isinstance(l, str)]

    bio = _bio_from_html(soup)
    r = _rating_from_html(soup)
    availability = _availability(soup)
    years = _years_experience(soup, bio)
    ext = _external_links(soup)

    return {
        "profile_url": url,
        "name": name,
        "title": title,
        "location": location,
        "postal_code": addr.get("postalCode", "") if isinstance(addr, dict) else "",
        "years_experience": years,
        "skills": skills,
        "tjm": tjm_str,
        "bio": bio,
        "availability": availability,
        "rating": r["rating"],
        "reviews_count": r["reviews_count"],
        "languages": languages,
        "github_url": ext["github"],
        "kaggle_url": ext["kaggle"],
        "stackoverflow_url": ext["stackoverflow"],
        "linkedin_url": ext["linkedin"],
        "twitter_url": ext["twitter"],
        "certifications": ext["certifications"],
        "other_links": ext["other"],
    }


_MALT_DOMAINS = (
    "malt.fr", "malt.com", "dam.malt.com", "maltcommunity", "malt-academy",
    "schema.org", "google.com/maps", "axept.io", "hubspotusercontent",
    "cloudflare.com", "developers.cloudflare.com",
)


def _external_links(soup: BeautifulSoup) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "github": "", "kaggle": "", "stackoverflow": "", "linkedin": "",
        "twitter": "", "certifications": [], "other": [],
    }
    seen: set = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        low = href.lower()
        if any(d in low for d in _MALT_DOMAINS):
            continue
        if "github.com/" in low and "/5285846" not in low:
            m = re.match(r"(https?://(?:www\.)?github\.com/[A-Za-z0-9_\-\.]+)", href)
            if m and not out["github"]:
                out["github"] = m.group(1)
            continue
        if "kaggle.com/" in low:
            if not out["kaggle"]:
                out["kaggle"] = href
            continue
        if "stackoverflow.com/users/" in low:
            if not out["stackoverflow"]:
                out["stackoverflow"] = href
            continue
        if "linkedin.com/in/" in low:
            if not out["linkedin"]:
                out["linkedin"] = href
            continue
        if re.search(r"(?:twitter|x)\.com/[A-Za-z0-9_]+$", href):
            if not out["twitter"]:
                out["twitter"] = href
            continue
        if any(d in low for d in ("credly.com", "credential.net", "coursera.org", "openclassrooms.com", "accredible.com", "credsverse.com", "codility.com", "francecompetences")):
            out["certifications"].append(href)
            continue
        out["other"].append(href)
    return out


async def scrape_profile(
    session: MaltSession,
    url: str,
    delay_min: float,
    delay_max: float,
    screenshots_dir: Optional[Path] = None,
    raw_html_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    logger.info("profile: %s", url)
    async with session.new_page() as page:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await sleep_random(delay_min, delay_max)
        await session.accept_cookies(page)
        await human_scroll(page, total_steps=10)
        await sleep_random(delay_min, delay_max)
        html = await page.content()
        if screenshots_dir:
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", url.split("/profile/")[-1])[:80]
            try:
                await page.screenshot(path=str(screenshots_dir / f"profile_{slug}.png"), full_page=False)
            except Exception as exc:
                logger.warning("screenshot failed: %s", exc)
    if raw_html_dir:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", url.split("/profile/")[-1])[:80]
        (raw_html_dir / f"{slug}.html").write_text(html, encoding="utf-8")
    data = parse_profile(html, url)
    data["_raw_html"] = html
    return data
