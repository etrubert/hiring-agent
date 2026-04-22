"""Write an Excel workbook with tabs: All, per-platform, per-target-role."""

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.storage.csv_writer import (
    HACKATHON_COLUMNS,
    PEOPLE_COLUMNS,
    COMPANY_COLUMNS,
    _company_rows,
    _hackathon_row,
    _people_rows,
)

logger = logging.getLogger(__name__)


def _sheet_name(raw: str) -> str:
    sanitized = "".join(c for c in raw if c not in r"[]:*?/\\")[:31]
    return sanitized or "Unknown"


def write_excel(hackathons: List[Dict], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_h = pd.DataFrame([_hackathon_row(h) for h in hackathons], columns=HACKATHON_COLUMNS)
    df_p = pd.DataFrame(_people_rows(hackathons), columns=PEOPLE_COLUMNS)
    df_c = pd.DataFrame(_company_rows(hackathons), columns=COMPANY_COLUMNS)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_h.to_excel(writer, sheet_name="Hackathons", index=False)
        df_p.to_excel(writer, sheet_name="People", index=False)
        df_c.to_excel(writer, sheet_name="Companies", index=False)

        if not df_h.empty:
            for platform, sub in df_h.groupby("source_platform"):
                sub.to_excel(writer, sheet_name=_sheet_name(f"P_{platform}"), index=False)

        if not df_p.empty:
            for role, sub in df_p.groupby("target_role"):
                label = role or "Unmatched"
                sub.to_excel(writer, sheet_name=_sheet_name(f"R_{label}"), index=False)

    logger.info("wrote excel workbook to %s", out_path)
    return out_path
