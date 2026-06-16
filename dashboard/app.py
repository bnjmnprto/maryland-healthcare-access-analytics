"""Streamlit dashboard for Maryland Healthcare Access Analytics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ai_summary import generate_template_summary  # noqa: E402


DATA_PATH = PROJECT_ROOT / "data" / "processed" / "dashboard_county_risk.csv"
METRICS_PATH = PROJECT_ROOT / "data" / "processed" / "model_metrics.json"
IMPORTANCE_PATH = PROJECT_ROOT / "data" / "processed" / "feature_importance.csv"
RUN_METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "run_metadata.json"
DATA_QUALITY_REPORT_PATH = PROJECT_ROOT / "reports" / "data_quality_report.md"
GEOJSON_PATH = PROJECT_ROOT / "data" / "raw" / "maryland_counties.geojson"


RISK_DRIVER_COLUMNS = [
    "socioeconomic_need_index",
    "insurance_access_burden_index",
    "chronic_burden_index",
    "provider_gap_index",
    "hospital_quality_gap_index",
]


st.set_page_config(
    page_title="Maryland Healthcare Access Analytics",
    page_icon="MD",
    layout="wide",
)


@st.cache_data
def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error("Processed dashboard data was not found. Run `python src/data_pipeline.py` first.")
        st.stop()
    return pd.read_csv(DATA_PATH, dtype={"county_fips": str})


@st.cache_data
def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_feature_importance() -> pd.DataFrame:
    if IMPORTANCE_PATH.exists():
        return pd.read_csv(IMPORTANCE_PATH)
    return pd.DataFrame()


@st.cache_data
def load_county_geojson() -> dict | None:
    if not GEOJSON_PATH.exists():
        return None
    try:
        geojson = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for feature in geojson.get("features", []):
        properties = feature.setdefault("properties", {})
        county_fip = str(properties.get("county_fip", "")).strip().zfill(3)
        if county_fip == "510":
            county_fips_full = "24510"
        elif county_fip:
            county_fips_full = f"24{county_fip}"
        else:
            county_fips_full = ""
        properties["county_fips_full"] = county_fips_full
    return geojson


def metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label=label, value=value, help=help_text)


def risk_color_scale() -> list[str]:
    return ["#1f8a70", "#bedc5a", "#f4a261", "#c1121f"]


def display_data_mode(mode: str) -> str:
    labels = {
        "real_public_data": "Real public data",
        "mixed_real_and_demo_data": "Mixed real + fallback",
        "demo_sample_data": "Demo fallback",
    }
    return labels.get(mode, mode.replace("_", " ").title() if mode else "Unknown")


def compact_data_mode(mode: str) -> str:
    labels = {
        "real_public_data": "Real",
        "mixed_real_and_demo_data": "Mixed",
        "demo_sample_data": "Demo",
    }
    return labels.get(mode, "Unknown")


def render_map(data: pd.DataFrame, county_geojson: dict | None) -> None:
    if county_geojson:
        map_fig = px.choropleth_map(
            data,
            geojson=county_geojson,
            locations="county_fips",
            featureidkey="properties.county_fips_full",
            color="access_risk_score",
            color_continuous_scale="YlOrRd",
            range_color=(0, 100),
            map_style="carto-positron",
            center={"lat": 39.0, "lon": -76.7},
            zoom=6.2,
            opacity=0.72,
            hover_name="county_name",
            hover_data={
                "county_fips": False,
                "access_risk_score": ":.1f",
                "access_risk_tier": True,
                "top_risk_factor": True,
            },
            labels={
                "access_risk_score": "Risk score",
                "access_risk_tier": "Risk category",
                "top_risk_factor": "Top risk factor",
            },
            title="Maryland county access risk score",
        )
        map_fig.update_layout(height=620, margin={"r": 0, "t": 48, "l": 0, "b": 0})
        st.plotly_chart(map_fig, width="stretch")
        return

    st.info("County GeoJSON could not be loaded, so the dashboard is showing the ranking table.")
    st.dataframe(
        data.sort_values("access_risk_score", ascending=False)[
            ["county_name", "access_risk_score", "access_risk_tier", "top_risk_factor"]
        ],
        width="stretch",
        hide_index=True,
    )


df = load_data()
metrics = load_json(METRICS_PATH)
run_metadata = load_json(RUN_METADATA_PATH)
feature_importance = load_feature_importance()
county_geojson = load_county_geojson()
state_average = df.select_dtypes(include="number").mean(numeric_only=True)

st.title("Maryland Healthcare Access Analytics")
st.caption(
    "Public-health analytics project using Python, SQL, SQLite, scikit-learn, Streamlit, and public county-level datasets to identify Maryland jurisdictions at elevated healthcare access risk."
)

regions = ["All regions"] + sorted(df["region"].unique())
selected_region = st.sidebar.selectbox("Region", regions)
risk_tiers = st.sidebar.multiselect(
    "Risk tier",
    options=["High", "Elevated", "Moderate", "Low"],
    default=["High", "Elevated", "Moderate", "Low"],
)

filtered = df.copy()
if selected_region != "All regions":
    filtered = filtered[filtered["region"] == selected_region]
if risk_tiers:
    filtered = filtered[filtered["access_risk_tier"].isin(risk_tiers)]

(
    overview_tab,
    ranking_tab,
    comparison_tab,
    map_tab,
    model_tab,
    summary_tab,
    data_quality_tab,
    limitations_tab,
) = st.tabs(
    [
        "Overview",
        "Risk Ranking",
        "County Comparison",
        "Map",
        "Model Results",
        "County Summary",
        "Data Sources / Data Quality",
        "Responsible Use",
    ]
)

with overview_tab:
    left, middle, right, far_right = st.columns(4)
    with left:
        metric_card("Jurisdictions", f"{len(df):,}")
    with middle:
        metric_card("Average risk score", f"{df['access_risk_score'].mean():.1f}")
    with right:
        metric_card("High-tier counties", f"{int((df['access_risk_tier'] == 'High').sum()):,}")
    with far_right:
        metric_card("Highest score", f"{df['access_risk_score'].max():.1f}")

    st.subheader("Current Data Run")
    meta_left, meta_mid, meta_right = st.columns(3)
    with meta_left:
        st.metric("Data mode", compact_data_mode(run_metadata.get("data_mode", "unknown")))
    with meta_mid:
        st.metric("Jurisdictions represented", run_metadata.get("maryland_jurisdictions_represented", len(df)))
    with meta_right:
        st.metric("All 24 present", "Yes" if run_metadata.get("all_24_jurisdictions_present") else "Review")

    st.write(
        f"Data mode detail: {display_data_mode(run_metadata.get('data_mode', 'unknown'))} "
        f"(`{run_metadata.get('data_mode', 'unknown')}`)"
    )
    st.write(f"Run timestamp: `{run_metadata.get('run_timestamp', 'not recorded')}`")
    st.write(
        f"Sources loaded: {', '.join(run_metadata.get('sources_successfully_loaded', [])) or 'Not recorded'}"
    )
    st.write(
        f"Fallback sources/fields: {', '.join(run_metadata.get('sources_using_fallback', [])) or 'None recorded'}"
    )

    chart_left, chart_right = st.columns([1.25, 1])
    with chart_left:
        top_risk = filtered.sort_values("access_risk_score", ascending=False)
        fig = px.bar(
            top_risk,
            x="access_risk_score",
            y="county_name",
            orientation="h",
            color="access_risk_tier",
            color_discrete_sequence=risk_color_scale(),
            labels={"access_risk_score": "Access risk score", "county_name": ""},
            title="County access risk ranking",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=620)
        st.plotly_chart(fig, width="stretch")

    with chart_right:
        scatter = px.scatter(
            filtered,
            x="provider_access_index",
            y="chronic_burden_index",
            size="population",
            color="access_risk_tier",
            hover_name="county_name",
            color_discrete_sequence=risk_color_scale(),
            labels={
                "provider_access_index": "Provider access index",
                "chronic_burden_index": "Chronic burden index",
            },
            title="Provider access vs. chronic disease burden",
        )
        st.plotly_chart(scatter, width="stretch")

with ranking_tab:
    display_columns = [
        "county_name",
        "region",
        "access_risk_score",
        "access_risk_tier",
        "poverty_pct",
        "uninsured_pct",
        "provider_access_index",
        "chronic_burden_index",
        "top_risk_factor",
    ]
    st.dataframe(
        filtered.sort_values("access_risk_score", ascending=False)[display_columns],
        width="stretch",
        hide_index=True,
    )

    driver_fig = px.bar(
        filtered.sort_values("access_risk_score", ascending=False),
        x="county_name",
        y=RISK_DRIVER_COLUMNS,
        labels={"value": "Index score", "county_name": "County", "variable": "Driver"},
        title="Risk driver profile by county",
    )
    driver_fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(driver_fig, width="stretch")

with comparison_tab:
    county_options = sorted(df["county_name"].unique())
    default_second = "Somerset" if "Somerset" in county_options else county_options[-1]
    first_county, second_county = st.columns(2)
    with first_county:
        selected_first = st.selectbox("County A", county_options, index=0)
    with second_county:
        selected_second = st.selectbox(
            "County B", county_options, index=county_options.index(default_second)
        )

    comparison = df[df["county_name"].isin([selected_first, selected_second])]
    comparison_metrics = [
        "poverty_pct",
        "uninsured_pct",
        "diabetes_pct",
        "poor_or_fair_health_pct",
        "provider_gap_index",
        "access_risk_score",
    ]
    compare_fig = px.bar(
        comparison.melt(
            id_vars="county_name",
            value_vars=comparison_metrics,
            var_name="metric",
            value_name="value",
        ),
        x="metric",
        y="value",
        color="county_name",
        barmode="group",
        title="Selected county comparison",
    )
    compare_fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(compare_fig, width="stretch")

    outcome_fig = px.scatter(
        df,
        x="poverty_pct",
        y="poor_or_fair_health_pct",
        color="access_risk_tier",
        size="uninsured_pct",
        hover_name="county_name",
        color_discrete_sequence=risk_color_scale(),
        title="Poverty, uninsured rate, and poor/fair health",
    )
    st.plotly_chart(outcome_fig, width="stretch")

with map_tab:
    st.subheader("Maryland County Choropleth")
    render_map(filtered, county_geojson)

with model_tab:
    if not metrics:
        st.info("Model metrics are not available yet. Run `python src/risk_model.py`.")
    else:
        st.subheader(f"Selected model: {metrics['selected_model'].replace('_', ' ').title()}")
        st.caption(
            f"Target mode: {metrics.get('target_mode', 'unknown')} | "
            f"Target: {metrics.get('target_name', metrics.get('target', 'unknown'))}"
        )
        if metrics.get("target_description"):
            st.write(metrics["target_description"])
        selected_metrics = metrics["models"][metrics["selected_model"]]
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("Accuracy", f"{selected_metrics['accuracy']:.3f}")
        with m2:
            metric_card("Precision", f"{selected_metrics['precision']:.3f}")
        with m3:
            metric_card("Recall", f"{selected_metrics['recall']:.3f}")
        with m4:
            roc_auc = selected_metrics["roc_auc"]
            metric_card("ROC AUC", "N/A" if roc_auc is None else f"{roc_auc:.3f}")

        if metrics.get("warning"):
            st.warning(metrics["warning"])
        st.write(metrics["evaluation_note"])
        if metrics.get("evaluation_design", {}).get("cross_validation"):
            st.caption("Cross-validation summary")
            st.json(metrics["evaluation_design"]["cross_validation"])
        st.caption("Confusion matrix")
        st.json(selected_metrics["confusion_matrix"])

    if not feature_importance.empty:
        importance_fig = px.bar(
            feature_importance.head(10).sort_values("importance"),
            x="importance",
            y="feature",
            orientation="h",
            title="Top model features",
        )
        st.plotly_chart(importance_fig, width="stretch")

with summary_tab:
    county = st.selectbox("County", sorted(df["county_name"].unique()), key="summary_county")
    row = df[df["county_name"] == county].iloc[0]
    summary = generate_template_summary(row, state_average)
    st.info(summary)

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Risk score", f"{row['access_risk_score']:.1f}")
    with c2:
        metric_card("Provider access", f"{row['provider_access_index']:.1f}")
    with c3:
        metric_card("Chronic burden", f"{row['chronic_burden_index']:.1f}")

with data_quality_tab:
    st.subheader("Data Sources and Quality")
    st.write(
        f"Data mode: {display_data_mode(run_metadata.get('data_mode', 'unknown'))} "
        f"(`{run_metadata.get('data_mode', 'unknown')}`)"
    )
    st.write(f"Sources loaded: {', '.join(run_metadata.get('sources_successfully_loaded', []))}")
    st.write(f"Fallback sources/fields: {', '.join(run_metadata.get('sources_using_fallback', []))}")
    source_cols = [
        "county_name",
        "source_acs",
        "source_cdc_places",
        "source_hrsa_hpsa",
        "source_cms_hospital_quality",
        "fallback_fields_note",
    ]
    st.dataframe(df[source_cols], width="stretch", hide_index=True)
    if DATA_QUALITY_REPORT_PATH.exists():
        with st.expander("Data quality report excerpt"):
            st.markdown(DATA_QUALITY_REPORT_PATH.read_text(encoding="utf-8")[:5000])

with limitations_tab:
    st.subheader("Responsible-use notes")
    st.markdown(
        f"""
- Current data mode: `{run_metadata.get('data_mode', 'unknown')}`.
- The included data is a reproducible county-level analytics dataset with documented sample fallback fields, not an official public-health surveillance product.
- County-level analysis can hide neighborhood-level inequities and should not be used to make individual eligibility decisions.
- The risk score is a transparent prioritization heuristic, not a clinical diagnosis or causal model.
- Machine learning metrics are shown to demonstrate workflow literacy on a small sample; they should not be interpreted as deployment evidence.
- Perfect or near-perfect metrics can occur with small county-level datasets and should not be interpreted as validated predictive performance.
- Production use would require source-data refreshes, stakeholder review, uncertainty checks, and equity impact assessment.
"""
    )
