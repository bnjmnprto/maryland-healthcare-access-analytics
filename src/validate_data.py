"""Validate project data artifacts and write data quality reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.data_pipeline import RAW_DATA_PATH, REQUIRED_COLUMNS, RUN_METADATA_PATH, run_pipeline
from src.fetch_common import MARYLAND_COUNTY_FIPS


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DASHBOARD_DATA_PATH = PROCESSED_DIR / "dashboard_county_risk.csv"
FEATURE_TABLE_PATH = PROCESSED_DIR / "healthcare_access_features.csv"
MODEL_FEATURE_TABLE_PATH = PROCESSED_DIR / "model_feature_table.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "data_quality_report.md"
VALIDATION_REPORT_PATH = PROJECT_ROOT / "docs" / "validation_report.md"


REQUIRED_DASHBOARD_COLUMNS = {
    "county_fips",
    "county_name",
    "data_mode",
    "source_acs",
    "source_cdc_places",
    "source_hrsa_hpsa",
    "source_cms_hospital_quality",
    "population",
    "poverty_pct",
    "median_household_income",
    "uninsured_pct",
    "pct_age_65_plus",
    "disability_pct",
    "transportation_access_proxy",
    "poor_or_fair_health_pct",
    "diabetes_pct",
    "hypertension_pct",
    "obesity_pct",
    "smoking_pct",
    "provider_gap_index",
    "socioeconomic_need_index",
    "insurance_access_burden_index",
    "chronic_burden_index",
    "hospital_quality_gap_index",
    "access_risk_score",
    "access_risk_tier",
    "top_risk_factor",
}


RANGE_CHECKS = {
    "poverty_pct": (0, 100),
    "uninsured_pct": (0, 100),
    "pct_age_65_plus": (0, 100),
    "disability_pct": (0, 100),
    "transportation_access_proxy": (0, 100),
    "internet_access_gap_pct": (0, 100),
    "poor_or_fair_health_pct": (0, 100),
    "diabetes_pct": (0, 100),
    "hypertension_pct": (0, 100),
    "obesity_pct": (0, 100),
    "smoking_pct": (0, 100),
    "access_risk_score": (0, 100),
    "provider_gap_index": (0, 100),
    "socioeconomic_need_index": (0, 100),
    "insurance_access_burden_index": (0, 100),
    "chronic_burden_index": (0, 100),
    "hospital_quality_gap_index": (0, 100),
}


def ensure_processed_data() -> pd.DataFrame:
    if not DASHBOARD_DATA_PATH.exists() or not RUN_METADATA_PATH.exists():
        run_pipeline()
    return pd.read_csv(DASHBOARD_DATA_PATH, dtype={"county_fips": str})


def load_metadata() -> dict:
    if not RUN_METADATA_PATH.exists():
        run_pipeline()
    return json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))


def validate_required_files() -> list[str]:
    required_files = [
        RAW_DATA_PATH,
        DASHBOARD_DATA_PATH,
        FEATURE_TABLE_PATH,
        MODEL_FEATURE_TABLE_PATH,
        RUN_METADATA_PATH,
        PROJECT_ROOT / "sql" / "schema.sql",
        PROJECT_ROOT / "sql" / "queries.sql",
        PROJECT_ROOT / "sql" / "validation_queries.sql",
        PROJECT_ROOT / "data" / "raw" / "maryland_counties.geojson",
        PROJECT_ROOT / "docs" / "data_provenance.md",
        PROJECT_ROOT / "docs" / "data_sources.md",
    ]
    return [str(path.relative_to(PROJECT_ROOT)) for path in required_files if not path.exists()]


def validate_dataframes(raw: pd.DataFrame, processed: pd.DataFrame, metadata: dict) -> list[str]:
    errors: list[str] = []

    missing_raw_columns = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing_raw_columns:
        errors.append(f"Raw sample data missing required columns: {missing_raw_columns}")

    missing_processed_columns = sorted(REQUIRED_DASHBOARD_COLUMNS - set(processed.columns))
    if missing_processed_columns:
        errors.append(f"Processed data missing required columns: {missing_processed_columns}")

    fips = set(processed["county_fips"].astype(str).str.zfill(5))
    missing_counties = sorted(MARYLAND_COUNTY_FIPS - fips)
    extra_counties = sorted(fips - MARYLAND_COUNTY_FIPS)
    if missing_counties:
        errors.append(f"Processed data missing Maryland county FIPS: {missing_counties}")
    if extra_counties:
        errors.append(f"Processed data contains unexpected FIPS: {extra_counties}")

    if "Baltimore City" not in set(processed["county_name"]):
        errors.append("Baltimore City is missing from processed data")

    if processed["county_fips"].duplicated().any():
        errors.append("Processed data has duplicate county FIPS values")
    if processed["county_name"].duplicated().any():
        errors.append("Processed data has duplicate county names")

    if processed["access_risk_tier"].isna().any():
        errors.append("Access risk tier must be populated for every row")

    for column, (minimum, maximum) in RANGE_CHECKS.items():
        if column not in processed.columns:
            continue
        if not processed[column].between(minimum, maximum).all():
            errors.append(f"{column} values must be between {minimum} and {maximum}")

    if metadata.get("maryland_jurisdictions_represented") != 24:
        errors.append("run_metadata.json does not record 24 Maryland jurisdictions")
    if metadata.get("all_24_jurisdictions_present") is not True:
        errors.append("run_metadata.json does not confirm complete jurisdiction coverage")
    if not metadata.get("data_mode"):
        errors.append("run_metadata.json does not record data_mode")
    if "sources_successfully_loaded" not in metadata:
        errors.append("run_metadata.json does not record source coverage")

    return errors


def _missingness_lines(processed: pd.DataFrame) -> list[str]:
    missingness = processed.isna().sum()
    lines = [
        f"- `{column}`: {int(count)} missing values"
        for column, count in missingness.items()
        if int(count) > 0
    ]
    return lines or ["- No missing values detected in processed dashboard data."]


def build_report(raw: pd.DataFrame, processed: pd.DataFrame, metadata: dict, errors: list[str]) -> str:
    duplicate_fips = int(processed["county_fips"].duplicated().sum())
    duplicate_names = int(processed["county_name"].duplicated().sum())
    risk_min = processed["access_risk_score"].min()
    risk_max = processed["access_risk_score"].max()
    tier_counts = processed["access_risk_tier"].value_counts().to_dict()

    status = "PASS" if not errors else "REVIEW REQUIRED"
    error_lines = [f"- {error}" for error in errors] or ["- No validation errors detected."]
    loaded = metadata.get("sources_successfully_loaded", [])
    fallback = metadata.get("sources_using_fallback", [])

    source_lines = [
        f"- Data mode: `{metadata.get('data_mode', 'unknown')}`",
        f"- Sources loaded: {', '.join(loaded) if loaded else 'None recorded'}",
        f"- Sources/fields using fallback: {', '.join(fallback) if fallback else 'None recorded'}",
        f"- Run timestamp: {metadata.get('run_timestamp', 'unknown')}",
        f"- All 24 jurisdictions present: {metadata.get('all_24_jurisdictions_present')}",
    ]

    return f"""# Data Quality Report

