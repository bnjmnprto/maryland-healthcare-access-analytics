# Validation Report

## Validation Status

**Status:** PASS

## Source Coverage

- Data mode: `mixed_real_and_demo_data`
- Sources loaded: ACS, CDC PLACES, CMS Hospital Quality, HRSA HPSA
- Sources/fields using fallback: sample reference fields
- Run timestamp: 2026-06-16T06:29:25+00:00
- All 24 jurisdictions present: True

The current committed run is `mixed_real_and_demo_data`: ACS, CDC PLACES, HRSA HPSA, and CMS Hospital Quality are loaded as real public-data sources. The bundled sample file remains only as a documented fallback for selected reference fields that are unavailable from those public feeds, including some provider workforce and hospital capacity fields.

## Row Counts

- Raw sample rows: 24
- Processed feature rows: 24
- Expected Maryland county/county-equivalent rows: 24

## County Coverage

- Unique processed county FIPS codes: 24
- Baltimore City present: True
- County coverage complete: True

## Missingness

- `hrsa_date_accessed`: 24 missing values
- `cms_date_accessed`: 24 missing values

## Duplicate Checks

- Duplicate FIPS values: 0
- Duplicate county names: 0

## Feature Range Checks

- Access risk score range: 12.5 to 75.8
- Risk score within 0-100: True
- Risk tier counts: {'Moderate': 9, 'Elevated': 7, 'Low': 6, 'High': 2}

## Validation Findings

- No validation errors detected.

## Known Limitations

- The dataset is county-level and does not contain patient-level data.
- Data mode may be `mixed_real_and_demo_data` because public sources do not provide every portfolio field.
- Fallback fields are documented in `data/processed/run_metadata.json`.
- The risk score is a transparent prioritization index, not a clinically validated model.
- A production version should add scheduled source refreshes, direct source QA, stakeholder review, and equity impact review.
