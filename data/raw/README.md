# Raw Data

This folder contains a small portfolio sample file so the project runs without paid APIs, large downloads, or credentials.

## Included sample

- `maryland_county_health_access_sample.csv` contains one row per Maryland county or county-equivalent jurisdiction.
- Values are illustrative and designed for reproducible portfolio development. They are not intended for operational public-health decision-making.
- `maryland_counties.geojson` contains Maryland county boundary geometry for the dashboard choropleth map. It was downloaded from Maryland Open Data's County Boundaries dataset.
- `source_manifest.json` documents the default sample file, the optional public-data sources, and the fields currently filled by live ingestion.

## Optional public-data ingestion

Run the optional live ingestion path with:

```bash
make live-data
make live-pipeline
```

`src/public_data_ingestion.py` pulls public county-level indicators from CDC PLACES, HRSA HPSA downloads, and CMS Provider Data where feasible. It writes `maryland_county_health_access_public.csv` and `public_data_provenance.json`, both of which are ignored by git because they depend on live source availability and fetch date.

Fields that are not available from the current public feeds retain documented sample fallback values. This keeps the project runnable while making source coverage honest.

## Recommended public data sources for production refreshes

Use the same county FIPS key (`county_fips`) when replacing the sample data:

- U.S. Census ACS 5-year Data Profiles for population, income, poverty, insurance status, age, and race or ethnicity.
- CDC PLACES county-level data for chronic disease burden and health status indicators.
- HRSA Data Warehouse shortage-area downloads or HPSA Find for primary care, dental, and mental health shortage designations.
- CMS Provider Data hospital datasets for hospital facility and quality measures.
- County Health Rankings & Roadmaps for county health outcomes, access, socioeconomic, and clinical-care indicators.
- Maryland Department of Health and Maryland Open Data datasets where county-level indicators are available.
- Maryland Open Data County Boundaries for county geometry: `https://opendata.maryland.gov/resource/y8c4-8fr3.geojson?$limit=5000`

## Suggested replacement workflow

1. Download source files into `data/raw/`.
2. Keep raw files unchanged.
3. Add a new loader or column mapping inside `src/data_pipeline.py`.
4. Run:

```bash
python src/data_pipeline.py
python src/risk_model.py
```

The dashboard reads from `data/processed/dashboard_county_risk.csv`.
