"""Write the main structured JSON output: data/final/malt-1.json."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def _profile_id(url: str) -> str:
    url = (url or "").rstrip("/")
    return url.split("/profile/")[-1].split("?")[0] if "/profile/" in url else url


def _profile_record(p: Dict[str, Any]) -> Dict[str, Any]:
    matched_skills = p.get("matched_skills") or []
    skill_list = [
        {"name": s[0], "category": s[1]} if isinstance(s, (list, tuple)) else {"name": s, "category": ""}
        for s in matched_skills
    ]
    competitors = p.get("competitors_detected") or []
    comp_list = [
        {"competitor": c[0], "matched_in": c[1]} if isinstance(c, (list, tuple)) else {"competitor": c, "matched_in": []}
        for c in competitors
    ]
    return {
        "profile_id": _profile_id(p.get("profile_url") or ""),
        "profile_url": p.get("profile_url") or "",
        "name": p.get("name") or "",
        "title": p.get("title") or "",
        "location": p.get("location") or "",
        "city_category": p.get("city_category") or "other",
        "years_experience": p.get("years_experience"),
        "tjm_eur": p.get("tjm_eur"),
        "tjm_raw": p.get("tjm") or "",
        "availability": p.get("availability") or "",
        "rating": p.get("rating"),
        "reviews_count": p.get("reviews_count"),
        "languages": p.get("languages") or [],
        "declared_skills": p.get("skills") or [],
        "matched_role": p.get("matched_role") or None,
        "matched_skills": skill_list,
        "matched_skills_count": len(skill_list),
        "worked_for_competitor": bool(competitors),
        "competitors_detected": comp_list,
        "is_match": bool(p.get("is_match")),
        "bio": p.get("bio") or "",
        "missions": p.get("missions") or [],
        "reviews": p.get("reviews") or [],
        "github_url": p.get("github_url") or "",
        "kaggle_url": p.get("kaggle_url") or "",
        "stackoverflow_url": p.get("stackoverflow_url") or "",
        "linkedin_url": p.get("linkedin_url") or "",
        "twitter_url": p.get("twitter_url") or "",
        "certifications": p.get("certifications") or [],
        "other_links": p.get("other_links") or [],
        "scraped_at": p.get("scraped_at") or "",
    }


def write_json(profiles: List[Dict[str, Any]], out: Path) -> Dict[str, Any]:
    records = [_profile_record(p) for p in profiles]

    skill_counter: Counter = Counter()
    comp_counter: Counter = Counter()
    for r in records:
        for s in r.get("matched_skills") or []:
            skill_counter[s["name"]] += 1
        for c in r.get("competitors_detected") or []:
            comp_counter[c["competitor"]] += 1

    payload = {
        "generated_at": records[0]["scraped_at"] if records else "",
        "total_profiles": len(records),
        "is_match_count": sum(1 for r in records if r["is_match"]),
        "worked_for_competitor_count": sum(1 for r in records if r["worked_for_competitor"]),
        "top_skills": [{"name": n, "count": c} for n, c in skill_counter.most_common(10)],
        "top_competitors": [{"name": n, "count": c} for n, c in comp_counter.most_common(5)],
        "profiles": records,
    }

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
