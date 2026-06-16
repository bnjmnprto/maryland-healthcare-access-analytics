# Portfolio Case Study

## Project

Maryland Healthcare Access Analytics

## Problem

Public-health and healthcare operations teams often need to compare access barriers across counties, but the relevant signals live in separate public datasets. This project turns those signals into a reproducible analytics workflow and dashboard.

## Stakeholders

- Healthcare data analysts
- Public health analysts
- Population health teams
- Community health planning teams
- Hiring managers reviewing portfolio readiness

## Data

The default pipeline attempts real public data first:

- ACS county demographics and access proxies
- CDC PLACES county health indicators
- HRSA HPSA provider-shortage records
- CMS Hospital General Information

The current run is `mixed_real_and_demo_data`: public sources loaded successfully, with a small number of documented fallback fields retained for schema completeness and reproducibility.

## Pipeline

`src/data_pipeline.py` loads cached or refreshed source extracts, joins records by county FIPS, creates a final county feature table, writes `run_metadata.json`, and publishes a SQLite database. The pipeline validates all 24 Maryland jurisdictions, including Baltimore City.

## SQL Layer

The SQLite layer includes source, feature, risk score, and validation tables. `sql/queries.sql` answers employer-relevant questions about highest-risk jurisdictions, poverty and chronic disease burden, uninsured rates, provider shortage, hospital access, regional risk components, and data completeness.

## Risk Score

The score is a 0-100 transparent prioritization index built from five components:

- Socioeconomic vulnerability
- Insurance and access burden
- Chronic disease burden
- Provider shortage burden
- Hospital availability/quality burden

The methodology document explains source variables, directionality, normalization, weights, and limitations.

## ML Workflow

`src/risk_model.py` uses a target hierarchy that prefers independent external targets. In the current run, the target is HRSA provider-shortage burden. HPSA-derived inputs are excluded from predictors when that target is used. Metrics are reproducible and caveated because the sample size is only 24 jurisdictions.

## Dashboard

The Streamlit dashboard shows:

- Data mode and source coverage
- Risk ranking
- County comparison
- Maryland choropleth map
- Model results
- AI-style county summary
- Data quality/source table
- Responsible-use notes

## AI-Style Summaries

`src/ai_summary.py` generates plain-English county summaries without an API key. Summaries use only final dataset values, mention the data mode, and include a responsible-use caveat.

## Findings

The current data identifies different access-risk drivers across Maryland jurisdictions. Some counties are driven by chronic disease burden, others by provider shortage or socioeconomic vulnerability. These are planning signals, not official rankings or clinical conclusions.

## Limitations

- County-level data hides sub-county variation.
- Some fields remain documented fallback fields.
- Public sources refresh on different schedules.
- The model target is a proxy, not an observed utilization outcome.
- No patient-level data is used.

## Recommendations

- Use the project as a reproducible analytics product and portfolio case study.
- Replace fallback fields with official workforce, hospital capacity, and utilization sources before operational use.
- Add multi-year trends and uncertainty checks.
- Validate against preventable hospitalizations, avoidable emergency visits, or unmet care due to cost.

## Future Production Version

A production version would add scheduled source refreshes, direct Census API-key support, source-level QA, multi-year data, validated outcomes, role-based stakeholder review, equity impact assessment, and deployment monitoring.
