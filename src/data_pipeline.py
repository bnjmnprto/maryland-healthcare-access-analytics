"""Clean, feature engineer, and publish Maryland county healthcare access data."""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "maryland_county_health_access_sample.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
DATABASE_PATH = PROCESSED_DIR / "maryland_healthcare_access.db"


RISK_DRIVER_LABELS = {
    "provider_gap_index": "Provider access gap",
    "socioeconomic_need_index": "Socioeconomic need",
    "chronic_burden_index": "Chronic disease burden",
    "hospital_quality_gap_index": "Hospital quality/capacity gap",
}


REQUIRED_COLUMNS = {
    "data_year",
    "county_fips",
    "county_name",
    "region",
    "population",
    "median_household_income",
    "poverty_pct",
    "uninsured_pct",
    "pct_age_65_plus",
    "pct_nonwhite",
    "rural_flag",
    "primary_care_physicians_per_100k",
    "mental_health_providers_per_100k",
    "dental_providers_per_100k",
    "hpsa_primary_care_score",
    "hpsa_mental_health_score",
    "acute_care_hospitals",
    "hospital_beds_per_1000",
    "avg_hospital_star_rating",
    "readmission_rate_pct",
    "diabetes_pct",
    "obesity_pct",
    "hypertension_pct",
    "poor_or_fair_health_pct",
    "preventable_hospital_stays_per_100k",
    "life_expectancy",
}


def min_max_scale(series: pd.Series, invert: bool = False) -> pd.Series:
    """Scale a numeric series to 0-100, optionally reversing the direction."""
    numeric = pd.to_numeric(series, errors="coerce")
    span = numeric.max() - numeric.min()
    if pd.isna(span) or span == 0:
        scaled = pd.Series(50.0, index=series.index)
    else:
        scaled = ((numeric - numeric.min()) / span) * 100
    return 100 - scaled if invert else scaled


def require_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Raw data is missing required columns: {', '.join(missing)}")


def load_raw_data(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Raw file not found at {path}. Add the sample file or update the --raw-path argument."
        )
    df = pd.read_csv(path, dtype={"county_fips": str})
    require_columns(df, REQUIRED_COLUMNS)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [column.strip().lower() for column in cleaned.columns]
    cleaned["county_fips"] = cleaned["county_fips"].astype(str).str.zfill(5)
    cleaned["county_name"] = cleaned["county_name"].str.strip()
    cleaned["region"] = cleaned["region"].str.strip()

    numeric_columns = sorted(REQUIRED_COLUMNS - {"county_fips", "county_name", "region"})
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    if cleaned[numeric_columns].isna().any().any():
        null_counts = cleaned[numeric_columns].isna().sum()
        bad_columns = ", ".join(null_counts[null_counts > 0].index)
        raise ValueError(f"Numeric conversion produced missing values in: {bad_columns}")

    return cleaned.sort_values("county_name").reset_index(drop=True)


def add_feature_indices(df: pd.DataFrame) -> pd.DataFrame:
    featured = df.copy()

    featured["primary_care_gap"] = min_max_scale(
        featured["primary_care_physicians_per_100k"], invert=True
    )
    featured["mental_health_gap"] = min_max_scale(
        featured["mental_health_providers_per_100k"], invert=True
    )
    featured["dental_gap"] = min_max_scale(featured["dental_providers_per_100k"], invert=True)
    featured["hpsa_primary_need"] = min_max_scale(featured["hpsa_primary_care_score"])
    featured["hpsa_mental_need"] = min_max_scale(featured["hpsa_mental_health_score"])

    featured["provider_gap_index"] = featured[
        [
            "primary_care_gap",
            "mental_health_gap",
            "dental_gap",
            "hpsa_primary_need",
            "hpsa_mental_need",
        ]
    ].mean(axis=1)
    featured["provider_access_index"] = 100 - featured["provider_gap_index"]

    featured["socioeconomic_need_index"] = (
        min_max_scale(featured["poverty_pct"]) * 0.35
        + min_max_scale(featured["uninsured_pct"]) * 0.35
        + min_max_scale(featured["pct_age_65_plus"]) * 0.15
        + min_max_scale(featured["median_household_income"], invert=True) * 0.15
    )

    featured["chronic_burden_index"] = (
        min_max_scale(featured["diabetes_pct"]) * 0.25
        + min_max_scale(featured["obesity_pct"]) * 0.20
        + min_max_scale(featured["hypertension_pct"]) * 0.20
        + min_max_scale(featured["poor_or_fair_health_pct"]) * 0.20
        + min_max_scale(featured["preventable_hospital_stays_per_100k"]) * 0.15
    )

    featured["hospital_quality_gap_index"] = (
        min_max_scale(featured["avg_hospital_star_rating"], invert=True) * 0.45
        + min_max_scale(featured["hospital_beds_per_1000"], invert=True) * 0.20
        + min_max_scale(featured["readmission_rate_pct"]) * 0.25
        + min_max_scale(featured["acute_care_hospitals"], invert=True) * 0.10
    )

    featured["access_risk_score"] = (
        featured["provider_gap_index"] * 0.35
        + featured["socioeconomic_need_index"] * 0.25
        + featured["chronic_burden_index"] * 0.25
        + featured["hospital_quality_gap_index"] * 0.15
    ).round(1)

    high_risk_cutoff = featured["access_risk_score"].quantile(0.75)
    featured["high_access_risk"] = (featured["access_risk_score"] >= high_risk_cutoff).astype(int)
    featured["access_risk_tier"] = pd.cut(
        featured["access_risk_score"],
        bins=[-np.inf, 35, 55, 70, np.inf],
        labels=["Low", "Moderate", "Elevated", "High"],
    ).astype(str)
    featured["top_risk_factor"] = featured[list(RISK_DRIVER_LABELS)].idxmax(axis=1).map(
        RISK_DRIVER_LABELS
    )

    return featured


