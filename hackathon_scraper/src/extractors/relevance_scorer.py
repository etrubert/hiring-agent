"""Compute a 0–100 relevance score for a hackathon and apply the keep/drop rule.

Keep rule: (theme_is_ai AND has_target_role_in_people) OR has_specific_tool.

The score is a transparent sum of weighted signals, documented via
`match_reasons` so downstream users can audit why a hackathon was kept.
"""

import logging
from typing import Dict, List, Tuple

from src.extractors.role_matcher import list_target_roles, match_role
from src.extractors.skill_matcher import find_specific_tools
from src.extractors.theme_detector import ai_keyword_hits, non_ai_hits

logger = logging.getLogger(__name__)

W_THEME_AI = 25
W_AI_KEYWORD_EACH = 4
W_AI_KEYWORD_MAX = 20
W_TARGET_ROLE_FIRST = 30
W_TARGET_ROLE_EACH = 10
W_TOOL_FIRST = 25
W_TOOL_EACH = 5
W_PENALTY_NON_AI = -15


def score_hackathon(hackathon: Dict) -> Tuple[int, List[str], bool]:
    """Return (score, reasons, keep)."""
    text = " ".join(
        [
            hackathon.get("title") or "",
            hackathon.get("description") or "",
            hackathon.get("tags_raw") or "",
        ]
    )
    people: List[Dict] = hackathon.get("people") or []
    reasons: List[str] = []
    score = 0

    ai_hits = ai_keyword_hits(text)
    tools = find_specific_tools(text)
    target_roles = list_target_roles(people)
    non_ai = non_ai_hits(text)

    theme_ai = bool(ai_hits)
    if theme_ai:
        score += W_THEME_AI
        reasons.append(f"theme=AI (keywords: {', '.join(ai_hits[:5])})")
        score += min(len(ai_hits) * W_AI_KEYWORD_EACH, W_AI_KEYWORD_MAX)

    if target_roles:
        score += W_TARGET_ROLE_FIRST + max(0, len(target_roles) - 1) * W_TARGET_ROLE_EACH
        reasons.append(f"target roles found: {', '.join(target_roles)}")

    if tools:
        score += W_TOOL_FIRST + max(0, len(tools) - 1) * W_TOOL_EACH
        reasons.append(f"specific tools: {', '.join(tools[:6])}")

    if non_ai and not theme_ai and not tools:
        score += W_PENALTY_NON_AI
        reasons.append(f"penalty: non-AI signals {non_ai}")

    score = max(0, min(100, score))

    has_role = bool(target_roles)
    has_tool = bool(tools)
    keep = (theme_ai and has_role) or has_tool

    if not keep and theme_ai and not has_role and not has_tool:
        reasons.append("dropped: AI theme but no target role and no specific tool")

    return score, reasons, keep


def annotate(hackathon: Dict) -> Dict:
    score, reasons, keep = score_hackathon(hackathon)
    hackathon["relevance_score"] = score
    hackathon["match_reasons"] = reasons
    hackathon["keep"] = keep
    hackathon["target_roles_found"] = list_target_roles(hackathon.get("people") or [])
    text = " ".join([hackathon.get("title") or "", hackathon.get("description") or ""])
    hackathon["tools_found"] = find_specific_tools(text)
    hackathon["ai_keywords_found"] = ai_keyword_hits(text)
    return hackathon
