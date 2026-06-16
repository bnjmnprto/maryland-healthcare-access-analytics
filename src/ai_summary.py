"""Plain-English county summaries with optional future LLM integration."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DASHBOARD_DATA_PATH = PROCESSED_DIR / "dashboard_county_risk.csv"
SUMMARY_PATH = PROCESSED_DIR / "county_ai_summaries.csv"


DRIVER_LABELS = {
    "provider_gap_index": "provider access constraints",
    "socioeconomic_need_index": "socioeconomic need",
    "insurance_access_burden_index": "insurance and transportation access barriers",
    "chronic_burden_index": "chronic disease burden",
    "hospital_quality_gap_index": "hospital quality and capacity gaps",
}


def load_dashboard_data(path: Path = DASHBOARD_DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dashboard data not found at {path}. Run `python src/data_pipeline.py` first."
        )
    return pd.read_csv(path, dtype={"county_fips": str})


def _format_delta(value: float, unit: str = "points") -> str:
    direction = "above" if value >= 0 else "below"
    return f"{abs(value):.1f} {unit} {direction}"


def identify_top_drivers(row: pd.Series, count: int = 2) -> list[str]:
    driver_columns = list(DRIVER_LABELS)
    ranked = row[driver_columns].sort_values(ascending=False)
    return [DRIVER_LABELS[column] for column in ranked.head(count).index]


def generate_template_summary(row: pd.Series, state_average: pd.Series) -> str:
    drivers = identify_top_drivers(row)
    risk_delta = row["access_risk_score"] - state_average["access_risk_score"]
    poverty_delta = row["poverty_pct"] - state_average["poverty_pct"]
    uninsured_delta = row["uninsured_pct"] - state_average["uninsured_pct"]
    diabetes_delta = row["diabetes_pct"] - state_average["diabetes_pct"]
    data_mode = str(row.get("data_mode", "unknown data mode")).replace("_", " ")

    return (
        f"{row['county_name']} is classified as {row['access_risk_tier'].lower()} access risk "
        f"with a score of {row['access_risk_score']:.1f}, which is "
        f"{_format_delta(risk_delta, 'risk-score points')} the Maryland county average. "
        f"This run is in {data_mode} mode. The leading risk drivers are {drivers[0]} and {drivers[1]}. "
        f"Poverty is {_format_delta(poverty_delta)} the county average, uninsured rate is "
        f"{_format_delta(uninsured_delta)}, and diabetes prevalence is "
        f"{_format_delta(diabetes_delta)}. This summary is intended to support prioritization "
        f"and should be reviewed alongside local context, community input, and updated source data. "
        f"It is not medical advice or a basis for individual eligibility decisions."
    )


def generate_openai_summary_placeholder(row: pd.Series) -> str:
    """Optional extension point for teams that later add paid API access.

    Default project behavior does not require an API key. To integrate OpenAI later,
    install the OpenAI SDK, set OPENAI_API_KEY, and replace this placeholder with a
    client call that sends only aggregate county-level metrics.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return ""

    return (
        "OPENAI_API_KEY detected, but live LLM summarization is intentionally disabled in "
        "the portfolio template. Replace generate_openai_summary_placeholder() with your "
        "organization-approved OpenAI client call when needed."
    )


def summarize_all_counties(df: pd.DataFrame) -> pd.DataFrame:
    state_average = df.select_dtypes(include="number").mean(numeric_only=True)
    summaries = df[["county_fips", "county_name", "access_risk_tier", "access_risk_score"]].copy()
    summaries["plain_english_summary"] = df.apply(
        lambda row: generate_template_summary(row, state_average), axis=1
    )

    if os.getenv("USE_OPENAI_SUMMARY", "false").lower() == "true":
        summaries["optional_openai_placeholder"] = df.apply(generate_openai_summary_placeholder, axis=1)

    return summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-data", type=Path, default=DASHBOARD_DATA_PATH)
    parser.add_argument("--output", type=Path, default=SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_dashboard_data(args.dashboard_data)
    summaries = summarize_all_counties(df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summaries.to_csv(args.output, index=False)
    print(f"Generated {len(summaries)} county summaries: {args.output}")


if __name__ == "__main__":
    main()
