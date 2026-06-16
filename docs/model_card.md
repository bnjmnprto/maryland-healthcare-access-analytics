# Model Card

## Model Purpose

The model demonstrates a reproducible healthcare analytics machine learning workflow for Maryland county-level access indicators. It is intended for employer portfolio review and technical communication, not operational deployment.

## Intended Use

- Demonstrate feature engineering, target selection, model training, evaluation, interpretation, and dashboard integration.
- Support portfolio review for Healthcare Data Analyst, Data Analyst, Junior Data Scientist, Public Health Data Analyst, and AI/Data Analyst roles.
- Explain associations between county-level features and the selected external/proxy target.

## Not Intended Use

- Clinical diagnosis, treatment, triage, or patient-specific decision-making.
- Eligibility decisions, funding denial, service denial, or automated resource allocation.
- Validated public-health surveillance or operational prediction.

## Data Sources

Current model inputs come from `data/processed/model_feature_table.csv`, built by `src/data_pipeline.py`.

Current run status:

- ACS demographics: real public ACS estimates via Census Reporter API
- CDC PLACES: real public county-level health indicators
- HRSA HPSA: real public shortage-area downloads aggregated to county FIPS
- CMS Hospital General Information: real public hospital facility data aggregated to county
- Fallback fields: documented sample reference fields listed in `data/processed/run_metadata.json`

No patient-level data is used.

## Features

Feature groups include:

- ACS socioeconomic and access features: poverty, income, uninsured, age 65+, disability, no vehicle, no internet
- CDC PLACES health features: diabetes, obesity, high blood pressure, poor/fair health, smoking, physical distress, checkup
- HRSA shortage features: HPSA scores, counts, and designation flags
- CMS hospital features: hospital count, acute-care count, emergency services count, average hospital rating
- Engineered component indices: socioeconomic need, insurance/access burden, chronic burden, and hospital burden

When the HRSA target is used, HPSA-derived provider features are excluded from predictors to avoid a circular target.

## Target Variable

Default target mode: `independent_external`

Default target: `high_hrsa_provider_shortage_burden`

Definition: counties in the top quartile of a HRSA HPSA score/count burden index.

Fallback target hierarchy:

1. HRSA provider shortage burden
2. CDC PLACES high poor/fair health rate
3. ACS high uninsured rate
4. Demo rule-derived high access-risk label

The demo rule-derived target is a last fallback only and is not independent validation.

## Model Type

- Logistic regression: selected default model for reproducibility and coefficient interpretation
- Random forest: retained as a comparison model

Model selection is deterministic. The selected model is intentionally fixed to logistic regression.

## Evaluation

Outputs:

- `data/processed/model_metrics.json`
- `data/processed/model_predictions.csv`
- `data/processed/feature_importance.csv`
- `data/processed/access_risk_model.joblib`

Evaluation uses a fixed random state, stratified train/test split when feasible, and small-sample cross-validation metadata. Because there are only 24 Maryland jurisdictions, metrics should be treated as workflow checks.

Perfect or near-perfect metrics can occur with small county-level datasets and should not be interpreted as validated predictive performance.

## Limitations

- The dataset is county-level and small.
- Some features remain documented fallback fields.
- The target is an external planning proxy, not an observed clinical or utilization outcome.
- County-level indicators can hide neighborhood-level inequities.
- The model cannot predict individual health outcomes.

## Fairness And Ethics

A production version should include equity review, sub-county analysis where available, uncertainty checks, stakeholder review, and transparent data lineage. Demographic indicators should not be used to deny care or infer individual risk.

## Healthcare Responsible-Use Warning

This model is not a clinical decision tool. It should not be used to diagnose, treat, triage, determine eligibility, deny services, or allocate resources automatically. It is a portfolio demonstration of county-level healthcare analytics.
