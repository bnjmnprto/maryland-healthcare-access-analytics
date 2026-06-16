"""Build a raw Maryland county file from public sources where feasible.

The default project pipeline uses the bundled sample file so tests and demos are
stable without network access. This module provides an optional live-data path
that pulls public county-level indicators from CDC PLACES, HRSA HPSA downloads,
and CMS Provider Data, then fills fields not available from those feeds with the
documented sample fallback values.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.data_pipeline import RAW_DATA_PATH, REQUIRED_COLUMNS  # noqa: E402

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PUBLIC_RAW_PATH = RAW_DIR / "maryland_county_health_access_public.csv"
PROVENANCE_PATH = RAW_DIR / "public_data_provenance.json"

CDC_PLACES_URL = "https://data.cdc.gov/resource/i46a-9kgh.json?%24limit=5000&stateabbr=MD"
HRSA_PRIMARY_CARE_URL = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
HRSA_MENTAL_HEALTH_URL = "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_MH.csv"
CMS_HOSPITAL_URL = (
    "https://data.cms.gov/provider-data/api/1/datastore/query/"
    "xubh-q36u/0?limit=1000&offset={offset}"
)

PUBLIC_SOURCES = {
    "CDC PLACES county release": "https://data.cdc.gov/resource/i46a-9kgh",
    "HRSA Primary Care HPSA download": HRSA_PRIMARY_CARE_URL,
    "HRSA Mental Health HPSA download": HRSA_MENTAL_HEALTH_URL,
    "CMS Hospital General Information": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
}

PUBLIC_COLUMN_SOURCES = {
    "population": "CDC PLACES total population",
    "uninsured_pct": "CDC PLACES ACCESS2 crude prevalence",
    "diabetes_pct": "CDC PLACES diabetes crude prevalence",
    "obesity_pct": "CDC PLACES obesity crude prevalence",
    "hypertension_pct": "CDC PLACES high blood pressure crude prevalence",
    "poor_or_fair_health_pct": "CDC PLACES poor/fair or physical-health proxy when available",
    "hpsa_primary_care_score": "HRSA Primary Care HPSA maximum score by county",
    "hpsa_mental_health_score": "HRSA Mental Health HPSA maximum score by county",
    "acute_care_hospitals": "CMS Hospital General Information facility count",
    "avg_hospital_star_rating": "CMS Hospital General Information average rating",
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "maryland-healthcare-access-analytics/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read().decode("utf-8-sig", "replace")
    except (urllib.error.URLError, ssl.SSLError) as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=90, context=context) as response:
            return response.read().decode("utf-8-sig", "replace")


def as_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"not available", "not applicable", "nan"}:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def county_key(value: str) -> str:
    text = value.lower().replace("&", "and").replace("st.", "st")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\bcounty\b|\bmd\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_sample_reference(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"county_fips": str})


def load_cdc_places() -> dict[str, dict[str, object]]:
    records = json.loads(fetch_text(CDC_PLACES_URL))
    return {str(row["countyfips"]).zfill(5): row for row in records}


def summarize_hrsa(url: str) -> dict[str, dict[str, float]]:
    text = fetch_text(url)
    reader = csv.DictReader(io.StringIO(text))
    seen: set[tuple[str, str]] = set()
    summary: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "max_score": 0.0, "score_total": 0.0}
    )
    for row in reader:
        if row.get("HPSA Status") != "Designated":
            continue
        fips = (
            row.get("Common State County FIPS Code")
            or row.get("State and County Federal Information Processing Standard Code")
            or ""
        ).strip()
        if not fips.startswith("24"):
            continue
        hpsa_id = (row.get("HPSA ID") or row.get("HPSA Name") or "").strip()
        key = (hpsa_id, fips)
        if key in seen:
            continue
        seen.add(key)
        score = as_float(row.get("HPSA Score")) or 0.0
        summary[fips]["count"] += 1.0
        summary[fips]["score_total"] += score
        summary[fips]["max_score"] = max(summary[fips]["max_score"], score)
    return summary


def load_cms_hospitals(sample: pd.DataFrame) -> dict[str, dict[str, float]]:
    lookup = {
        county_key(row["county_name"]): row["county_fips"]
        for _, row in sample[["county_name", "county_fips"]].iterrows()
    }
    hospitals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "rating_total": 0.0, "rating_count": 0.0}
    )
    offset = 0
    expected_count = None
    while True:
        data = json.loads(fetch_text(CMS_HOSPITAL_URL.format(offset=offset)))
        rows = data.get("results", [])
        if expected_count is None:
            expected_count = data.get("count", 0)
        if not rows:
            break
        for row in rows:
            if row.get("state") != "MD":
                continue
            fips = lookup.get(county_key(row.get("countyparish", "")))
            if not fips:
                continue
            rating = as_float(row.get("hospital_overall_rating"))
            hospitals[fips]["count"] += 1.0
            if rating is not None:
                hospitals[fips]["rating_total"] += rating
                hospitals[fips]["rating_count"] += 1.0
        offset += len(rows)
        if expected_count and offset >= expected_count:
            break
    return hospitals


def first_available(row: dict[str, object], keys: list[str]) -> float | None:
    for key in keys:
        value = as_float(row.get(key))
        if value is not None:
            return value
    return None


def apply_live_public_fields(sample: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    public = sample.copy()
    public["county_fips"] = public["county_fips"].astype(str).str.zfill(5)
    column_order = [column for column in public.columns if column in REQUIRED_COLUMNS]

    cdc = load_cdc_places()
    primary = summarize_hrsa(HRSA_PRIMARY_CARE_URL)
    mental = summarize_hrsa(HRSA_MENTAL_HEALTH_URL)
    hospitals = load_cms_hospitals(public)

    columns_filled_from_public: set[str] = set()
    for index, row in public.iterrows():
        fips = str(row["county_fips"]).zfill(5)
        cdc_row = cdc.get(fips, {})
        if cdc_row:
            mapping = {
                "population": first_available(cdc_row, ["totalpopulation"]),
                "uninsured_pct": first_available(cdc_row, ["access2_crudeprev"]),
                "diabetes_pct": first_available(cdc_row, ["diabetes_crudeprev"]),
                "obesity_pct": first_available(cdc_row, ["obesity_crudeprev"]),
                "hypertension_pct": first_available(cdc_row, ["bphigh_crudeprev"]),
                "poor_or_fair_health_pct": first_available(
                    cdc_row, ["ghlth_crudeprev", "phlth_crudeprev"]
                ),
            }
            for column, value in mapping.items():
                if value is not None:
                    public.at[index, column] = value
                    columns_filled_from_public.add(column)

        if fips in primary:
            public.at[index, "hpsa_primary_care_score"] = primary[fips]["max_score"]
            columns_filled_from_public.add("hpsa_primary_care_score")
        if fips in mental:
            public.at[index, "hpsa_mental_health_score"] = mental[fips]["max_score"]
            columns_filled_from_public.add("hpsa_mental_health_score")
        if fips in hospitals:
            hospital_summary = hospitals[fips]
            public.at[index, "acute_care_hospitals"] = hospital_summary["count"]
            columns_filled_from_public.add("acute_care_hospitals")
            rating_count = hospital_summary["rating_count"]
            if rating_count:
                public.at[index, "avg_hospital_star_rating"] = (
                    hospital_summary["rating_total"] / rating_count
                )
                columns_filled_from_public.add("avg_hospital_star_rating")

    public["data_year"] = dt.date.today().year
    public = public[column_order]
    provenance = build_provenance(public, columns_filled_from_public, "live_public_with_sample_fallback")
    return public, provenance


def build_provenance(
    df: pd.DataFrame, columns_filled_from_public: set[str], mode: str, error: str | None = None
) -> dict:
    field_sources = {}
    for column in df.columns:
        if column in columns_filled_from_public:
            field_sources[column] = {
                "source": PUBLIC_COLUMN_SOURCES.get(column, "Official public source"),
                "fallback_used": False,
            }
        else:
            field_sources[column] = {
                "source": "Bundled sample fallback",
                "fallback_used": True,
            }
    return {
        "project": "Maryland Healthcare Access Analytics",
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "mode": mode,
        "public_sources": PUBLIC_SOURCES,
        "row_count": int(len(df)),
        "field_sources": field_sources,
        "error": error,
        "responsible_use_note": (
            "This file contains aggregate county-level indicators only. It is not patient-level "
            "data and is not validated for clinical decision-making."
        ),
    }


def write_outputs(df: pd.DataFrame, provenance: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    provenance_path = output_path.parent / "public_data_provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")


def build_sample_fallback(error: str | None = None) -> tuple[pd.DataFrame, dict]:
    sample = load_sample_reference()
    provenance = build_provenance(sample, set(), "sample_fallback", error)
    return sample, provenance


def build_public_dataset(allow_sample_fallback: bool = True) -> tuple[pd.DataFrame, dict]:
    sample = load_sample_reference()
    try:
        return apply_live_public_fields(sample)
    except Exception as exc:
        if not allow_sample_fallback:
            raise
        return build_sample_fallback(str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PUBLIC_RAW_PATH)
    parser.add_argument(
        "--strict-live",
        action="store_true",
        help="Fail if live public sources cannot be fetched instead of writing sample fallback.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df, provenance = build_public_dataset(allow_sample_fallback=not args.strict_live)
    write_outputs(df, provenance, args.output)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.output.parent / 'public_data_provenance.json'}")
    print(f"Mode: {provenance['mode']}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()
