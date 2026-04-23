"""Write a multi-sheet Excel workbook from the three CSV files plus a summary."""

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def write_excel(
    profiles: List[Dict[str, Any]],
    freelances_csv: Path,
    missions_csv: Path,
    skills_csv: Path,
    out: Path,
) -> None:
    df_free = pd.read_csv(freelances_csv) if freelances_csv.exists() else pd.DataFrame()
    df_miss = pd.read_csv(missions_csv) if missions_csv.exists() else pd.DataFrame()
    df_sk = pd.read_csv(skills_csv) if skills_csv.exists() else pd.DataFrame()

    skill_counter: Counter = Counter()
    comp_counter: Counter = Counter()
    for p in profiles:
        for s in (p.get("matched_skills") or []):
            name = s[0] if isinstance(s, (list, tuple)) else s
            skill_counter[name] += 1
        for c in (p.get("competitors_detected") or []):
            key = c[0] if isinstance(c, (list, tuple)) else c
            comp_counter[key] += 1

    summary_rows = [
        {"metric": "total_profiles", "value": len(profiles)},
        {"metric": "is_match_true", "value": sum(1 for p in profiles if p.get("is_match"))},
        {"metric": "worked_for_competitor", "value": sum(1 for p in profiles if p.get("competitors_detected"))},
    ]
    for name, cnt in skill_counter.most_common(10):
        summary_rows.append({"metric": f"top_skill:{name}", "value": cnt})
    for name, cnt in comp_counter.most_common(5):
        summary_rows.append({"metric": f"top_competitor:{name}", "value": cnt})
    df_summary = pd.DataFrame(summary_rows)

    with pd.ExcelWriter(out, engine="openpyxl") as xl:
        df_free.to_excel(xl, sheet_name="freelances", index=False)
        df_miss.to_excel(xl, sheet_name="missions", index=False)
        df_sk.to_excel(xl, sheet_name="skills", index=False)
        df_summary.to_excel(xl, sheet_name="summary", index=False)
