# Data Provenance

## Current Default Run

The current committed run is recorded in `data/processed/run_metadata.json`. At publication time, the run mode is `mixed_real_and_demo_data`: public ACS, CDC PLACES, HRSA HPSA, and CMS Hospital General Information sources loaded successfully, while selected fields remain documented sample fallbacks.

No patient-level data is used.

## Source Details

| Source | Access URL or endpoint | Variables used | Transformation | Current status |
|---|---|---|---|---|
| U.S. Census ACS 5-year via Census Reporter API | `https://api.censusreporter.org/1.0/data/show/latest?table_ids=B01003,B17001,B19013,B27010,B01001,B18101,B08201,B28002&geo_ids=050|04000US24` | population, poverty, median income, uninsured, age 65+, disability, no vehicle, no internet | Detailed ACS counts are converted to county percentages and joined by FIPS | Used in current run |
| CDC PLACES county API | `https://data.cdc.gov/resource/i46a-9kgh.json?$limit=5000&stateabbr=MD` | poor/fair health, diabetes, high blood pressure, obesity, smoking, physical distress, checkup, access proxy | County records are filtered to Maryland and renamed to project feature columns | Used in current run |
| HRSA HPSA downloads | `BCD_HPSA_FCT_DET_PC.csv`, `BCD_HPSA_FCT_DET_MH.csv`, `BCD_HPSA_FCT_DET_DH.csv` from `https://data.hrsa.gov/DataDownload/DD_Files/` | HPSA score, designated record counts, primary/mental/dental status | Active designated records are filtered to Maryland and aggregated to county FIPS | Used in current run |
| CMS Hospital General Information | `https://data.cms.gov/provider-data/dataset/xubh-q36u` | hospital count, acute-care count, emergency services count, overall rating | Maryland facilities are aggregated to county using county names and FIPS lookup | Used in current run |
| Maryland county GeoJSON | `data/raw/maryland_counties.geojson` | county geometries | FIPS fields are normalized for Plotly map joins | Used in dashboard |
| Bundled sample fallback | `data/raw/maryland_county_health_access_sample.csv` | region, rural flag, nonwhite percentage, provider workforce rates, beds, readmission proxy, preventable stays, life expectancy | Used only for fields not provided by current public feeds | Fallback fields in current run |

## Access Dates

Access dates are written by each fetcher and summarized in `data/processed/run_metadata.json`.

Processed source extracts:

- `data/processed/acs_county_demographics.csv`
- `data/processed/cdc_places_maryland.csv`
- `data/processed/hrsa_hpsa_maryland.csv`
- `data/processed/cms_hospital_quality_maryland.csv`

Raw or filtered raw source extracts:

- `data/raw/acs/`
- `data/raw/cdc_places/`
- `data/raw/hrsa_hpsa/`
- `data/raw/cms_hospital_quality/`

## Known Limitations

- ACS is accessed through Census Reporter’s public API because direct `api.census.gov` calls may require an API key in some environments.
- CMS Hospital General Information does not provide hospital beds or a true county readmission rate, so those fields remain documented fallback values.
- Provider workforce rates are fallback fields until an official county-level workforce source is integrated.
- County-level indicators can hide sub-county access barriers.
- Source years and release timing may differ across ACS, CDC, HRSA, and CMS.

## Responsible-Use Boundary

This project uses aggregate county-level public data and sample fallback fields. It should not be used for diagnosis, treatment, individual eligibility, service denial, or automated resource allocation. Any operational version would require official source refresh governance, uncertainty analysis, equity review, and stakeholder sign-off.
