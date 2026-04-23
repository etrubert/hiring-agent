"""Write a human-friendly .txt report: one block per hackathon, listing its
winners (or all projects if no winners were detected) with participant
GitHub/LinkedIn/Twitter when available."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

logger = logging.getLogger(__name__)


def _project_block(p: Dict, idx: int) -> List[str]:
    lines = []
    winner_badge = " [WINNER]" if p.get("is_winner") else ""
    labels = p.get("winner_labels") or []
    label_str = f" ({', '.join(labels)})" if labels else ""
    lines.append(f"  {idx}. {p.get('project_title') or '(untitled)'}{winner_badge}{label_str}")
    if p.get("tagline"):
        lines.append(f"     Tagline     : {p['tagline']}")
    lines.append(f"     Project URL : {p.get('project_url') or '-'}")
    if p.get("github_url"):
        lines.append(f"     GitHub      : {p['github_url']}")
    ext = [x for x in (p.get("external_links") or []) if "github.com" not in x]
    if ext:
        lines.append(f"     Other links : {', '.join(ext)}")
    built = p.get("built_with") or []
    if built:
        lines.append(f"     Built with  : {', '.join(built[:15])}")
    participants = p.get("participants") or []
    if participants:
        lines.append(f"     Participants:")
        for part in participants:
            name = part.get("name") or "(anonymous)"
            bits = []
            if part.get("github"):
                bits.append(f"GitHub: {part['github']}")
            if part.get("linkedin"):
                bits.append(f"LinkedIn: {part['linkedin']}")
            if part.get("twitter"):
                bits.append(f"Twitter: {part['twitter']}")
            if part.get("website"):
                bits.append(f"Web: {part['website']}")
            if part.get("profile_url"):
                bits.append(f"Devpost: {part['profile_url']}")
            trailer = f"   —   {' | '.join(bits)}" if bits else ""
            lines.append(f"        - {name}{trailer}")
    return lines


def write_readable_report(
    hackathons: List[Dict],
    projects: Iterable[Dict],
    out_path: Path,
    winners_only: bool = False,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    by_hackathon: Dict[str, List[Dict]] = defaultdict(list)
    for p in projects:
        by_hackathon[p.get("hackathon_id") or ""].append(p)

    hackathons_sorted = sorted(
        hackathons,
        key=lambda h: (h.get("relevance_score") or 0, len(by_hackathon.get(h.get("id") or "", []))),
        reverse=True,
    )

    lines: List[str] = []
    total = len(hackathons_sorted)
    for idx, h in enumerate(hackathons_sorted, 1):
        hid = h.get("id") or ""
        ps = by_hackathon.get(hid, [])
        winners = [p for p in ps if p.get("is_winner")]
        shown = winners if winners else (ps if not winners_only else [])
        lines.append(f"=== [{idx}/{total}] {h.get('title') or '(no title)'} ===")
        lines.append(f"  Platform     : {h.get('source_platform') or '-'}")
        lines.append(f"  Hackathon URL: {h.get('url') or '-'}")
        if h.get("city_fr"):
            lines.append(f"  City (FR)    : {h['city_fr']}")
        if h.get("start_date") or h.get("end_date"):
            lines.append(f"  Dates        : {h.get('start_date') or '?'}  ->  {h.get('end_date') or '?'}")
        if h.get("location"):
            lines.append(f"  Location     : {h['location']}  (online={h.get('is_online')})")
        if h.get("prize_pool"):
            lines.append(f"  Prize pool   : {h['prize_pool']}")
        lines.append(f"  Score        : {h.get('relevance_score')}")
        if h.get("tools_found"):
            lines.append(f"  Tools        : {', '.join(h['tools_found'])}")
        if h.get("ai_keywords_found"):
            lines.append(f"  AI keywords  : {', '.join(h['ai_keywords_found'])}")
        if h.get("target_roles_found"):
            lines.append(f"  Target roles : {', '.join(h['target_roles_found'])}")
        lines.append(
            f"  Projects     : {len(ps)} total, {len(winners)} winners"
        )

        if shown:
            header = "WINNERS:" if winners else "PROJECTS:"
            lines.append(f"  --- {header} ---")
            for j, p in enumerate(shown, 1):
                lines.extend(_project_block(p, j))
        else:
            lines.append("  (no projects scraped for this hackathon)")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("wrote readable report to %s", out_path)
    return out_path
