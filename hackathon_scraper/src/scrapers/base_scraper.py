"""Base class for all platform scrapers.

A scraper is responsible for producing a list of "hackathon" dicts with the
following canonical keys. Any missing key is filled with an empty/default
value by `_base_record`.

    id                str  — stable identifier (platform + slug or url-hash)
    title             str
    url               str
    source_platform   str  — e.g. "devpost", "mlh"
    description       str
    location          str
    is_online         bool
    start_date        str  — ISO-ish ("YYYY-MM-DD" preferred, raw if unknown)
    end_date          str
    prize_pool        str
    tags_raw          str  — free-form tag/topic text for theme detection
    people            list[dict]  — {name, title, context_role, linkedin, twitter, company}
    companies         list[dict]  — {name, role, website}
"""

import hashlib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseScraper:
    platform: str = "base"

    def fetch(self, config_block: Dict) -> List[Dict]:
        raise NotImplementedError

    @classmethod
    def _base_record(cls, url: str, title: str = "") -> Dict:
        hid = cls._make_id(url or title)
        return {
            "id": f"{cls.platform}:{hid}",
            "title": title,
            "url": url,
            "source_platform": cls.platform,
            "sources": [cls.platform],
            "description": "",
            "location": "",
            "is_online": None,
            "start_date": "",
            "end_date": "",
            "prize_pool": "",
            "tags_raw": "",
            "people": [],
            "companies": [],
        }

    @staticmethod
    def _make_id(seed: str) -> str:
        if not seed:
            seed = "unknown"
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _safe(value: Optional[str]) -> str:
        return (value or "").strip()
