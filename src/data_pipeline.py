"""Build Maryland county healthcare access features from public data with fallback."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.fetch_acs import fetch_acs
from src.fetch_cdc_places import fetch_cdc_places
from src.fetch_cms_hospital_quality import fetch_cms_hospital_quality
from src.fetch_common import MARYLAND_COUNTY_FIPS, today_iso, utc_now_iso
from src.fetch_hrsa_hpsa import fetch_hrsa_hpsa


RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "maryland_county_health_access_sample.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
DATABASE_PATH = PROCESSED_DIR / "maryland_healthcare_access.db"
RUN_METADATA_PATH = PROCESSED_DIR / "run_metadata.json"


RISK_DRIVER_LABELS = {
    "socioeconomic_need_index": "Socioeconomic vulnerability",
    "insurance_access_burden_index": "Insurance and access burden",
    "chronic_burden_index": "Chronic disease burden",
    "provider_gap_index": "Provider shortage burden",
    "hospital_quality_gap_index": "Hospital availability/quality burden",
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


SOURCE_FETCHERS: dict[str, Callable[[bool], tuple[pd.DataFrame, dict]]] = {
    "ACS": fetch_acs,
    "CDC PLACES": fetch_cdc_places,
    "HRSA HPSA": fetch_hrsa_hpsa,
    "CMS Hospital Quality": fetch_cms_hospital_quality,
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

    numeric_columns = [
        column
        for column in cleaned.columns
        if column not in {"county_fips", "county_name", "region"}
        and not column.startswith("source_")
        and column not in {"data_mode", "top_risk_factor", "fallback_fields_note", "acs_source_year"}
    ]
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    required_numeric = sorted(REQUIRED_COLUMNS - {"county_fips", "county_name", "region"})
    if cleaned[required_numeric].isna().any().any():
        null_counts = cleaned[required_numeric].isna().sum()
        bad_columns = ", ".join(null_counts[null_counts > 0].index)
        raise ValueError(f"Numeric conversion produced missing values in: {bad_columns}")

    return cleaned.sort_values("county_name").reset_index(drop=True)


def _extract_year(value: object, fallback: int) -> int:
    match = re.search(r"(20\d{2})", str(value))
    return int(match.group(1)) if match else fallback


def _fetch_sources(refresh_public: bool) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict] = {}
    for source_name, fetcher in SOURCE_FETCHERS.items():
        try:
            frame, source_metadata = fetcher(refresh=refresh_public)
            frames[source_name] = frame
            metadata[source_name] = {**source_metadata, "status": "loaded"}
        except Exception as exc:  # pragma: no cover - exercised when public endpoints fail
            metadata[source_name] = {
                "source_name": source_name,
                "status": "fallback_used",
                "error": str(exc),
                "date_accessed": today_iso(),
            }
    return frames, metadata


def _source_status(frames: dict[str, pd.DataFrame], source_name: str) -> str:
    return "real_public_data" if source_name in frames else "fallback_sample"


def _assemble_public_feature_base(
    sample: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    source_metadata: dict[str, dict],
) -> tuple[pd.DataFrame, dict]:
    public = sample.copy()
    public["county_fips"] = public["county_fips"].astype(str).str.zfill(5)
    public["data_year"] = pd.to_numeric(public["data_year"], errors="coerce").fillna(2024).astype(int)

    sources_loaded = sorted(frames)
    sources_using_fallback = [
        source for source in SOURCE_FETCHERS if source not in frames
    ]

    if "ACS" in frames:
        acs = frames["ACS"].copy()
        public = public.merge(
            acs[
                [
                    "county_fips",
                    "source_year",
                    "population",
                    "poverty_pct",
                    "median_household_income",
                    "uninsured_pct",
                    "age_65_plus_pct",
                    "disability_pct",
                    "transportation_access_proxy",
                    "internet_access_gap_pct",
                ]
            ].rename(columns={"source_year": "acs_source_year"}),
            on="county_fips",
            how="left",
            suffixes=("", "_acs"),
        )
        for column in ["population", "poverty_pct", "median_household_income", "uninsured_pct"]:
            public[column] = public[f"{column}_acs"].combine_first(public[column])
            public = public.drop(columns=[f"{column}_acs"])
        public["pct_age_65_plus"] = public["age_65_plus_pct"].combine_first(public["pct_age_65_plus"])
        public["data_year"] = public["acs_source_year"].apply(
            lambda value: _extract_year(value, int(public["data_year"].max()))
        )
    else:
        public["acs_source_year"] = "sample fallback"
        public["disability_pct"] = np.nan
        public["transportation_access_proxy"] = np.nan
        public["internet_access_gap_pct"] = np.nan

    if "CDC PLACES" in frames:
        cdc = frames["CDC PLACES"].copy()
        public = public.merge(
            cdc[
                [
                    "county_fips",
                    "poor_or_fair_health_pct",
                    "diabetes_pct",
                    "high_blood_pressure_pct",
                    "obesity_pct",
                    "smoking_pct",
                    "frequent_physical_distress_pct",
                    "routine_checkup_pct",
                    "places_uninsured_pct",
                ]
            ].rename(
                columns={
                    "poor_or_fair_health_pct": "poor_or_fair_health_pct_cdc",
                    "diabetes_pct": "diabetes_pct_cdc",
                    "obesity_pct": "obesity_pct_cdc",
                }
            ),
            on="county_fips",
            how="left",
        )
        public["poor_or_fair_health_pct"] = public["poor_or_fair_health_pct_cdc"].combine_first(
            public["poor_or_fair_health_pct"]
        )
        public["diabetes_pct"] = public["diabetes_pct_cdc"].combine_first(public["diabetes_pct"])
        public["obesity_pct"] = public["obesity_pct_cdc"].combine_first(public["obesity_pct"])
        public["hypertension_pct"] = public["high_blood_pressure_pct"].combine_first(
            public["hypertension_pct"]
        )
        public = public.drop(
            columns=["poor_or_fair_health_pct_cdc", "diabetes_pct_cdc", "obesity_pct_cdc"]
        )
    else:
        public["smoking_pct"] = np.nan
        public["frequent_physical_distress_pct"] = np.nan
        public["routine_checkup_pct"] = np.nan
        public["places_uninsured_pct"] = np.nan

    if "HRSA HPSA" in frames:
        hrsa = frames["HRSA HPSA"].copy()
        hrsa = hrsa.rename(columns={"date_accessed": "hrsa_date_accessed"})
        public = public.merge(hrsa.drop(columns=["county_name"], errors="ignore"), on="county_fips", how="left")
        for column in ["hpsa_primary_care_score", "hpsa_mental_health_score"]:
            public[column] = public[f"{column}_y"].combine_first(public[f"{column}_x"])
            public = public.drop(columns=[f"{column}_x", f"{column}_y"])
    else:
        for column in [
            "hpsa_primary_care_count",
            "hpsa_primary_care_designated",
            "hpsa_mental_health_count",
            "hpsa_mental_health_designated",
            "hpsa_dental_count",
            "hpsa_dental_score",
            "hpsa_dental_designated",
        ]:
            public[column] = np.nan

    if "CMS Hospital Quality" in frames:
        cms = frames["CMS Hospital Quality"].copy()
        cms = cms.rename(columns={"date_accessed": "cms_date_accessed"})
        public = public.merge(cms.drop(columns=["county_name"], errors="ignore"), on="county_fips", how="left")
        for column in ["acute_care_hospitals", "avg_hospital_star_rating"]:
            public[column] = public[f"{column}_y"].where(
                public[f"{column}_y"].notna(), public[f"{column}_x"]
            )
            public = public.drop(columns=[f"{column}_x", f"{column}_y"])
    else:
        for column in [
            "hospital_count",
            "emergency_services_count",
            "readmission_worse_measure_count",
        ]:
            public[column] = np.nan

    for source_name, column_name in [
        ("ACS", "source_acs"),
        ("CDC PLACES", "source_cdc_places"),
        ("HRSA HPSA", "source_hrsa_hpsa"),
        ("CMS Hospital Quality", "source_cms_hospital_quality"),
    ]:
        public[column_name] = _source_status(frames, source_name)

    if {"ACS", "CDC PLACES"}.issubset(frames):
        data_mode = "mixed_real_and_demo_data"
    else:
        data_mode = "demo_sample_data"
        if "ACS" not in sources_using_fallback:
            sources_using_fallback.append("ACS-derived fields")
        if "CDC PLACES" not in sources_using_fallback:
            sources_using_fallback.append("CDC-derived fields")

    source_fallback_fields = [
        "region",
        "rural_flag",
        "pct_nonwhite",
        "primary_care_physicians_per_100k",
        "mental_health_providers_per_100k",
        "dental_providers_per_100k",
        "hospital_beds_per_1000",
        "readmission_rate_pct",
        "preventable_hospital_stays_per_100k",
        "life_expectancy",
    ]
    public["data_mode"] = data_mode
    public["fallback_fields_note"] = "; ".join(source_fallback_fields)

    metadata = {
        "project": "Maryland Healthcare Access Analytics",
        "data_mode": data_mode,
        "run_timestamp": utc_now_iso(),
        "data_access_dates": {
            source: details.get("date_accessed") for source, details in source_metadata.items()
        },
        "sources_successfully_loaded": sources_loaded,
        "sources_using_fallback": sources_using_fallback + ["sample reference fields"],
        "source_metadata": source_metadata,
        "source_fallback_fields": source_fallback_fields,
        "maryland_jurisdictions_represented": int(public["county_fips"].nunique()),
        "all_24_jurisdictions_present": set(public["county_fips"]) == MARYLAND_COUNTY_FIPS,
        "notes": (
            "Default mode attempts real ACS and CDC PLACES data first. HRSA/CMS are integrated "
            "when available. A documented sample file fills fields not provided by those feeds."
        ),
    }
    return public, metadata


def build_public_or_fallback_dataset(refresh_public: bool = False) -> tuple[pd.DataFrame, dict]:
    sample = load_raw_data(RAW_DATA_PATH)
    frames, source_metadata = _fetch_sources(refresh_public=refresh_public)
    public, metadata = _assemble_public_feature_base(sample, frames, source_metadata)
    return public, metadata


def _fill_optional_numeric(featured: pd.DataFrame, column: str) -> None:
    if column not in featured.columns:
        featured[column] = np.nan
    featured[column] = pd.to_numeric(featured[column], errors="coerce")
    if featured[column].isna().all():
        featured[column] = 0.0
    else:
        featured[column] = featured[column].fillna(featured[column].median())


def add_feature_indices(df: pd.DataFrame) -> pd.DataFrame:
    featured = df.copy()
    optional_columns = [
        "disability_pct",
        "transportation_access_proxy",
        "internet_access_gap_pct",
        "smoking_pct",
        "frequent_physical_distress_pct",
        "routine_checkup_pct",
        "places_uninsured_pct",
        "hpsa_primary_care_count",
        "hpsa_primary_care_designated",
        "hpsa_mental_health_count",
        "hpsa_mental_health_designated",
        "hpsa_dental_count",
        "hpsa_dental_score",
        "hpsa_dental_designated",
        "hospital_count",
        "emergency_services_count",
        "readmission_worse_measure_count",
    ]
    for column in optional_columns:
        _fill_optional_numeric(featured, column)

    featured["age_65_plus_pct"] = featured["pct_age_65_plus"]
    featured["high_blood_pressure_pct"] = featured["hypertension_pct"]
    featured["hospital_count_per_100k"] = (
        featured["hospital_count"] / featured["population"].replace(0, np.nan) * 100000
    ).fillna(0)
    featured["emergency_services_per_100k"] = (
        featured["emergency_services_count"] / featured["population"].replace(0, np.nan) * 100000
    ).fillna(0)

    featured["primary_care_gap"] = min_max_scale(
        featured["primary_care_physicians_per_100k"], invert=True
    )
    featured["mental_health_gap"] = min_max_scale(
        featured["mental_health_providers_per_100k"], invert=True
    )
    featured["dental_gap"] = min_max_scale(featured["dental_providers_per_100k"], invert=True)
    featured["hpsa_primary_need"] = min_max_scale(featured["hpsa_primary_care_score"])
    featured["hpsa_mental_need"] = min_max_scale(featured["hpsa_mental_health_score"])
    featured["hpsa_dental_need"] = min_max_scale(featured["hpsa_dental_score"])
    featured["hpsa_designation_burden"] = min_max_scale(
        featured[
            [
                "hpsa_primary_care_designated",
                "hpsa_mental_health_designated",
                "hpsa_dental_designated",
            ]
        ].sum(axis=1)
    )

    featured["provider_gap_index"] = (
        featured["hpsa_primary_need"] * 0.25
        + featured["hpsa_mental_need"] * 0.20
        + featured["hpsa_dental_need"] * 0.15
        + featured["hpsa_designation_burden"] * 0.15
        + featured["primary_care_gap"] * 0.10
        + featured["mental_health_gap"] * 0.10
        + featured["dental_gap"] * 0.05
    )
    featured["provider_shortage_burden_index"] = featured["provider_gap_index"]
    featured["provider_access_index"] = 100 - featured["provider_gap_index"]

    featured["socioeconomic_need_index"] = (
        min_max_scale(featured["poverty_pct"]) * 0.40
        + min_max_scale(featured["median_household_income"], invert=True) * 0.25
        + min_max_scale(featured["pct_age_65_plus"]) * 0.15
        + min_max_scale(featured["disability_pct"]) * 0.20
    )

    featured["insurance_access_burden_index"] = (
        min_max_scale(featured["uninsured_pct"]) * 0.55
        + min_max_scale(featured["transportation_access_proxy"]) * 0.25
        + min_max_scale(featured["internet_access_gap_pct"]) * 0.20
    )

    featured["chronic_burden_index"] = (
        min_max_scale(featured["diabetes_pct"]) * 0.20
        + min_max_scale(featured["obesity_pct"]) * 0.18
        + min_max_scale(featured["hypertension_pct"]) * 0.18
        + min_max_scale(featured["poor_or_fair_health_pct"]) * 0.24
        + min_max_scale(featured["smoking_pct"]) * 0.10
        + min_max_scale(featured["frequent_physical_distress_pct"]) * 0.10
    )

    featured["hospital_quality_gap_index"] = (
        min_max_scale(featured["avg_hospital_star_rating"], invert=True) * 0.35
        + min_max_scale(featured["hospital_count_per_100k"], invert=True) * 0.25
        + min_max_scale(featured["emergency_services_per_100k"], invert=True) * 0.20
        + min_max_scale(featured["hospital_beds_per_1000"], invert=True) * 0.10
        + min_max_scale(featured["readmission_worse_measure_count"]) * 0.10
    )
    featured["hospital_availability_quality_burden_index"] = featured["hospital_quality_gap_index"]

    featured["access_risk_score"] = (
        featured["socioeconomic_need_index"] * 0.25
        + featured["insurance_access_burden_index"] * 0.20
        + featured["chronic_burden_index"] * 0.25
        + featured["provider_gap_index"] * 0.20
        + featured["hospital_quality_gap_index"] * 0.10
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
            "disability_pct",
            "transportation_access_proxy",
            "internet_access_gap_pct",
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
            "smoking_pct",
            "frequent_physical_distress_pct",
            "routine_checkup_pct",
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
            "hpsa_primary_care_count",
            "hpsa_mental_health_score",
            "hpsa_mental_health_count",
            "hpsa_dental_score",
            "hpsa_dental_count",
            "provider_access_index",
        ]
    ].copy()

    hospital_quality = featured[
        [
            "county_fips",
            "data_year",
            "hospital_count",
            "acute_care_hospitals",
            "emergency_services_count",
            "hospital_beds_per_1000",
            "avg_hospital_star_rating",
            "readmission_rate_pct",
            "readmission_worse_measure_count",
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
            "insurance_access_burden_index",
            "provider_gap_index",
            "chronic_burden_index",
            "hospital_quality_gap_index",
            "top_risk_factor",
        ]
    ].copy()

    source_status = featured[
        [
            "county_fips",
            "data_year",
            "data_mode",
            "source_acs",
            "source_cdc_places",
            "source_hrsa_hpsa",
            "source_cms_hospital_quality",
            "fallback_fields_note",
        ]
    ].copy()

    final_feature_table = featured.copy()

    return {
        "counties": counties,
        "demographics": demographics,
        "health_outcomes": health_outcomes,
        "provider_shortages": provider_shortages,
        "hospital_quality": hospital_quality,
        "access_risk_scores": access_risk_scores,
        "source_status": source_status,
        "final_feature_table": final_feature_table,
    }


def write_sqlite_database(tables: dict[str, pd.DataFrame], database_path: Path = DATABASE_PATH) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.executescript(schema_sql)
            for table_name, table_df in tables.items():
                table_df.to_sql(table_name, connection, if_exists="append", index=False)


def write_processed_outputs(
    featured: pd.DataFrame,
    metadata: dict,
    output_dir: Path = PROCESSED_DIR,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    featured.to_csv(output_dir / "dashboard_county_risk.csv", index=False)
    featured.to_csv(output_dir / "healthcare_access_features.csv", index=False)
    featured.to_csv(output_dir / "md_county_health_access_scores.csv", index=False)

    model_features = featured[
        [
            "county_fips",
            "county_name",
            "data_mode",
            "poverty_pct",
            "median_household_income",
            "uninsured_pct",
            "pct_age_65_plus",
            "disability_pct",
            "transportation_access_proxy",
            "internet_access_gap_pct",
            "primary_care_physicians_per_100k",
            "mental_health_providers_per_100k",
            "dental_providers_per_100k",
            "hpsa_primary_care_score",
            "hpsa_primary_care_count",
            "hpsa_primary_care_designated",
            "hpsa_mental_health_score",
            "hpsa_mental_health_count",
            "hpsa_mental_health_designated",
            "hpsa_dental_score",
            "hpsa_dental_count",
            "hpsa_dental_designated",
            "hospital_count",
            "acute_care_hospitals",
            "emergency_services_count",
            "avg_hospital_star_rating",
            "hospital_count_per_100k",
            "diabetes_pct",
            "obesity_pct",
            "hypertension_pct",
            "poor_or_fair_health_pct",
            "smoking_pct",
            "frequent_physical_distress_pct",
            "routine_checkup_pct",
            "provider_gap_index",
            "socioeconomic_need_index",
            "insurance_access_burden_index",
            "chronic_burden_index",
            "hospital_quality_gap_index",
            "access_risk_score",
            "high_access_risk",
            "top_risk_factor",
            "source_acs",
            "source_cdc_places",
            "source_hrsa_hpsa",
            "source_cms_hospital_quality",
        ]
    ].copy()
    model_features.to_csv(output_dir / "model_feature_table.csv", index=False)

    state_average = featured.select_dtypes(include=[np.number]).mean(numeric_only=True).to_frame(
        "maryland_average"
    )
    state_average.to_csv(output_dir / "state_average.csv", index_label="metric")
    RUN_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _demo_metadata(featured: pd.DataFrame) -> dict:
    return {
        "project": "Maryland Healthcare Access Analytics",
        "data_mode": "demo_sample_data",
        "run_timestamp": utc_now_iso(),
        "data_access_dates": {},
        "sources_successfully_loaded": [],
        "sources_using_fallback": ["bundled sample data"],
        "maryland_jurisdictions_represented": int(featured["county_fips"].nunique()),
        "all_24_jurisdictions_present": set(featured["county_fips"]) == MARYLAND_COUNTY_FIPS,
        "notes": "Pipeline was run in explicit demo/sample mode.",
    }


def run_pipeline(
    raw_path: Path = RAW_DATA_PATH,
    refresh_public: bool = False,
    demo_sample: bool = False,
) -> pd.DataFrame:
    if demo_sample or raw_path != RAW_DATA_PATH:
        raw = load_raw_data(raw_path)
        metadata_base = None
    else:
        raw, metadata_base = build_public_or_fallback_dataset(refresh_public=refresh_public)

    cleaned = clean_data(raw)
    featured = add_feature_indices(cleaned)
    metadata = metadata_base or _demo_metadata(featured)
    metadata["maryland_jurisdictions_represented"] = int(featured["county_fips"].nunique())
    metadata["all_24_jurisdictions_present"] = set(featured["county_fips"]) == MARYLAND_COUNTY_FIPS

    tables = build_table_frames(featured)
    write_sqlite_database(tables)
    write_processed_outputs(featured, metadata)
    return featured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-path",
        type=Path,
        default=RAW_DATA_PATH,
        help="Path to county-level raw CSV file. Non-default paths run sample/demo mode.",
    )
    parser.add_argument(
        "--refresh-public",
        action="store_true",
        help="Fetch public sources instead of using cached processed source extracts.",
    )
    parser.add_argument(
        "--demo-sample",
        action="store_true",
        help="Use the bundled sample file instead of attempting public data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    featured = run_pipeline(
        raw_path=args.raw_path,
        refresh_public=args.refresh_public,
        demo_sample=args.demo_sample,
    )
    metadata = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    top_counties = featured.nlargest(5, "access_risk_score")[
        ["county_name", "access_risk_score", "access_risk_tier", "top_risk_factor"]
    ]
    print("Pipeline completed.")
    print(f"Data mode: {metadata['data_mode']}")
    print(f"Processed rows: {len(featured)}")
    print(f"SQLite database: {DATABASE_PATH}")
    print("Top access-risk counties:")
    print(top_counties.to_string(index=False))


if __name__ == "__main__":
    main()
