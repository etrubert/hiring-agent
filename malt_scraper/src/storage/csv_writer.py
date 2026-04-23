"""Write the three required CSVs: freelances, missions, skills."""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _profile_id(p: Dict[str, Any]) -> str:
    url = (p.get("profile_url") or "").rstrip("/")
    return url.split("/profile/")[-1].split("?")[0] if "/profile/" in url else url


def write_freelances(profiles: List[Dict[str, Any]], out: Path) -> None:
    rows: List[Dict[str, Any]] = []
    for p in profiles:
        matched_skills = p.get("matched_skills") or []
        skill_names = [s[0] if isinstance(s, (list, tuple)) else s for s in matched_skills]
        competitors_detected = p.get("competitors_detected") or []
        comp_keys = [c[0] if isinstance(c, (list, tuple)) else c for c in competitors_detected]
        rows.append({
            "profile_id": _profile_id(p),
            "name": p.get("name") or "",
            "title": p.get("title") or "",
            "location": p.get("location") or "",
            "city_category": p.get("city_category") or "other",
            "years_experience": p.get("years_experience"),
            "tjm_eur": p.get("tjm_eur"),
            "availability": p.get("availability") or "",
            "rating": p.get("rating"),
            "reviews_count": p.get("reviews_count"),
            "matched_role": p.get("matched_role") or "",
            "matched_skills_count": len(skill_names),
            "matched_skills_list": "; ".join(skill_names),
            "worked_for_competitor": bool(comp_keys),
            "competitors_detected": "; ".join(comp_keys),
            "is_match": bool(p.get("is_match")),
            "bio": (p.get("bio") or "")[:2000],
            "profile_url": p.get("profile_url") or "",
            "scraped_at": p.get("scraped_at") or "",
        })
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")


def write_missions(profiles: List[Dict[str, Any]], out: Path) -> None:
    rows: List[Dict[str, Any]] = []
    for p in profiles:
        pid = _profile_id(p)
        comp_hits = {k: titles for k, titles in (p.get("competitors_detected") or [])}
        for m in p.get("missions") or []:
            competitor_name = ""
            is_competitor = False
            for key, titles in comp_hits.items():
                if (m.get("mission_title") or "") in titles or any(
                    k in (m.get("client_name", "") + " " + (m.get("mission_description") or "")).lower()
                    for k in [key]
                ):
                    competitor_name = key
                    is_competitor = True
                    break
            rows.append({
                "profile_id": pid,
                "mission_title": m.get("mission_title") or "",
                "mission_description": (m.get("mission_description") or "")[:2000],
                "client_name": m.get("client_name") or "",
                "duration": m.get("duration") or "",
                "technologies": "; ".join(m.get("technologies") or []),
                "is_competitor_mission": is_competitor,
                "competitor_name": competitor_name,
                "extracted_at": p.get("scraped_at") or "",
            })
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")


def write_skills(profiles: List[Dict[str, Any]], out: Path, key_skill_set: set) -> None:
    rows: List[Dict[str, Any]] = []
    for p in profiles:
        pid = _profile_id(p)
        matched = {name.lower(): cat for (name, cat) in (p.get("matched_skills") or [])}
        for s in p.get("skills") or []:
            cat = matched.get(s.lower(), "")
            rows.append({
                "profile_id": pid,
                "skill_name": s,
                "skill_category": cat,
                "is_key_skill": s.lower() in key_skill_set or cat != "",
            })
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8")
