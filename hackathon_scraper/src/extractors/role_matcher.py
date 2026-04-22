"""Detect whether a job title / person matches one of our 4 target roles."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

import config
from src.utils.text_cleaner import normalize

logger = logging.getLogger(__name__)


def _load_roles() -> List[Dict]:
    path: Path = config.SOURCES_DIR / "target_roles.yaml"
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("roles", [])


_ROLES = _load_roles()


def match_role(title: str) -> Optional[str]:
    """Return the canonical target-role name if `title` matches any pattern, else None."""
    if not title:
        return None
    n = normalize(title)
    for role in _ROLES:
        for pat in role.get("patterns", []):
            if pat.lower() in n:
                return role["name"]
    return None


def has_target_role(people: List[Dict]) -> bool:
    return any(match_role(p.get("title", "")) for p in people or [])


def list_target_roles(people: List[Dict]) -> List[str]:
    roles: List[str] = []
    for p in people or []:
        r = match_role(p.get("title", ""))
        if r and r not in roles:
            roles.append(r)
    return roles
