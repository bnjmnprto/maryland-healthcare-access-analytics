"""Fetch Maryland county ACS 5-year demographics through Census Reporter.

The U.S. Census API may require an API key in some environments. Census Reporter
is a public no-key API backed by ACS tables, which keeps this portfolio project
runnable by default while still using ACS county-level estimates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.fetch_common import PROCESSED_DIR, RAW_DIR, as_float, fetch_json, percent, today_iso


ACS_TABLES = ["B01003", "B17001", "B19013", "B27010", "B01001", "B18101", "B08201", "B28002"]
ACS_URL = (
    "https://api.censusreporter.org/1.0/data/show/latest"
    f"?table_ids={','.join(ACS_TABLES)}&geo_ids=050|04000US24"
)
RAW_ACS_DIR = RAW_DIR / "acs"
RAW_ACS_JSON = RAW_ACS_DIR / "acs_census_reporter_latest.json"
PROCESSED_ACS_PATH = PROCESSED_DIR / "acs_county_demographics.csv"
ACS_METADATA_PATH = PROCESSED_DIR / "acs_county_demographics_metadata.json"

UNINSURED_COLUMNS = ["B27010017", "B27010033", "B27010050", "B27010066"]
AGE_65_PLUS_COLUMNS = [
    "B01001020",
    "B01001021",
    "B01001022",
    "B01001023",
    "B01001024",
    "B01001025",
    "B01001044",
    "B01001045",
    "B01001046",
    "B01001047",
    "B01001048",
    "B01001049",
]
DISABILITY_COLUMNS = [
    "B18101004",
    "B18101007",
    "B18101010",
    "B18101013",
    "B18101016",
    "B18101019",
    "B18101023",
    "B18101026",
    "B18101029",
    "B18101032",
    "B18101035",
    "B18101038",
]


VARIABLE_LABELS = {
    "population": "ACS B01003 total population",
    "poverty_pct": "ACS B17001 population below poverty / poverty universe",
    "median_household_income": "ACS B19013 median household income",
    "uninsured_pct": "ACS B27010 no health insurance coverage / coverage universe",
    "age_65_plus_pct": "ACS B01001 population age 65+ / total population",
    "disability_pct": "ACS B18101 population with a disability / civilian noninstitutionalized population",
    "transportation_access_proxy": "ACS B08201 households with no vehicle available / households",
    "internet_access_gap_pct": "ACS B28002 households with no internet access / households",
}


def _estimate(block: dict, variable: str) -> float | None:
    return as_float(block.get("estimate", {}).get(variable))


def _sum_estimates(block: dict, variables: list[str]) -> float | None:
    values = [_estimate(block, variable) for variable in variables]
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return float(sum(numeric))


def _county_name(name: str) -> str:
    cleaned = name.replace(", Maryland", "").replace(", MD", "").strip()
    if cleaned.lower().endswith(" county"):
        cleaned = cleaned[:-7]
    elif cleaned.lower().endswith(" city"):
        cleaned = f"{cleaned[:-5]} City"
    return cleaned.strip()


def parse_acs_response(payload: dict) -> pd.DataFrame:
    release = payload.get("release", {})
    rows: list[dict] = []
    for geo_id, tables in payload.get("data", {}).items():
        if not geo_id.startswith("05000US"):
            continue

        fips = geo_id[-5:]
        b01003 = tables["B01003"]
        b17001 = tables["B17001"]
        b19013 = tables["B19013"]
        b27010 = tables["B27010"]
        b01001 = tables["B01001"]
        b18101 = tables["B18101"]
        b08201 = tables["B08201"]
        b28002 = tables["B28002"]

        population = _estimate(b01003, "B01003001")
        poverty_universe = _estimate(b17001, "B17001001")
        poverty_count = _estimate(b17001, "B17001002")
        uninsured_universe = _estimate(b27010, "B27010001")
        uninsured_count = _sum_estimates(b27010, UNINSURED_COLUMNS)
        age_65_plus_count = _sum_estimates(b01001, AGE_65_PLUS_COLUMNS)
        disability_universe = _estimate(b18101, "B18101001")
        disability_count = _sum_estimates(b18101, DISABILITY_COLUMNS)
        households_vehicle_universe = _estimate(b08201, "B08201001")
        households_no_vehicle_count = _estimate(b08201, "B08201002")
        internet_universe = _estimate(b28002, "B28002001")
        no_internet_access_count = _estimate(b28002, "B28002013")

        rows.append(
            {
                "county_fips": fips,
                "county_name": _county_name(payload["geography"][geo_id]["name"]),
                "source_year": release.get("years") or release.get("name"),
                "acs_release": release.get("name"),
                "date_accessed": today_iso(),
                "population": int(population) if population is not None else None,
                "poverty_count": poverty_count,
                "poverty_universe": poverty_universe,
                "poverty_pct": percent(poverty_count, poverty_universe),
                "median_household_income": _estimate(b19013, "B19013001"),
                "uninsured_count": uninsured_count,
                "uninsured_universe": uninsured_universe,
                "uninsured_pct": percent(uninsured_count, uninsured_universe),
                "age_65_plus_count": age_65_plus_count,
                "age_65_plus_pct": percent(age_65_plus_count, population),
                "disability_count": disability_count,
                "disability_pct": percent(disability_count, disability_universe),
                "households_no_vehicle_count": households_no_vehicle_count,
                "transportation_access_proxy": percent(
                    households_no_vehicle_count, households_vehicle_universe
                ),
                "no_internet_access_count": no_internet_access_count,
                "internet_access_gap_pct": percent(no_internet_access_count, internet_universe),
                "source_acs": "real_public_data",
            }
        )

    frame = pd.DataFrame(rows)
    frame["county_fips"] = frame["county_fips"].astype(str).str.zfill(5)
    return frame.sort_values("county_name").reset_index(drop=True)


def fetch_acs(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    if PROCESSED_ACS_PATH.exists() and ACS_METADATA_PATH.exists() and not refresh:
        return (
            pd.read_csv(PROCESSED_ACS_PATH, dtype={"county_fips": str}),
            json.loads(ACS_METADATA_PATH.read_text(encoding="utf-8")),
        )

    payload = fetch_json(ACS_URL)
    RAW_ACS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_ACS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    frame = parse_acs_response(payload)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED_ACS_PATH, index=False)

    metadata = {
        "source_name": "U.S. Census ACS 5-year via Census Reporter API",
        "access_url": ACS_URL,
        "release": payload.get("release", {}),
        "date_accessed": today_iso(),
        "rows": int(len(frame)),
        "variables": VARIABLE_LABELS,
        "status": "loaded",
        "notes": (
            "Census Reporter exposes ACS estimates without requiring a Census API key. "
            "For production, teams may swap in direct api.census.gov calls with an API key."
        ),
    }
    ACS_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return frame, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch from the public API even if cached.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame, metadata = fetch_acs(refresh=args.refresh)
    print(f"Wrote {PROCESSED_ACS_PATH}")
    print(f"Rows: {len(frame)} | Source: {metadata['source_name']}")


if __name__ == "__main__":
    main()
