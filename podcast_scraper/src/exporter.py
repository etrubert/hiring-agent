"""Export results as CSV, Excel (tab per role), and JSON."""

import json
import logging
from pathlib import Path
from typing import Dict, List
import pandas as pd

logger = logging.getLogger(__name__)

COLUMNS = [
    "guest_name",
    "role_detected",
    "confidence",
    "is_ai_guest",
    "podcast_source",
    "episode_title",
    "episode_url",
    "published_at",
    "linkedin",
    "twitter",
    "github",
    "website",
    "source_type",
    "description_snippet",
    "reasoning",
]


def _row(ep: Dict) -> Dict:
    desc = ep.get("description", "") or ""
    return {
        "guest_name": ep.get("guest_name") or "",
        "role_detected": ep.get("role_detected") or "",
        "confidence": ep.get("confidence"),
        "is_ai_guest": ep.get("is_ai_guest"),
        "podcast_source": ep.get("channel_title") or "",
        "episode_title": ep.get("title") or "",
        "episode_url": ep.get("url") or "",
        "published_at": ep.get("published_at") or "",
        "linkedin": ep.get("linkedin") or "",
        "twitter": ep.get("twitter") or "",
        "github": ep.get("github") or "",
        "website": ep.get("website") or "",
        "source_type": ep.get("source_type") or "",
        "description_snippet": desc[:300].replace("\n", " "),
        "reasoning": ep.get("reasoning") or "",
    }


def to_dataframe(episodes: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame([_row(ep) for ep in episodes], columns=COLUMNS)


def export_csv(episodes: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = to_dataframe(episodes)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("wrote %d rows to %s", len(df), path)


def export_json(episodes: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2, default=str)
    logger.info("wrote %d rows to %s", len(episodes), path)


def export_excel(episodes: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = to_dataframe(episodes)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All", index=False)
        for role, sub in df.groupby("role_detected"):
            sheet = (role or "Unknown")[:31] or "Unknown"
            sub.to_excel(writer, sheet_name=sheet, index=False)
    logger.info("wrote excel with per-role tabs to %s", path)


def save_intermediate(episodes: List[Dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, default=str)


def export_readable(episodes: List[Dict], path: Path) -> None:
    """Write a human-friendly text report: one episode per block, blank line between."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    for idx, ep in enumerate(episodes, 1):
        lines.append(f"=== Épisode {idx} / {len(episodes)} ===")
        lines.append(f"Invité         : {ep.get('guest_name') or '(inconnu)'}")
        lines.append(f"Rôle détecté   : {ep.get('role_detected') or '-'}   (confiance {ep.get('confidence')})")
        lines.append(f"Est AI ?       : {ep.get('is_ai_guest')}")
        lines.append(f"Podcast        : {ep.get('channel_title') or '-'}")
        lines.append(f"Titre          : {ep.get('title') or '-'}")
        lines.append(f"URL            : {ep.get('url') or '-'}")
        lines.append(f"Publié         : {ep.get('published_at') or '-'}")
        lines.append(f"LinkedIn       : {ep.get('linkedin') or '-'}")
        lines.append(f"Twitter/X      : {ep.get('twitter') or '-'}")
        lines.append(f"GitHub         : {ep.get('github') or '-'}")
        lines.append(f"Website        : {ep.get('website') or '-'}")
        lines.append(f"Source         : {ep.get('source_type') or '-'}")
        desc = (ep.get("description") or "")[:400].replace("\n", " ")
        lines.append(f"Description    : {desc}")
        reasoning = (ep.get("reasoning") or "").replace("\n", " ")
        lines.append(f"Pourquoi ce rôle: {reasoning}")
        lines.append("")  # blank separator line
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("wrote readable report to %s", path)
