# Data Sources

Maryland Healthcare Access Analytics now defaults to public county-level data where feasible. The current committed run uses `mixed_real_and_demo_data`: ACS, CDC PLACES, HRSA HPSA, and CMS Hospital General Information were loaded successfully, while a small number of fields remain documented sample fallbacks because the public feeds do not provide those exact measures in this project.

## Current Run

- Data mode: recorded in `data/processed/run_metadata.json`
- Final feature table: `data/processed/healthcare_access_features.csv`
- Dashboard data: `data/processed/dashboard_county_risk.csv`
- No patient-level data is used.

## Real Public Sources

| Source | Current use | Output | Notes |
|---|---|---|---|
| U.S. Census ACS 5-year via Census Reporter API | Demographics, poverty, income, uninsured, age 65+, disability, vehicle access, internet access | `data/processed/acs_county_demographics.csv` | Census Reporter provides public no-key access to ACS tables. A production version may use direct `api.census.gov` calls with an API key. |
| CDC PLACES | Poor/fair health, diabetes, high blood pressure, obesity, smoking, frequent physical distress, checkup, access proxy | `data/processed/cdc_places_maryland.csv` | County-level aggregate estimates only. |
| HRSA HPSA downloads | Primary care, mental health, and dental HPSA designation counts and scores | `data/processed/hrsa_hpsa_maryland.csv` | Aggregated from designated shortage-area records to county FIPS. |
| CMS Hospital General Information | Hospital count, acute care count, emergency services count, average hospital rating | `data/processed/cms_hospital_quality_maryland.csv` | Beds and true county readmission rates are not available in this feed and remain documented fallback fields. |

## Fallback Fields

The bundled sample file remains a fallback for region labels, rural flag, nonwhite percentage, provider workforce rates, hospital beds per 1,000 population, readmission-rate proxy, preventable hospital stays, and life expectancy. These fields are listed in `source_fallback_fields` inside `data/processed/run_metadata.json`.

## Responsible Use

The data is aggregate county-level data. It should support portfolio review and planning discussion only. It is not a clinical decision tool, eligibility tool, resource-denial tool, or validated operational surveillance product.
