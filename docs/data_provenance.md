# Data Provenance

## Current Default Dataset

The repository defaults to `data/raw/maryland_county_health_access_sample.csv`. This file is a curated demonstration dataset with one row for each Maryland county or county-equivalent jurisdiction, including Baltimore City. It exists so reviewers can run the full project without credentials, paid services, large downloads, or network access.

The sample structure mirrors public county-level sources, but the included values should not be treated as official public-health findings.

## Optional Live Public-Data Ingestion

The optional script `src/public_data_ingestion.py` can build a pipeline-compatible raw CSV using public sources where fields are available:

```bash
make live-data
make live-pipeline
```

The script writes:

- `data/raw/maryland_county_health_access_public.csv`
- `data/raw/public_data_provenance.json`

Those generated files are intentionally ignored by git because they depend on live source availability and fetch date.

## Source Coverage

| Source | Fields used where feasible | Notes |
|---|---|---|
| CDC PLACES county data | Population, uninsured rate, diabetes, obesity, hypertension, poor/fair health proxy | Official public county-level health indicators. |
| HRSA HPSA primary care download | Primary care shortage score | Uses active designated Maryland HPSA records. |
| HRSA HPSA mental health download | Mental health shortage score | Uses active designated Maryland HPSA records. |
| CMS Hospital General Information | Hospital count, average hospital star rating | Aggregates Maryland hospital records to county level. |
| Maryland Open Data County Boundaries | County geometry | Used for the dashboard choropleth map. |
| Bundled sample fallback | Demographics, provider supply, dental access, hospital beds, readmissions, life expectancy, and any missing live fields | Keeps the project runnable and schema-complete. |

## Why Some Fields Still Use Fallback Values

The dashboard schema includes features that are not all available in a single public feed with identical county coverage and refresh timing. For example, median household income, poverty, age structure, provider rates, dental provider supply, hospital beds, readmission rates, and life expectancy should ideally come from ACS, County Health Rankings, CMS quality files, state facility sources, or workforce data.

The optional live ingestion script therefore uses public data where feasible and clearly marks remaining fields as sample fallback. A production version should replace those fallback fields with official extracts and preserve source table IDs, extract dates, and refresh logic.

## Responsible-Use Boundary

This project uses aggregate county-level data only. It does not use patient-level data and should not be used for diagnosis, treatment, eligibility decisions, funding denial, or automated clinical triage.
