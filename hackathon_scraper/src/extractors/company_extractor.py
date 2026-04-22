"""Extract sponsor / organiser company names from hackathon pages."""

import logging
import re
from typing import Dict, List

from bs4 import BeautifulSoup

from src.utils.text_cleaner import collapse

logger = logging.getLogger(__name__)

_SPONSOR_LABELS = [
    "sponsor",
    "sponsors",
    "partner",
    "partners",
    "organizer",
    "organizers",
    "organiser",
    "organisers",
    "presented by",
    "hosted by",
]

_COMPANY_NAME_RE = re.compile(r"[A-Z][A-Za-z0-9&.\-' ]{1,40}")


def _sponsor_blocks(soup: BeautifulSoup) -> List[str]:
    blocks: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "section", "div"]):
        heading = collapse(tag.get_text(" ", strip=True)).lower()
        if any(label in heading for label in _SPONSOR_LABELS) and len(heading) < 80:
            chunk: List[str] = []
            for sib in tag.next_siblings:
                t = collapse(getattr(sib, "get_text", lambda *a, **kw: "")(" ", strip=True))
                if not t:
                    continue
                chunk.append(t)
                if len(" ".join(chunk)) > 1500:
                    break
            blocks.append(" ".join(chunk))
    return blocks


def extract_companies(html: str) -> List[Dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    companies: List[Dict] = []
    seen = set()

    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if not alt or len(alt) > 60:
            continue
        lowered = alt.lower()
        if any(x in lowered for x in ["logo", "sponsor", "partner"]):
            clean = re.sub(r"\b(logo|sponsor|partner)\b", "", alt, flags=re.IGNORECASE).strip(" -:—")
            if clean and clean.lower() not in seen and len(clean) > 1:
                seen.add(clean.lower())
                companies.append({"name": clean, "role": "sponsor", "website": img.get("src") or ""})

    for block in _sponsor_blocks(soup):
        for m in _COMPANY_NAME_RE.finditer(block):
            name = m.group(0).strip()
            if len(name) < 2 or name.lower() in seen:
                continue
            if name.lower() in {"the", "and", "our", "with", "by", "for"}:
                continue
            seen.add(name.lower())
            companies.append({"name": name, "role": "sponsor", "website": ""})

    return companies[:50]