## Validation Status

**Status:** {status}

## Source Coverage

{chr(10).join(source_lines)}

The default pipeline now attempts real public ACS and CDC PLACES data first, then adds HRSA HPSA and CMS Hospital General Information when available. The bundled sample file remains as a fallback for fields that are unavailable from those public feeds, including some provider workforce and hospital capacity fields.

## Row Counts

- Raw sample rows: {len(raw)}
- Processed feature rows: {len(processed)}
- Expected Maryland county/county-equivalent rows: {len(MARYLAND_COUNTY_FIPS)}

## County Coverage

- Unique processed county FIPS codes: {processed["county_fips"].nunique()}
- Baltimore City present: {"Baltimore City" in set(processed["county_name"])}
- County coverage complete: {processed["county_fips"].nunique() == len(MARYLAND_COUNTY_FIPS)}

## Missingness

{chr(10).join(_missingness_lines(processed))}

## Duplicate Checks

- Duplicate FIPS values: {duplicate_fips}
- Duplicate county names: {duplicate_names}

## Feature Range Checks

- Access risk score range: {risk_min:.1f} to {risk_max:.1f}
- Risk score within 0-100: {processed["access_risk_score"].between(0, 100).all()}
- Risk tier counts: {tier_counts}

## Validation Findings

{chr(10).join(error_lines)}

## Known Limitations

- The dataset is county-level and does not contain patient-level data.
- Data mode may be `mixed_real_and_demo_data` because public sources do not provide every portfolio field.
- Fallback fields are documented in `data/processed/run_metadata.json`.
- The risk score is a transparent prioritization index, not a clinically validated model.
- A production version should add scheduled source refreshes, direct source QA, stakeholder review, and equity impact review.
"""


def validate_project(write_report: bool = True) -> list[str]:
    raw = pd.read_csv(RAW_DATA_PATH, dtype={"county_fips": str})
    processed = ensure_processed_data()
    metadata = load_metadata()

    errors = validate_required_files()
    errors.extend(validate_dataframes(raw, processed, metadata))

    if write_report:
        report = build_report(raw, processed, metadata, errors)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        VALIDATION_REPORT_PATH.write_text(report.replace("# Data Quality Report", "# Validation Report"), encoding="utf-8")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-report", action="store_true", help="Validate without writing reports.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = validate_project(write_report=not args.no_report)
    if errors:
        print("Data validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Data validation passed. Report: {REPORT_PATH}")
    print(f"Validation report: {VALIDATION_REPORT_PATH}")


if __name__ == "__main__":
    main()
