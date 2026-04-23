"""Upload GitHub candidate profiles from a CSV into the Supabase
`github_profiles` table.

Source CSV columns expected:
    role, username, name, github_url, location, company,
    experience_years_est, account_age_years, followers, public_repos,
    role_match_confidence, overall_score, skills_detected, wow_signals,
    red_flags, summary, bio, blog, email

Transformations applied to match the Supabase schema:
  - role_match_confidence: divided by 100 if > 1 (CSV uses 0-100, Supabase 0-1)
  - skills_detected, wow_signals, red_flags: split on ';' into string arrays
  - followers, public_repos: cast to int
  - experience_years_est, account_age_years, overall_score: cast to float
  - nan/empty values mapped to None

Usage:
    python scripts/upload_github_profiles.py ../Github/candidates-1.csv
"""

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

TABLE = "github_profiles"
LIST_COLUMNS = ("skills_detected", "wow_signals", "red_flags")
INT_COLUMNS = ("followers", "public_repos")
FLOAT_COLUMNS = ("experience_years_est", "account_age_years", "overall_score")
TEXT_COLUMNS = (
    "username",
    "name",
    "email",
    "bio",
    "blog",
    "github_url",
    "location",
    "company",
    "role",
    "summary",
)


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _to_list(v: Any) -> Optional[List[str]]:
    if _is_blank(v):
        return None
    items = [s.strip() for s in str(v).split(";") if s.strip()]
    return items or None


def _to_int(v: Any) -> Optional[int]:
    if _is_blank(v):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _to_float(v: Any) -> Optional[float]:
    if _is_blank(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_text(v: Any) -> Optional[str]:
    if _is_blank(v):
        return None
    return str(v).strip()


def row_to_record(row: Dict[str, Any]) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    for col in TEXT_COLUMNS:
        rec[col] = _to_text(row.get(col))
    for col in INT_COLUMNS:
        rec[col] = _to_int(row.get(col))
    for col in FLOAT_COLUMNS:
        rec[col] = _to_float(row.get(col))
    for col in LIST_COLUMNS:
        rec[col] = _to_list(row.get(col))

    # role_match_confidence: CSV is 0-100 scale, Supabase schema is 0-1
    rmc = _to_float(row.get("role_match_confidence"))
    if rmc is not None and rmc > 1:
        rmc = round(rmc / 100.0, 4)
    rec["role_match_confidence"] = rmc

    if not rec.get("username"):
        raise ValueError(f"row missing username: {row}")
    return rec


def upload(csv_path: Path, dry_run: bool = False) -> None:
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

    df = pd.read_csv(csv_path)
    print(f"loaded {len(df)} rows from {csv_path}")

    records = [row_to_record(r) for r in df.to_dict(orient="records")]
    print(f"built {len(records)} records; preview of first:")
    for k, v in records[0].items():
        print(f"  {k}: {v!r}")

    if dry_run:
        print("dry-run: no write performed")
        return

    client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    resp = client.table(TABLE).upsert(records, on_conflict="username").execute()
    inserted = len(resp.data) if getattr(resp, "data", None) else len(records)
    print(f"upserted {inserted} rows into {TABLE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    upload(args.csv, dry_run=args.dry_run)
