# Executive Summary

## Problem

Healthcare access risk is multidimensional. Maryland jurisdictions can face overlapping barriers: poverty, uninsured residents, transportation and digital access constraints, chronic disease burden, provider shortage designations, and limited hospital availability. Analysts need a transparent workflow that organizes these signals without overclaiming clinical validity.

## Methods

Maryland Healthcare Access Analytics builds a county-level pipeline for all 24 Maryland county-equivalent jurisdictions, including Baltimore City.

The default pipeline attempts real public data first:

- ACS demographics and access indicators via Census Reporter’s ACS API
- CDC PLACES health indicators
- HRSA HPSA provider-shortage downloads
- CMS Hospital General Information

The current committed run is `mixed_real_and_demo_data`: the public sources loaded successfully, while selected fields remain documented sample fallback values because the public feeds do not provide those exact measures. Fallback status is recorded in `data/processed/run_metadata.json`.

The risk score combines five components:

- Socioeconomic vulnerability
- Insurance and access burden
- Chronic disease burden
- Provider shortage burden
- Hospital availability/quality burden

The project also includes a SQLite layer, SQL queries, validation reports, a reproducible machine learning workflow, template-based AI-style summaries, and a Streamlit dashboard with choropleth mapping.

## Findings

The current run identifies elevated access-risk signals in several jurisdictions, with top risk drivers varying by county. Some jurisdictions show chronic disease burden as the leading factor, while others are driven by provider shortage burden or socioeconomic vulnerability.

These findings should be interpreted as planning signals only. They are not official public-health rankings and are not clinical conclusions.

## Machine Learning

The model defaults to an HRSA provider-shortage target when available: `high_hrsa_provider_shortage_burden`, target mode `independent_external`. HPSA-derived predictor fields are excluded to avoid circular modeling. Logistic regression is selected deterministically for reproducibility, while random forest is retained for comparison.

Perfect or near-perfect metrics can occur with small county-level datasets and should not be interpreted as validated predictive performance.

## Recommendations

- Use the dashboard to identify counties that warrant deeper local review.
- Treat the score as a transparent prioritization index, not a decision rule.
- Review fallback fields before any operational use.
- Pair county-level signals with sub-county, community, and provider-network context.
- Validate future models against observed outcomes such as preventable hospitalizations or avoidable emergency department visits.

## Limitations

- County averages can hide neighborhood-level inequities.
- Some fields remain sample fallback values.
- Source years differ across ACS, CDC, HRSA, and CMS.
- No patient-level data is used.
- The project is not a clinical, eligibility, or resource-allocation tool.

## Next Steps

- Replace fallback provider workforce and hospital capacity fields with official public sources.
- Add scheduled source refreshes and source-level QA.
- Add multi-year trend analysis.
- Validate the score against independent outcomes.
- Deploy the Streamlit app after human review.
