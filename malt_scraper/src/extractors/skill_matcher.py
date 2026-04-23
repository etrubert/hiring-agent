"""Count how many key skills (from skills.yaml) appear in a freelance's
declared skills and bio."""

import re
from typing import Dict, List, Tuple

from src.utils.text_cleaner import lower_no_accent


def _word_match(needle: str, haystack: str) -> bool:
    """Word-boundary regex match — avoids 'R' matching inside 'RAG'."""
    if not needle or not haystack:
        return False
    pat = r"(?<![A-Za-z0-9])" + re.escape(needle) + r"(?![A-Za-z0-9])"
    return re.search(pat, haystack) is not None


def match_skills(
    declared_skills: List[str],
    bio: str,
    skills_by_category: Dict[str, List[str]],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Return (matched_skills, unmatched_declared).

    matched_skills: list of (skill_name, category).
    unmatched_declared: declared skills that did not map to any key skill.
    """
    haystack_tokens = {lower_no_accent(s) for s in declared_skills if s}
    haystack_bio = lower_no_accent(bio)

    matched: List[Tuple[str, str]] = []
    matched_norm: set = set()
    for category, skills in skills_by_category.items():
        for skill in skills:
            norm = lower_no_accent(skill)
            if not norm or norm in matched_norm:
                continue
            if norm in haystack_tokens or _word_match(norm, haystack_bio):
                matched.append((skill, category))
                matched_norm.add(norm)

    unmatched = [s for s in declared_skills if lower_no_accent(s) not in matched_norm]
    return matched, unmatched
