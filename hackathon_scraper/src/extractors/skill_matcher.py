"""Detect mentions of specific AI tools/frameworks/SDKs in hackathon text."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

import config
from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _load_tools() -> List[Dict]:
    path: Path = config.SOURCES_DIR / "skills.yaml"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("tools", [])


_TOOLS = _load_tools()


def _compile_patterns(tool: Dict) -> List[Tuple[str, re.Pattern]]:
    aliases = [tool["name"].lower(), *(a.lower() for a in tool.get("aliases", []))]
    patterns = []
    for a in set(aliases):
        esc = re.escape(a)
        patterns.append((tool["name"], re.compile(rf"(?<![a-z0-9]){esc}(?![a-z0-9])", re.IGNORECASE)))
    return patterns


_COMPILED = [p for tool in _TOOLS for p in _compile_patterns(tool)]


def find_specific_tools(text: str) -> List[str]:
    """Return the de-duplicated list of tool canonical names mentioned in `text`."""
    if not text:
        return []
    haystack = normalize(text)
    found: List[str] = []
    for name, pat in _COMPILED:
        if pat.search(haystack) and name not in found:
            found.append(name)
    return found


def has_specific_tool(text: str) -> bool:
    return bool(find_specific_tools(text))
