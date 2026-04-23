"""Extract client reviews from a profile HTML blob (max 5 by default)."""

import logging
import re
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def extract_reviews(html: str, max_reviews: int = 5) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    reviews: List[Dict[str, Any]] = []
    blocks = soup.select(
        "[data-testid*='review'], [class*='review'], [class*='Review'], "
        "[data-testid*='testimonial'], [class*='testimonial']"
    )
    seen: set = set()
    for block in blocks:
        text = normalize(block.get_text(" ", strip=True))
        if not text or len(text) < 30:
            continue
        key = hash(text[:200])
        if key in seen:
            continue
        seen.add(key)
        rating = None
        m = re.search(r"(\d[.,]\d)\s*/\s*5", text)
        if m:
            try:
                rating = float(m.group(1).replace(",", "."))
            except ValueError:
                rating = None
        reviewer = ""
        for tag in block.find_all(["span", "div", "h4", "h5"]):
            t = normalize(tag.get_text(" ", strip=True))
            if 3 <= len(t) <= 60 and re.match(r"^[A-ZÀ-ÖØ-Þ][\w\s.'\-]+$", t):
                reviewer = t
                break
        date_m = re.search(r"\b\d{1,2}\s+(?:janv|févr|mars|avril|mai|juin|juil|aoû|sept|oct|nov|déc)[^\s]*\s+\d{4}\b", text, flags=re.I)
        reviews.append({
            "review_rating": rating,
            "review_text": text[:1500],
            "reviewer_name": reviewer,
            "review_date": date_m.group(0) if date_m else "",
        })
        if len(reviews) >= max_reviews:
            break
    return reviews
