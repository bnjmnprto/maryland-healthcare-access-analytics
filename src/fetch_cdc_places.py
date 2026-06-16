"""Fetch CDC PLACES county-level indicators for Maryland."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.fetch_common import PROCESSED_DIR, RAW_DIR, as_float, fetch_json, today_iso


CDC_PLACES_URL = "https://data.cdc.gov/resource/i46a-9kgh.json?$limit=5000&stateabbr=MD"
RAW_CDC_DIR = RAW_DIR / "cdc_places"
RAW_CDC_JSON = RAW_CDC_DIR / "cdc_places_maryland.json"
PROCESSED_CDC_PATH = PROCESSED_DIR / "cdc_places_maryland.csv"
CDC_METADATA_PATH = PROCESSED_DIR / "cdc_places_metadata.json"


VARIABLE_LABELS = {
    "poor_or_fair_health_pct": "CDC PLACES GHLTH crude prevalence",
    "diabetes_pct": "CDC PLACES DIABETES crude prevalence",
    "high_blood_pressure_pct": "CDC PLACES BPHIGH crude prevalence",
    "obesity_pct": "CDC PLACES OBESITY crude prevalence",
    "smoking_pct": "CDC PLACES CSMOKING crude prevalence",
    "frequent_physical_distress_pct": "CDC PLACES PHLTH crude prevalence",
    "routine_checkup_pct": "CDC PLACES CHECKUP crude prevalence",
    "places_uninsured_pct": "CDC PLACES ACCESS2 crude prevalence",
}


def parse_cdc_places(rows: list[dict]) -> pd.DataFrame:
    parsed_rows = []
    for row in rows:
        fips = str(row.get("countyfips", "")).zfill(5)
        if not fips.startswith("24"):
            continue
        parsed_rows.append(
            {
                "county_fips": fips,
                "county_name": str(row.get("countyname", "")).strip(),
                "source_year": "CDC PLACES county release",
                "date_accessed": today_iso(),
                "places_population": as_float(row.get("totalpopulation")),
                "poor_or_fair_health_pct": as_float(row.get("ghlth_crudeprev")),
                "diabetes_pct": as_float(row.get("diabetes_crudeprev")),
                "high_blood_pressure_pct": as_float(row.get("bphigh_crudeprev")),
                "obesity_pct": as_float(row.get("obesity_crudeprev")),
                "smoking_pct": as_float(row.get("csmoking_crudeprev")),
                "frequent_physical_distress_pct": as_float(row.get("phlth_crudeprev")),
                "routine_checkup_pct": as_float(row.get("checkup_crudeprev")),
                "places_uninsured_pct": as_float(row.get("access2_crudeprev")),
                "source_cdc_places": "real_public_data",
            }
        )
    frame = pd.DataFrame(parsed_rows)
    frame["county_fips"] = frame["county_fips"].astype(str).str.zfill(5)
    return frame.sort_values("county_name").reset_index(drop=True)


def fetch_cdc_places(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    if PROCESSED_CDC_PATH.exists() and CDC_METADATA_PATH.exists() and not refresh:
        return (
            pd.read_csv(PROCESSED_CDC_PATH, dtype={"county_fips": str}),
            json.loads(CDC_METADATA_PATH.read_text(encoding="utf-8")),
        )

    rows = fetch_json(CDC_PLACES_URL)
    RAW_CDC_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CDC_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    frame = parse_cdc_places(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED_CDC_PATH, index=False)

    metadata = {
        "source_name": "CDC PLACES county-level health indicators",
        "access_url": CDC_PLACES_URL,
        "release": "CDC PLACES county API",
        "date_accessed": today_iso(),
        "rows": int(len(frame)),
        "variables": VARIABLE_LABELS,
        "status": "loaded",
    }
    CDC_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return frame, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch from the public API even if cached.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame, metadata = fetch_cdc_places(refresh=args.refresh)
    print(f"Wrote {PROCESSED_CDC_PATH}")
    print(f"Rows: {len(frame)} | Source: {metadata['source_name']}")


if __name__ == "__main__":
    main()
