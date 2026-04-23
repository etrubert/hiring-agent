"""Extract past missions / portfolio entries from a profile HTML blob."""

import logging
import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _find_mission_blocks(soup: BeautifulSoup) -> List[Any]:
    blocks: List[Any] = []
    selectors = [
        "[data-testid*='mission'], [class*='mission'], [class*='Mission']",
        "[data-testid*='experience'], [class*='experience'], [class*='Experience']",
        "[data-testid*='portfolio'], [class*='portfolio'], [class*='Portfolio']",
    ]
    seen: set = set()
    for sel in selectors:
        for el in soup.select(sel):
            key = (el.name or "") + (el.get("class", [""])[0] if el.get("class") else "")
            t = el.get_text(" ", strip=True)
            if not t or len(t) < 20:
                continue
            h = hash(t[:200])
            if h in seen:
                continue
            seen.add(h)
            blocks.append(el)
    return blocks


def _parse_duration(txt: str) -> str:
    m = re.search(
        r"(\d+\s*(?:mois|ans|months|years))"
        r"|((?:janv|févr|mars|avril|mai|juin|juil|aoû|sept|oct|nov|déc)[^\s]*\s+\d{4}\s*[-–]\s*(?:janv|févr|mars|avril|mai|juin|juil|aoû|sept|oct|nov|déc)[^\s]*\s+\d{4})",
        txt,
        flags=re.I,
    )
    return m.group(0) if m else ""


def extract_missions(html: str, max_missions: int = 20) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Dict[str, Any]] = []
    for block in _find_mission_blocks(soup)[:max_missions]:
        title_el = block.find(["h3", "h4", "h5"])
        title = normalize(title_el.get_text(" ", strip=True)) if title_el else ""
        body = normalize(block.get_text(" ", strip=True))
        client = ""
        for tag in block.find_all(["span", "div", "p"]):
            t = normalize(tag.get_text(" ", strip=True))
            if not t:
                continue
            if re.match(r"^(client|chez|pour|@)\s*:?\s*", t, flags=re.I):
                client = re.sub(r"^(client|chez|pour|@)\s*:?\s*", "", t, flags=re.I)
                break
        techs: List[str] = []
        for tag in block.select("[class*='tech'], [class*='tag'], [data-testid*='tech']"):
            t = normalize(tag.get_text(" ", strip=True))
            if t and len(t) <= 40 and t not in techs:
                techs.append(t)
        out.append({
            "mission_title": title,
            "mission_description": body[:1500],
            "client_name": client,
            "duration": _parse_duration(body),
            "technologies": techs,
        })
    return out
