"""Match a freelance's title/bio against the 4 target Mirakl roles."""

from typing import Dict, List, Optional, Tuple

from src.utils.text_cleaner import lower_no_accent


def _all_synonyms(roles: Dict[str, Dict[str, List[str]]]) -> Dict[str, List[str]]:
    """Flatten {role_key: [synonym, ...]} normalized."""
    out: Dict[str, List[str]] = {}
    for role_key, langs in roles.items():
        syns: List[str] = []
        for lang_list in langs.values():
            syns.extend(lang_list)
        out[role_key] = [lower_no_accent(s) for s in syns]
    return out


def match_role(title: str, bio: str, roles: Dict[str, Dict[str, List[str]]]) -> Optional[str]:
    """Return the first role_key whose synonym appears in title or bio."""
    haystack = lower_no_accent(f"{title} {bio}")
    if not haystack.strip():
        return None
    for role_key, syns in _all_synonyms(roles).items():
        for s in syns:
            if s and s in haystack:
                return role_key
    return None