def build_table_frames(featured: pd.DataFrame) -> dict[str, pd.DataFrame]:
    counties = featured[["county_fips", "county_name", "region", "rural_flag"]].copy()

    demographics = featured[
        [
            "county_fips",
            "data_year",
            "population",
            "median_household_income",
            "poverty_pct",
            "uninsured_pct",
            "pct_age_65_plus",
            "pct_nonwhite",
        ]
    ].copy()

    health_outcomes = featured[
        [
            "county_fips",
            "data_year",
            "diabetes_pct",
            "obesity_pct",
            "hypertension_pct",
            "poor_or_fair_health_pct",
            "preventable_hospital_stays_per_100k",
            "life_expectancy",
        ]
    ].copy()

    provider_shortages = featured[
        [
            "county_fips",
            "data_year",
            "primary_care_physicians_per_100k",
            "mental_health_providers_per_100k",
            "dental_providers_per_100k",
            "hpsa_primary_care_score",
            "hpsa_mental_health_score",
            "provider_access_index",
        ]
    ].copy()

    hospital_quality = featured[
        [
            "county_fips",
            "data_year",
            "acute_care_hospitals",
            "hospital_beds_per_1000",
            "avg_hospital_star_rating",
            "readmission_rate_pct",
        ]
    ].copy()

    access_risk_scores = featured[
        [
            "county_fips",
            "data_year",
            "access_risk_score",
            "access_risk_tier",
            "high_access_risk",
            "socioeconomic_need_index",
            "provider_gap_index",
            "chronic_burden_index",
            "hospital_quality_gap_index",
            "top_risk_factor",
        ]
    ].copy()

    return {
        "counties": counties,
        "demographics": demographics,
        "health_outcomes": health_outcomes,
        "provider_shortages": provider_shortages,
        "hospital_quality": hospital_quality,
        "access_risk_scores": access_risk_scores,
    }


def write_sqlite_database(tables: dict[str, pd.DataFrame], database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.executescript(schema_sql)
            for table_name, table_df in tables.items():
                table_df.to_sql(table_name, connection, if_exists="append", index=False)


def write_processed_outputs(featured: pd.DataFrame, output_dir: Path = PROCESSED_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    featured.to_csv(output_dir / "dashboard_county_risk.csv", index=False)

    model_features = featured[
        [
            "county_fips",
            "county_name",
            "poverty_pct",
            "uninsured_pct",
            "pct_age_65_plus",
            "primary_care_physicians_per_100k",
            "mental_health_providers_per_100k",
            "dental_providers_per_100k",
            "hpsa_primary_care_score",
            "hpsa_mental_health_score",
            "diabetes_pct",
            "obesity_pct",
            "hypertension_pct",
            "poor_or_fair_health_pct",
            "preventable_hospital_stays_per_100k",
            "avg_hospital_star_rating",
            "readmission_rate_pct",
            "provider_gap_index",
            "socioeconomic_need_index",
            "chronic_burden_index",
            "hospital_quality_gap_index",
            "access_risk_score",
            "high_access_risk",
            "top_risk_factor",
        ]
    ].copy()
    model_features.to_csv(output_dir / "model_feature_table.csv", index=False)

    state_average = featured.select_dtypes(include=[np.number]).mean(numeric_only=True).to_frame(
        "maryland_average"
    )
    state_average.to_csv(output_dir / "state_average.csv", index_label="metric")


def run_pipeline(raw_path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    raw = load_raw_data(raw_path)
    cleaned = clean_data(raw)
    featured = add_feature_indices(cleaned)
    tables = build_table_frames(featured)
    write_sqlite_database(tables)
    write_processed_outputs(featured)
    return featured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-path",
        type=Path,
        default=RAW_DATA_PATH,
        help="Path to county-level raw CSV file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    featured = run_pipeline(args.raw_path)
    top_counties = featured.nlargest(5, "access_risk_score")[
        ["county_name", "access_risk_score", "access_risk_tier"]
    ]
    print("Pipeline completed.")
    print(f"Processed rows: {len(featured)}")
    print(f"SQLite database: {DATABASE_PATH}")
    print("Top access-risk counties:")
    print(top_counties.to_string(index=False))


if __name__ == "__main__":
    main()
