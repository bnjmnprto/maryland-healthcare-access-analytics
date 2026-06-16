"""Fetch and aggregate HRSA HPSA shortage designations for Maryland counties."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.fetch_common import PROCESSED_DIR, RAW_DIR, as_float, fetch_text, today_iso


PROJECT_SAMPLE_PATH = RAW_DIR / "maryland_county_health_access_sample.csv"
RAW_HRSA_DIR = RAW_DIR / "hrsa_hpsa"
PROCESSED_HRSA_PATH = PROCESSED_DIR / "hrsa_hpsa_maryland.csv"
HRSA_METADATA_PATH = PROCESSED_DIR / "hrsa_hpsa_metadata.json"

HRSA_SOURCES = {
    "primary_care": {
        "url": "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv",
        "score_column": "hpsa_primary_care_score",
        "count_column": "hpsa_primary_care_count",
        "flag_column": "hpsa_primary_care_designated",
    },
    "mental_health": {
        "url": "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_MH.csv",
        "score_column": "hpsa_mental_health_score",
        "count_column": "hpsa_mental_health_count",
        "flag_column": "hpsa_mental_health_designated",
    },
    "dental": {
        "url": "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_DH.csv",
        "score_column": "hpsa_dental_score",
        "count_column": "hpsa_dental_count",
        "flag_column": "hpsa_dental_designated",
    },
}


def _load_scaffold() -> pd.DataFrame:
    return pd.read_csv(PROJECT_SAMPLE_PATH, dtype={"county_fips": str})[
        ["county_fips", "county_name"]
    ].drop_duplicates()


def _county_fips(row: pd.Series) -> str:
    candidates = [
        "Common State County FIPS Code",
        "State and County Federal Information Processing Standard Code",
        "HPSA Geography Identification Number",
    ]
    for column in candidates:
        value = str(row.get(column, "")).strip()
        if value.startswith("24") and len(value) >= 5:
            return value[:5]
    return ""


def _summarize_source(name: str, url: str) -> tuple[pd.DataFrame, int]:
    text = fetch_text(url, timeout=180)
    raw = pd.read_csv(io.StringIO(text), dtype=str)
    raw["county_fips"] = raw.apply(_county_fips, axis=1)
    raw_md = raw[raw["county_fips"].str.startswith("24", na=False)].copy()
    RAW_HRSA_DIR.mkdir(parents=True, exist_ok=True)
    raw_md.to_csv(RAW_HRSA_DIR / f"{name}_maryland_raw.csv", index=False)

    designated = raw_md[raw_md.get("HPSA Status", "").eq("Designated")].copy()
    if designated.empty:
        return pd.DataFrame(columns=["county_fips", "hpsa_count", "hpsa_max_score"]), len(raw_md)
    designated["hpsa_score_numeric"] = designated.get("HPSA Score", "").apply(as_float).fillna(0)
    if "HPSA ID" in designated:
        designated = designated.drop_duplicates(["county_fips", "HPSA ID"])

    summary = (
        designated.groupby("county_fips", as_index=False)
        .agg(hpsa_count=("county_fips", "size"), hpsa_max_score=("hpsa_score_numeric", "max"))
        .reset_index(drop=True)
    )
    return summary, len(raw_md)


def fetch_hrsa_hpsa(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    if PROCESSED_HRSA_PATH.exists() and HRSA_METADATA_PATH.exists() and not refresh:
        return (
            pd.read_csv(PROCESSED_HRSA_PATH, dtype={"county_fips": str}),
            json.loads(HRSA_METADATA_PATH.read_text(encoding="utf-8")),
        )

    output = _load_scaffold()
    loaded_sources: list[str] = []
    source_rows: dict[str, int] = {}
    for name, config in HRSA_SOURCES.items():
        summary, row_count = _summarize_source(name, config["url"])
        source_rows[name] = row_count
        loaded_sources.append(name)
        output = output.merge(summary, on="county_fips", how="left")
        output[config["count_column"]] = output.pop("hpsa_count").fillna(0).astype(int)
        output[config["score_column"]] = output.pop("hpsa_max_score").fillna(0).astype(float)
        output[config["flag_column"]] = (output[config["count_column"]] > 0).astype(int)

    output["date_accessed"] = today_iso()
    output["source_hrsa_hpsa"] = "real_public_data"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(PROCESSED_HRSA_PATH, index=False)

    metadata = {
        "source_name": "HRSA Health Professional Shortage Area downloads",
        "access_urls": {name: config["url"] for name, config in HRSA_SOURCES.items()},
        "date_accessed": today_iso(),
        "rows": int(len(output)),
        "source_rows": source_rows,
        "sources_loaded": loaded_sources,
        "status": "loaded",
        "variables": {
            "hpsa_primary_care_score": "Maximum HRSA primary care HPSA score by county",
            "hpsa_mental_health_score": "Maximum HRSA mental health HPSA score by county",
            "hpsa_dental_score": "Maximum HRSA dental HPSA score by county",
            "hpsa_*_designated": "1 when the county has at least one designated HPSA record",
        },
    }
    HRSA_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch source files even if cached.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame, metadata = fetch_hrsa_hpsa(refresh=args.refresh)
    print(f"Wrote {PROCESSED_HRSA_PATH}")
    print(f"Rows: {len(frame)} | Sources: {', '.join(metadata['sources_loaded'])}")


if __name__ == "__main__":
    main()
