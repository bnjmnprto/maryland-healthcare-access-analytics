"""Fetch CMS hospital availability and quality fields for Maryland counties."""

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


PROJECT_SAMPLE_PATH = RAW_DIR / "maryland_county_health_access_sample.csv"
CMS_URL_TEMPLATE = (
    "https://data.cms.gov/provider-data/api/1/datastore/query/"
    "xubh-q36u/0?limit=1000&offset={offset}"
)
RAW_CMS_DIR = RAW_DIR / "cms_hospital_quality"
RAW_CMS_JSON = RAW_CMS_DIR / "cms_hospital_general_information_maryland.json"
PROCESSED_CMS_PATH = PROCESSED_DIR / "cms_hospital_quality_maryland.csv"
CMS_METADATA_PATH = PROCESSED_DIR / "cms_hospital_quality_metadata.json"


def _load_scaffold() -> pd.DataFrame:
    return pd.read_csv(PROJECT_SAMPLE_PATH, dtype={"county_fips": str})[
        ["county_fips", "county_name"]
    ].drop_duplicates()


def _cms_county_lookup(scaffold: pd.DataFrame) -> dict[str, str]:
    lookup = {}
    for _, row in scaffold.iterrows():
        name = row["county_name"].upper()
        if name == "BALTIMORE CITY":
            lookup["BALTIMORE CITY"] = row["county_fips"]
        else:
            lookup[name.replace(" COUNTY", "")] = row["county_fips"]
    return lookup


def _fetch_all_hospitals() -> list[dict]:
    rows: list[dict] = []
    offset = 0
    expected_count = None
    while True:
        payload = fetch_json(CMS_URL_TEMPLATE.format(offset=offset), timeout=120)
        chunk = payload.get("results", [])
        if expected_count is None:
            expected_count = int(payload.get("count") or 0)
        if not chunk:
            break
        rows.extend(chunk)
        offset += len(chunk)
        if expected_count and offset >= expected_count:
            break
    return rows


def parse_cms_hospitals(rows: list[dict]) -> pd.DataFrame:
    scaffold = _load_scaffold()
    lookup = _cms_county_lookup(scaffold)
    output = scaffold.copy()

    md_rows = [row for row in rows if row.get("state") == "MD"]
    RAW_CMS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_CMS_JSON.write_text(json.dumps(md_rows, indent=2), encoding="utf-8")

    parsed = []
    for row in md_rows:
        county_raw = str(row.get("countyparish", "")).strip().upper()
        fips = lookup.get(county_raw)
        if not fips:
            continue
        rating = as_float(row.get("hospital_overall_rating"))
        readm_worse_count = as_float(row.get("count_of_readm_measures_worse"))
        parsed.append(
            {
                "county_fips": fips,
                "hospital_count": 1,
                "acute_care_hospitals": 1
                if str(row.get("hospital_type", "")).lower().startswith("acute care")
                else 0,
                "emergency_services_count": 1 if row.get("emergency_services") == "Yes" else 0,
                "rating_total": rating if rating is not None else 0,
                "rating_count": 1 if rating is not None else 0,
                "readmission_worse_measure_count": readm_worse_count or 0,
            }
        )

    if not parsed:
        output["hospital_count"] = 0
        output["acute_care_hospitals"] = 0
        output["emergency_services_count"] = 0
        output["avg_hospital_star_rating"] = 0
        output["readmission_worse_measure_count"] = 0
    else:
        grouped = pd.DataFrame(parsed).groupby("county_fips", as_index=False).sum(numeric_only=True)
        grouped["avg_hospital_star_rating"] = grouped.apply(
            lambda row: row["rating_total"] / row["rating_count"]
            if row["rating_count"]
            else None,
            axis=1,
        )
        grouped = grouped.drop(columns=["rating_total", "rating_count"])
        output = output.merge(grouped, on="county_fips", how="left")
        fill_columns = [
            "hospital_count",
            "acute_care_hospitals",
            "emergency_services_count",
            "avg_hospital_star_rating",
            "readmission_worse_measure_count",
        ]
        output[fill_columns] = output[fill_columns].fillna(0)

    output["date_accessed"] = today_iso()
    output["source_cms_hospital_quality"] = "real_public_data"
    return output


def fetch_cms_hospital_quality(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    if PROCESSED_CMS_PATH.exists() and CMS_METADATA_PATH.exists() and not refresh:
        return (
            pd.read_csv(PROCESSED_CMS_PATH, dtype={"county_fips": str}),
            json.loads(CMS_METADATA_PATH.read_text(encoding="utf-8")),
        )

    rows = _fetch_all_hospitals()
    frame = parse_cms_hospitals(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROCESSED_CMS_PATH, index=False)

    metadata = {
        "source_name": "CMS Provider Data: Hospital General Information",
        "access_url": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
        "api_url_template": CMS_URL_TEMPLATE,
        "date_accessed": today_iso(),
        "rows": int(len(frame)),
        "status": "loaded",
        "variables": {
            "hospital_count": "CMS hospital facility count by county",
            "acute_care_hospitals": "CMS acute care hospital count by county",
            "emergency_services_count": "Hospitals reporting emergency services = Yes",
            "avg_hospital_star_rating": "Average numeric CMS overall hospital rating by county",
        },
        "notes": (
            "The CMS General Information file does not include hospital beds or a county-level "
            "readmission rate, so those exact fields remain documented fallback inputs."
        ),
    }
    CMS_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return frame, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch source files even if cached.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame, metadata = fetch_cms_hospital_quality(refresh=args.refresh)
    print(f"Wrote {PROCESSED_CMS_PATH}")
    print(f"Rows: {len(frame)} | Source: {metadata['source_name']}")


if __name__ == "__main__":
    main()
