#!/usr/bin/env python3
"""Build a Maryland county health-access prioritization dashboard.

The project intentionally uses only the Python standard library so reviewers can
run it without dependency setup. It pulls public data from official CDC, HRSA,
and CMS endpoints, creates a transparent county scoring model, and writes both
processed data and a static HTML dashboard.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import io
import json
import math
import re
import ssl
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"

CDC_PLACES_URL = (
    "https://data.cdc.gov/resource/i46a-9kgh.json?%24limit=5000&stateabbr=MD"
)
HRSA_PRIMARY_CARE_URL = (
    "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
)
HRSA_MENTAL_HEALTH_URL = (
    "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_MH.csv"
)
CMS_HOSPITAL_URL = (
    "https://data.cms.gov/provider-data/api/1/datastore/query/"
    "xubh-q36u/0?limit=1000&offset={offset}"
)

SOURCES = {
    "CDC PLACES 2025": "https://data.cdc.gov/resource/i46a-9kgh",
    "HRSA HPSA Primary Care": HRSA_PRIMARY_CARE_URL,
    "HRSA HPSA Mental Health": HRSA_MENTAL_HEALTH_URL,
    "CMS Hospital General Information": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
}

HEALTH_FIELDS = [
    ("diabetes_crudeprev", "Diabetes"),
    ("obesity_crudeprev", "Obesity"),
    ("bphigh_crudeprev", "High blood pressure"),
    ("phlth_crudeprev", "Physical distress"),
    ("mhlth_crudeprev", "Mental distress"),
    ("depression_crudeprev", "Depression"),
]

SOCIAL_FIELDS = [
    ("access2_crudeprev", "Uninsured adults"),
    ("foodinsecu_crudeprev", "Food insecurity"),
    ("housinsecu_crudeprev", "Housing insecurity"),
    ("lacktrpt_crudeprev", "Transportation barrier"),
    ("shututility_crudeprev", "Utility insecurity"),
]

CSV_FIELDS = [
    "rank",
    "county_fips",
    "county",
    "population",
    "priority_score",
    "health_burden_score",
    "social_need_score",
    "access_gap_score",
    "uninsured_adults_pct",
    "food_insecurity_pct",
    "housing_insecurity_pct",
    "transportation_barrier_pct",
    "utility_insecurity_pct",
    "diabetes_pct",
    "obesity_pct",
    "high_blood_pressure_pct",
    "physical_distress_pct",
    "mental_distress_pct",
    "depression_pct",
    "primary_care_hpsa_count",
    "mental_health_hpsa_count",
    "max_hpsa_score",
    "hospital_count",
    "hospital_per_100k",
    "avg_hospital_rating",
]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "community-health-access-analytics/1.0"},
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


def as_int(value: object) -> int:
    number = as_float(value)
    return int(number) if number is not None else 0


def mean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def county_key(value: str) -> str:
    text = value.lower().replace("&", "and").replace("st.", "st")
    text = re.sub(r"[^a-z0-9 ]+", "", text)
    text = re.sub(r"\bcounty\b|\bmd\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def display_county(raw_name: str) -> str:
    name = raw_name.strip()
    if name.lower() == "baltimore city":
        return "Baltimore City"
    if name.lower().endswith("city"):
        return name.title()
    return f"{name} County"


def clean_csv_value(value: float | int | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def load_cdc_places() -> list[dict[str, object]]:
    rows = json.loads(fetch_text(CDC_PLACES_URL))
    counties: list[dict[str, object]] = []
    for row in rows:
        fips = row["countyfips"]
        county = "Baltimore City" if fips == "24510" else display_county(row["countyname"])
        record: dict[str, object] = {
            "county_fips": fips,
            "county": county,
            "county_key": county_key(county),
            "population": as_int(row.get("totalpopulation")),
        }
        for field, _ in HEALTH_FIELDS + SOCIAL_FIELDS:
            record[field] = as_float(row.get(field))
        counties.append(record)
    counties.sort(key=lambda item: str(item["county"]))
    return counties


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


def load_cms_hospitals(county_lookup: dict[str, str]) -> dict[str, dict[str, float]]:
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
            key = county_key(row.get("countyparish", ""))
            fips = county_lookup.get(key)
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


def minmax_scores(
    rows: list[dict[str, object]], field: str, invert: bool = False
) -> dict[str, float | None]:
    values = [as_float(row.get(field)) for row in rows]
    clean = [value for value in values if value is not None]
    if not clean:
        return {str(row["county_fips"]): None for row in rows}
    low = min(clean)
    high = max(clean)
    scores: dict[str, float | None] = {}
    for row in rows:
        fips = str(row["county_fips"])
        value = as_float(row.get(field))
        if value is None:
            scores[fips] = None
            continue
        score = 50.0 if math.isclose(high, low) else ((value - low) / (high - low)) * 100
        scores[fips] = 100 - score if invert else score
    return scores


def add_scores(rows: list[dict[str, object]]) -> None:
    health_norms = {
        field: minmax_scores(rows, field)
        for field, _ in HEALTH_FIELDS
    }
    social_norms = {
        field: minmax_scores(rows, field)
        for field, _ in SOCIAL_FIELDS
    }
    access_norms = {
        "primary_care_hpsa_per_100k": minmax_scores(rows, "primary_care_hpsa_per_100k"),
        "mental_health_hpsa_per_100k": minmax_scores(rows, "mental_health_hpsa_per_100k"),
        "max_hpsa_score": minmax_scores(rows, "max_hpsa_score"),
        "hospital_per_100k": minmax_scores(rows, "hospital_per_100k", invert=True),
        "hospital_rating_gap": minmax_scores(rows, "hospital_rating_gap"),
    }
    for row in rows:
        fips = str(row["county_fips"])
        row["health_burden_score"] = mean(
            [health_norms[field][fips] for field, _ in HEALTH_FIELDS]
        )
        row["social_need_score"] = mean(
            [social_norms[field][fips] for field, _ in SOCIAL_FIELDS]
        )
        row["access_gap_score"] = mean(
            [access_norms[field][fips] for field in access_norms]
        )
        row["priority_score"] = (
            0.40 * float(row["health_burden_score"] or 0)
            + 0.35 * float(row["social_need_score"] or 0)
            + 0.25 * float(row["access_gap_score"] or 0)
        )
    rows.sort(key=lambda item: float(item["priority_score"]), reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index


def build_dataset() -> list[dict[str, object]]:
    rows = load_cdc_places()
    county_lookup = {str(row["county_key"]): str(row["county_fips"]) for row in rows}
    primary = summarize_hrsa(HRSA_PRIMARY_CARE_URL)
    mental = summarize_hrsa(HRSA_MENTAL_HEALTH_URL)
    hospitals = load_cms_hospitals(county_lookup)

    for row in rows:
        fips = str(row["county_fips"])
        population = max(as_int(row["population"]), 1)
        primary_summary = primary.get(fips, {})
        mental_summary = mental.get(fips, {})
        hospital_summary = hospitals.get(fips, {})

        primary_count = primary_summary.get("count", 0.0)
        mental_count = mental_summary.get("count", 0.0)
        hospital_count = hospital_summary.get("count", 0.0)
        rating_count = hospital_summary.get("rating_count", 0.0)
        avg_rating = (
            hospital_summary["rating_total"] / rating_count if rating_count else None
        )

        row["primary_care_hpsa_count"] = primary_count
        row["mental_health_hpsa_count"] = mental_count
        row["primary_care_hpsa_per_100k"] = (primary_count / population) * 100000
        row["mental_health_hpsa_per_100k"] = (mental_count / population) * 100000
        row["max_hpsa_score"] = max(
            primary_summary.get("max_score", 0.0),
            mental_summary.get("max_score", 0.0),
        )
        row["hospital_count"] = hospital_count
        row["hospital_per_100k"] = (hospital_count / population) * 100000
        row["avg_hospital_rating"] = avg_rating
        row["hospital_rating_gap"] = 5 - avg_rating if avg_rating is not None else None

        row["uninsured_adults_pct"] = row.get("access2_crudeprev")
        row["food_insecurity_pct"] = row.get("foodinsecu_crudeprev")
        row["housing_insecurity_pct"] = row.get("housinsecu_crudeprev")
        row["transportation_barrier_pct"] = row.get("lacktrpt_crudeprev")
        row["utility_insecurity_pct"] = row.get("shututility_crudeprev")
        row["diabetes_pct"] = row.get("diabetes_crudeprev")
        row["obesity_pct"] = row.get("obesity_crudeprev")
        row["high_blood_pressure_pct"] = row.get("bphigh_crudeprev")
        row["physical_distress_pct"] = row.get("phlth_crudeprev")
        row["mental_distress_pct"] = row.get("mhlth_crudeprev")
        row["depression_pct"] = row.get("depression_crudeprev")

    add_scores(rows)
    return rows


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: clean_csv_value(row.get(field)) for field in CSV_FIELDS})


def score_color(score: float) -> str:
    if score >= 75:
        return "#c84a3f"
    if score >= 60:
        return "#d58a2a"
    if score >= 45:
        return "#287c85"
    return "#5f7f4f"


def render_bar_svg(rows: list[dict[str, object]]) -> str:
    top = rows[:10]
    width = 920
    height = 390
    left = 190
    top_pad = 36
    row_h = 31
    max_score = max(float(row["priority_score"]) for row in top) or 1
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Top counties by priority score">'
    ]
    parts.append('<line x1="190" y1="24" x2="190" y2="356" class="axis"/>')
    for index, row in enumerate(top):
        y = top_pad + index * row_h
        score = float(row["priority_score"])
        bar_w = (score / max_score) * 610
        color = score_color(score)
        county = html.escape(str(row["county"]))
        parts.append(f'<text x="12" y="{y + 19}" class="chart-label">{county}</text>')
        parts.append(
            f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="21" '
            f'rx="4" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{left + bar_w + 10:.1f}" y="{y + 16}" '
            f'class="chart-value">{score:.1f}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def render_scatter_svg(rows: list[dict[str, object]]) -> str:
    width = 920
    height = 430
    left = 76
    right = 34
    top = 34
    bottom = 64
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_pos(value: float) -> float:
        return left + (value / 100) * plot_w

    def y_pos(value: float) -> float:
        return top + plot_h - (value / 100) * plot_h

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Health burden by access gap scatter plot">'
    ]
    for tick in range(0, 101, 25):
        x = x_pos(tick)
        y = y_pos(tick)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" class="grid"/>')
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{height - 34}" class="tick" text-anchor="middle">{tick}</text>')
        parts.append(f'<text x="50" y="{y + 4:.1f}" class="tick" text-anchor="end">{tick}</text>')
    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>')
    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 10}" class="axis-label" text-anchor="middle">Access gap score</text>')
    parts.append('<text transform="translate(17 215) rotate(-90)" class="axis-label" text-anchor="middle">Health burden score</text>')

    max_pop = max(as_int(row["population"]) for row in rows) or 1
    for row in rows:
        x = x_pos(float(row["access_gap_score"] or 0))
        y = y_pos(float(row["health_burden_score"] or 0))
        population = as_int(row["population"])
        radius = 5 + math.sqrt(population / max_pop) * 15
        score = float(row["priority_score"])
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" '
            f'fill="{score_color(score)}" opacity="0.78">'
            f'<title>{html.escape(str(row["county"]))}: priority {score:.1f}</title>'
            '</circle>'
        )
    for row in rows[:5]:
        x = x_pos(float(row["access_gap_score"] or 0))
        y = y_pos(float(row["health_burden_score"] or 0))
        label = html.escape(str(row["county"]).replace(" County", ""))
        parts.append(
            f'<text x="{x + 12:.1f}" y="{y - 10:.1f}" class="point-label">{label}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def heat_cell(value: float | None) -> str:
    if value is None:
        return '<td class="num muted">n/a</td>'
    color = score_color(value)
    return f'<td class="heat num" style="--heat:{color}">{value:.1f}</td>'


def render_table(rows: list[dict[str, object]]) -> str:
    body = []
    for row in rows[:12]:
        body.append(
            "<tr>"
            f"<td>{int(row['rank'])}</td>"
            f"<th>{html.escape(str(row['county']))}</th>"
            f"<td class='num strong'>{float(row['priority_score']):.1f}</td>"
            f"<td class='num'>{float(row['health_burden_score']):.1f}</td>"
            f"<td class='num'>{float(row['social_need_score']):.1f}</td>"
            f"<td class='num'>{float(row['access_gap_score']):.1f}</td>"
            f"<td class='num'>{float(row['uninsured_adults_pct'] or 0):.1f}%</td>"
            f"<td class='num'>{float(row['food_insecurity_pct'] or 0):.1f}%</td>"
            f"<td class='num'>{int(float(row['primary_care_hpsa_count']))}</td>"
            f"<td class='num'>{int(float(row['mental_health_hpsa_count']))}</td>"
            f"<td class='num'>{float(row['hospital_per_100k'] or 0):.2f}</td>"
            "</tr>"
        )
    return "\n".join(body)


def render_component_heatmap(rows: list[dict[str, object]]) -> str:
    body = []
    for row in rows[:12]:
        body.append(
            "<tr>"
            f"<th>{html.escape(str(row['county']))}</th>"
            f"{heat_cell(as_float(row.get('health_burden_score')))}"
            f"{heat_cell(as_float(row.get('social_need_score')))}"
            f"{heat_cell(as_float(row.get('access_gap_score')))}"
            "</tr>"
        )
    return "\n".join(body)


def render_kpi_cards(rows: list[dict[str, object]], fetched_on: str) -> str:
    top = rows[0]
    total_hpsas = sum(
        float(row["primary_care_hpsa_count"]) + float(row["mental_health_hpsa_count"])
        for row in rows
    )
    total_hospitals = sum(float(row["hospital_count"]) for row in rows)
    avg_uninsured = mean([as_float(row["uninsured_adults_pct"]) for row in rows]) or 0
    cards = [
        ("Counties analyzed", f"{len(rows)}", "Maryland counties and Baltimore City"),
        ("Highest priority", str(top["county"]), f"Score {float(top['priority_score']):.1f}"),
        ("Active HPSAs", f"{int(total_hpsas)}", "Primary-care and mental-health designations"),
        ("Hospitals", f"{int(total_hospitals)}", "CMS Hospital General Information"),
        ("Avg. uninsured", f"{avg_uninsured:.1f}%", "CDC PLACES adult access measure"),
        ("Fetched", fetched_on, "Live public data pull"),
    ]
    return "\n".join(
        "<article class='kpi'>"
        f"<span>{html.escape(title)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        f"<p>{html.escape(note)}</p>"
        "</article>"
        for title, value, note in cards
    )


def render_html(rows: list[dict[str, object]], fetched_on: str) -> str:
    source_links = " ".join(
        f'<a href="{html.escape(url)}">{html.escape(name)}</a>'
        for name, url in SOURCES.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Maryland Health Access Priority Dashboard</title>
  <style>
    :root {{
      --ink: #1d2528;
      --muted: #5c676b;
      --line: #d9e1df;
      --paper: #f8faf8;
      --surface: #ffffff;
      --green: #5f7f4f;
      --teal: #287c85;
      --gold: #d58a2a;
      --coral: #c84a3f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
      letter-spacing: 0;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    .wrap {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-start;
      padding: 30px 0 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
      line-height: 1.1;
      font-weight: 760;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 1.08rem;
      line-height: 1.25;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }}
    a {{ color: var(--teal); font-weight: 650; text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    .source-note {{
      max-width: 430px;
      text-align: right;
      font-size: 0.92rem;
    }}
    main {{ padding: 24px 0 44px; }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 24px;
    }}
    .kpi {{
      min-height: 132px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .kpi span {{
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 720;
      text-transform: uppercase;
    }}
    .kpi strong {{
      display: block;
      margin: 10px 0 8px;
      font-size: 1.35rem;
      line-height: 1.12;
    }}
    .kpi p {{ font-size: 0.86rem; }}
    .grid-two {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 18px;
      margin-bottom: 22px;
    }}
    section {{
      min-width: 0;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    .chart {{
      width: 100%;
      height: auto;
      display: block;
      overflow: hidden;
    }}
    .axis {{ stroke: #80908e; stroke-width: 1.2; }}
    .grid {{ stroke: #e7ecea; stroke-width: 1; }}
    .chart-label, .chart-value, .tick, .axis-label, .point-label {{
      fill: var(--ink);
      font-size: 13px;
    }}
    .chart-label {{ font-weight: 650; }}
    .chart-value {{ font-weight: 720; }}
    .tick, .axis-label {{ fill: var(--muted); }}
    .point-label {{ font-size: 12px; font-weight: 720; }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      min-width: 920px;
      border-collapse: collapse;
      background: #ffffff;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 0.9rem;
      vertical-align: middle;
      white-space: nowrap;
    }}
    thead th {{
      background: #eef4f1;
      font-size: 0.76rem;
      text-transform: uppercase;
      color: #3f4d50;
    }}
    tbody tr:last-child th, tbody tr:last-child td {{ border-bottom: 0; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .strong {{ font-weight: 760; }}
    .muted {{ color: var(--muted); }}
    .heat {{
      color: #ffffff;
      background: var(--heat);
      font-weight: 760;
    }}
    .method {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
      margin-top: 22px;
    }}
    .formula {{
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
      font-variant-numeric: tabular-nums;
      font-weight: 720;
    }}
    .small {{
      margin-top: 10px;
      font-size: 0.86rem;
    }}
    footer {{
      padding: 22px 0 34px;
      border-top: 1px solid var(--line);
      background: #ffffff;
    }}
    @media (max-width: 980px) {{
      .topbar, .method {{ grid-template-columns: 1fr; display: grid; }}
      .topbar {{ gap: 12px; }}
      .source-note {{ text-align: left; max-width: none; }}
      .kpis {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .grid-two {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ width: min(100% - 22px, 1180px); }}
      h1 {{ font-size: 1.55rem; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      section {{ padding: 14px; }}
      .kpi {{ min-height: 122px; padding: 13px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>Maryland Health Access Priority Dashboard</h1>
        <p>County-level prioritization model for outreach planning using health burden, social need, provider-shortage designations, and hospital availability.</p>
      </div>
      <p class="source-note">Built from official public feeds: {source_links}. <a href="md_county_health_access_scores.csv">Download processed CSV</a>.</p>
    </div>
  </header>
  <main class="wrap">
    <div class="kpis">
      {render_kpi_cards(rows, fetched_on)}
    </div>

    <div class="grid-two">
      <section>
        <h2>Priority Ranking</h2>
        {render_bar_svg(rows)}
      </section>
      <section>
        <h2>Health Burden vs. Access Gap</h2>
        {render_scatter_svg(rows)}
      </section>
    </div>

    <section>
      <h2>Top Counties by Outreach Priority</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>County</th>
              <th class="num">Priority</th>
              <th class="num">Health</th>
              <th class="num">Social</th>
              <th class="num">Access</th>
              <th class="num">Uninsured</th>
              <th class="num">Food insecure</th>
              <th class="num">PC HPSA</th>
              <th class="num">MH HPSA</th>
              <th class="num">Hospitals / 100k</th>
            </tr>
          </thead>
          <tbody>
            {render_table(rows)}
          </tbody>
        </table>
      </div>
    </section>

    <div class="method">
      <section>
        <h2>Component Heatmap</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>County</th>
                <th class="num">Health burden</th>
                <th class="num">Social need</th>
                <th class="num">Access gap</th>
              </tr>
            </thead>
            <tbody>
              {render_component_heatmap(rows)}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <h2>Scoring Model</h2>
        <div class="formula">Priority = 40% health burden + 35% social need + 25% access gap</div>
        <p class="small">Each metric is min-max normalized across Maryland counties so 100 is the highest observed need in the state. Health burden includes diabetes, obesity, high blood pressure, physical distress, mental distress, and depression. Social need includes uninsured adults, food insecurity, housing insecurity, transportation barriers, and utility insecurity. Access gap combines active primary-care and mental-health HPSA designations, HPSA score severity, hospital count per 100,000 residents, and CMS star-rating gaps where available.</p>
        <p class="small">This is a planning and analytics artifact, not medical advice or a clinical triage tool.</p>
      </section>
    </div>
  </main>
  <footer>
    <div class="wrap">
      <p>Generated on {html.escape(fetched_on)} by <code>src/build_dashboard.py</code>. The processed dataset is committed for review, and the pipeline can be rerun against the official sources.</p>
    </div>
  </footer>
</body>
</html>
"""


def main() -> int:
    fetched_on = dt.date.today().isoformat()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    rows = build_dataset()
    processed_csv = PROCESSED_DIR / "md_county_health_access_scores.csv"
    docs_csv = DOCS_DIR / "md_county_health_access_scores.csv"
    write_csv(rows, processed_csv)
    write_csv(rows, docs_csv)
    (DOCS_DIR / "index.html").write_text(render_html(rows, fetched_on), encoding="utf-8")

    top = rows[0]
    print(f"Wrote {processed_csv.relative_to(ROOT)}")
    print(f"Wrote {docs_csv.relative_to(ROOT)}")
    print(f"Wrote {Path('docs/index.html')}")
    print(
        f"Top priority: {top['county']} "
        f"({float(top['priority_score']):.1f})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
