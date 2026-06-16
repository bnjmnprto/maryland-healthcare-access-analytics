# Portfolio Case Study: Maryland Healthcare Access Analytics

## Problem

Healthcare access risk is multidimensional. A county may face provider shortages, high uninsured rates, high chronic disease burden, weaker hospital capacity, or a combination of those barriers. The challenge is to organize these signals into a clear, reproducible workflow that can support public-health planning conversations without overclaiming clinical validity.

This project asks: **which Maryland counties show elevated healthcare access risk signals, and what factors appear to drive those signals in the demonstration dataset?**

## Stakeholders

Potential stakeholders include:

- Healthcare data analysts
- Public health analysts
- Community health program managers
- Nonprofit healthcare organizations
- Population health teams
- Workforce planning teams
- Hiring managers reviewing analytics portfolio work

## Data

The current repository uses a sample Maryland county-level dataset so the project runs locally without credentials or paid services. It also includes optional public-data ingestion for selected CDC PLACES, HRSA HPSA, and CMS Provider Data fields. The fields are structured to mirror official public data sources such as ACS, CDC PLACES, HRSA shortage-area data, CMS Provider Data, County Health Rankings, Maryland Open Data, and Maryland Department of Health sources.

The project does not use patient-level data.

## Methods

The workflow creates four interpretable risk components:

- Provider access gap
- Socioeconomic need
- Chronic disease burden
- Hospital quality/capacity gap

Each component is built from min-max scaled county-level indicators. The final access risk score weights provider access most heavily, followed by socioeconomic need, chronic burden, and hospital quality/capacity.

## SQL Layer

The project creates a SQLite database with normalized tables:

- `counties`
- `demographics`
- `health_outcomes`
- `provider_shortages`
- `hospital_quality`
- `access_risk_scores`

The SQL query file answers practical portfolio questions:

- Which counties have the highest access risk?
- Which counties combine high poverty, high uninsured rates, and poor provider access?
- Which counties have worse chronic disease burden?
- How do counties compare to the Maryland average?

## ML Layer

The ML workflow trains logistic regression and random forest models.

The default model target is `high_poor_or_fair_health_rate`, an external-proxy target based on counties in the top quartile of poor/fair health rate. This is stronger than only predicting a label derived from the project’s own risk score, but the current data is still sample data.

The script also supports `demo_score` mode, which uses the score-derived `high_access_risk` label. That mode is clearly marked as demonstration-only.

## Dashboard Layer

The Streamlit dashboard includes:

- Overview metrics
- Maryland county choropleth risk map
- County risk ranking
- County comparison tool
- Demographic, healthcare access, and outcome charts
- Model results and feature interpretation
- Plain-English county summaries
- Responsible-use notes

If the GeoJSON county boundary file cannot be loaded, the map section falls back to a county ranking table.

## AI Summary Layer

The project includes a template-based AI-style summary module. It does not require an API key and does not send data to a paid service. The summaries use aggregate county-level metrics and include language reminding users to review local context and updated source data.

## Findings From The Sample Dataset

In the demonstration dataset, Somerset, Dorchester, Caroline, Allegany, Garrett, and Wicomico appear near the top of the access risk ranking. These sample findings reflect overlapping signals such as provider access gaps, socioeconomic need, chronic disease burden, and hospital quality/capacity gaps.

These are demonstration findings only. They should not be interpreted as official public-health conclusions.

## Limitations

- The included data is illustrative sample data.
- County-level averages can hide neighborhood-level variation.
- The ML model is not validated for deployment.
- The default target is an external-proxy sample target, not an official outcome.
- The project does not include appointment wait times, provider network adequacy, transportation time, language access, disability access, or community input.

## Recommendations

- Use the dashboard as a portfolio demonstration and planning conversation starter.
- Replace the sample data with official public datasets before making operational claims.
- Use the optional `make live-data` workflow to demonstrate public-source ingestion, while treating fallback fields honestly.
- Validate future models against preventable hospitalizations, avoidable emergency department visits, ambulatory care sensitive admissions, appointment wait times, or unmet care due to cost.
- Add county mapping, data quality checks, source refresh automation, and equity review before production use.

## Future Production Version

A production version would use official data extracts from ACS, CDC PLACES, HRSA, CMS, County Health Rankings, Maryland Open Data, and Maryland Department of Health sources. It would add extract dates, source table IDs, automated validation, geographic trend analysis, model monitoring, and stakeholder-reviewed methodology.

The strongest next step would be validating the access risk score against an independent observed outcome such as preventable hospitalizations or avoidable emergency department utilization.
