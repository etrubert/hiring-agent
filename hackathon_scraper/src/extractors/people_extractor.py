"""Heuristic extraction of 'people' (judges / mentors / speakers / organisers)
from an already-fetched hackathon HTML page.

Public listings rarely expose judges in structured form — this module tries a
few best-effort strategies and returns an empty list when nothing is found.
"""

import logging
import re
from typing import Dict, List

from bs4 import BeautifulSoup

from src.extractors.link_extractor import classify_social, extract_urls
from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)

_ROLE_LABELS = [
    "judge",
    "judges",
    "mentor",
    "mentors",
    "speaker",
    "speakers",
    "organizer",
    "organizers",
    "organiser",
    "organisers",
    "host",
    "hosts",
    "panelist",
    "panelists",
]

_NAME_TITLE_RE = re.compile(
    r"([A-Z][a-zA-ZÀ-ÿ'’\-]+(?:\s+[A-Z][a-zA-ZÀ-ÿ'’\-]+){0,3})"
    r"\s*[—–\-,|·•]\s*"
    r"([A-Za-z][A-Za-z0-9 ,/&\-]+)"
)


def _role_sections(soup: BeautifulSoup) -> List[str]:
    sections: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "section", "div"]):
        heading = collapse(tag.get_text(" ", strip=True)).lower()
        if any(label in heading for label in _ROLE_LABELS) and len(heading) < 80:
            block = []
            for sib in tag.next_siblings:
                text = collapse(getattr(sib, "get_text", lambda *a, **kw: "")(" ", strip=True))
                if not text:
                    continue
                block.append(text)
                if len(" ".join(block)) > 2000:
                    break
            sections.append(" ".join(block))
    return sections


def _parse_people_from_text(text: str, context_role: str = "") -> List[Dict]:
    people: List[Dict] = []
    for m in _NAME_TITLE_RE.finditer(text):
        name = m.group(1).strip()
        title = m.group(2).strip()
        if len(name.split()) < 2:
            continue
        if len(title) < 3 or len(title) > 120:
            continue
        people.append(
            {
                "name": name,
                "title": title,
                "context_role": context_role,
                "linkedin": "",
                "twitter": "",
                "company": "",
            }
        )
    return people


def extract_people(html: str) -> List[Dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")

    people: List[Dict] = []
    for section in _role_sections(soup):
        people.extend(_parse_people_from_text(section))

    urls = extract_urls(html)
    linkedin_urls = [u for u in urls if classify_social(u) == "linkedin" and "/in/" in u]
    for p, url in zip(people, linkedin_urls):
        p["linkedin"] = url

    seen = set()
    unique: List[Dict] = []
    for p in people:
        key = (p["name"].lower(), p["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique
