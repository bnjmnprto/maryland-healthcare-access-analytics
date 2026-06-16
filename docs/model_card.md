# Model Card

## Model Purpose

The model demonstrates a beginner-friendly healthcare analytics machine learning workflow for identifying Maryland counties with elevated access-related risk signals. It is part of a portfolio simulation and is intended to show reproducible feature engineering, model training, evaluation, interpretation, and dashboard integration.

## Intended Use

- Demonstrate a healthcare analytics modeling workflow.
- Support portfolio review for Data Analyst, Healthcare Data Analyst, Junior Data Scientist, AI/Data Analyst, and Analytics Engineer-adjacent roles.
- Help users understand which county-level features are associated with the selected target in the sample dataset.
- Support planning conversations and deeper analysis, not operational decisions.

## Not Intended Use

- Clinical diagnosis, treatment, triage, or patient-specific decision-making.
- Eligibility decisions, funding denial, or automated resource allocation.
- Validated public-health surveillance.
- Real-world prediction without replacing the sample data and validating against official external outcomes.

## Data Sources

The current model defaults to the project’s demonstration dataset in `data/raw/maryland_county_health_access_sample.csv`. The repository also includes `src/public_data_ingestion.py`, which can build an optional raw file from selected CDC PLACES, HRSA HPSA, and CMS Provider Data fields while retaining documented sample fallback values for missing feature groups.

The fields are structured to mirror public county-level data sources such as:

- U.S. Census ACS county demographics
- CDC PLACES chronic disease and health status indicators
- HRSA HPSA/provider shortage data
- CMS hospital quality or facility data
- County Health Rankings
- Maryland Open Data / Maryland Department of Health sources

## Features

The model uses county-level demographic, access, provider, chronic disease, and hospital quality/capacity indicators. Example features include:

- Poverty rate
- Uninsured rate
- Older adult share
- Primary care physicians per 100,000 residents
- Mental health providers per 100,000 residents
- Dental providers per 100,000 residents
- HRSA-style primary care and mental health shortage scores
- Diabetes, obesity, and hypertension prevalence
- Preventable hospital stays
- Average hospital star rating
- Readmission rate

When the default external-proxy target is used, `poor_or_fair_health_pct` is excluded from the model inputs because it is used to construct the target.

## Target Variable

The default target mode is `external_proxy`.

**Default target:** `high_poor_or_fair_health_rate`

This target labels counties in the top quartile of `poor_or_fair_health_pct`. It is not derived from the project’s access risk score, so it is a stronger demonstration target than the original score-derived label. However, the current values are still sample portfolio data, so this is not validated predictive modeling.

The script also supports `demo_score` mode.

**Demo target:** `high_access_risk`

This label is derived from the top quartile of the project’s own access risk score. It is useful only for demonstrating ML workflow mechanics and should not be interpreted as independent validation.

## Evaluation

The model script trains:

- Logistic regression
- Random forest classifier

Outputs include:

- `data/processed/model_metrics.json`
- `data/processed/model_predictions.csv`
- `data/processed/feature_importance.csv`
- `data/processed/access_risk_model.joblib`

Because the dataset has only 24 county rows, evaluation metrics should be treated as workflow checks rather than deployment evidence.

## Limitations

- The committed default data is illustrative sample data.
- Optional live ingestion does not yet replace every field and should be reviewed through `docs/data_provenance.md`.
- County-level data can hide neighborhood-level inequities.
- The default target is an external-proxy target, not a validated operational outcome.
- The model does not use patient-level data and cannot predict individual health outcomes.
- The sample size is too small for robust model validation.
- Production modeling would require multiple years of official public data and validation against an observed outcome.

## Fairness And Ethics

The project avoids patient-level data and does not make individual predictions. Demographic fields should be used for descriptive equity review, not for denying services or making assumptions about individual patients.

A production version should include:

- Equity impact review
- Stakeholder review
- Sub-county analysis where available
- Transparent data lineage
- Uncertainty and sensitivity checks
- Governance around any LLM-generated narrative

## Healthcare Responsible-Use Warning

This model is not a clinical decision tool. It should not be used to diagnose, treat, triage, or determine individual eligibility. It is a portfolio demonstration of county-level healthcare analytics and should be interpreted only as a planning and communication workflow.
