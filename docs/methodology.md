# Methodology

## Project Framing

This project estimates county-level healthcare access risk across Maryland using indicators that are commonly available from public datasets. The committed workflow uses a stable sample dataset by default and includes optional live ingestion for selected CDC PLACES, HRSA HPSA, and CMS Provider Data fields. The goal is not to diagnose patients or replace local public-health judgment. The goal is to show how an analyst can combine demographic, access, facility, and outcome signals into a transparent prioritization workflow.

## Why These Four Risk Components Were Chosen

### Provider Access Gap

Provider availability is central to healthcare access. A county with fewer primary care, mental health, or dental providers may face longer appointment wait times, more travel burden, and fewer preventive-care touchpoints. HRSA shortage-area style scores add a public-health planning signal beyond simple provider counts.

### Socioeconomic Need

Healthcare access is strongly shaped by affordability and social context. Poverty and uninsured rates can limit preventive care, medication adherence, and timely follow-up. Median household income is included inversely because lower income can indicate financial barriers. Older adult share is included because aging populations often have higher care coordination and transportation needs.

### Chronic Disease Burden

High chronic disease prevalence can indicate greater demand for ongoing care. Diabetes, obesity, hypertension, poor/fair health, and preventable hospital stays are included because they connect access, prevention, and health system strain.

### Hospital Quality and Capacity Gap

Hospitals are not the whole access story, but they matter when counties have limited acute-care capacity, higher readmission rates, or lower facility quality ratings. This component is weighted lower than provider access and chronic burden because hospital measures are less direct proxies for everyday primary and preventive care access.

## How Min-Max Scaling Works

The pipeline uses min-max scaling to place indicators with different units on a common 0-100 scale:

```text
scaled_value = ((county_value - minimum_county_value) / (maximum_county_value - minimum_county_value)) * 100
```

For measures where higher raw values are better, such as provider supply or hospital star rating, the project inverts the scaled value:

```text
inverted_scaled_value = 100 - scaled_value
```

This makes the component scores easier to read: higher component values consistently mean more risk or greater need.

Min-max scaling is easy to explain and beginner-friendly, but it has limitations. It depends on the range of counties included in the dataset, can be sensitive to outliers, and does not prove that a county is clinically unsafe or underserved. In a production version, the team should test alternative scaling methods, uncertainty intervals, and benchmarks against state or national reference values.

## Why These Weights Were Selected

The current access risk score uses:

- 35% provider access gap
- 25% socioeconomic need
- 25% chronic disease burden
- 15% hospital quality and capacity gap

Provider access receives the highest weight because the project is specifically focused on healthcare access risk, not overall population health ranking. Socioeconomic need and chronic burden receive equal weights because both affordability barriers and care demand can drive poor access outcomes. Hospital quality/capacity receives a smaller but meaningful weight because facility context matters, but it is less directly tied to routine outpatient access than provider availability.

These weights are transparent assumptions, not validated policy weights. They are intentionally easy to change in `src/data_pipeline.py`. A production version should review weights with public-health leaders, community stakeholders, clinicians, and healthcare operations teams.

## ML Target Modes

The model script supports two target modes.

The default mode is `external_proxy`. It labels counties in the top quartile of `poor_or_fair_health_pct` as `high_poor_or_fair_health_rate`. This target is not derived from the project’s access risk score, so it is more credible than only predicting a score-derived label. However, the current values are still part of the demonstration dataset, so this should be treated as a sample workflow rather than validated predictive modeling.

The optional mode is `demo_score`. It uses `high_access_risk`, a label derived from the project’s own access risk score. This mode is useful for showing ML workflow mechanics, but it is explicitly demonstration-only.

The modeling layer is acceptable for a portfolio demonstration because it shows:

- Train/test split workflow
- Logistic regression and random forest modeling
- Model evaluation metrics
- Feature importance and coefficient interpretation
- Dashboard integration of model outputs

It should not be interpreted as validated predictive performance. Perfect or near-perfect metrics can happen with a small dataset and should be treated as a workflow signal, not deployment evidence.

## Future Validated Outcome

A future production version should train and validate against an external outcome that was not created by the project score. Stronger candidate outcomes include:

- Avoidable emergency department visit rates
- Preventable hospitalization rates
- Ambulatory care sensitive condition admissions
- Appointment wait-time measures
- Unmet care due to cost
- Primary care visit rates or delayed care survey measures
- County-level preventable hospital stays from an official source

The strongest near-term validation target would be an independently sourced measure of preventable hospitalizations or avoidable emergency department utilization, ideally stratified by year and county. That would test whether the score and model identify counties with measurable access-related utilization burden.

## Ethical Limitations

This project should not be used as a clinical decision tool, benefits eligibility tool, or automated resource denial tool. It operates at the county level and cannot represent individual patients, households, neighborhoods, or provider networks.

Important limitations:

- County averages can hide neighborhood-level inequities.
- Rural travel time, language access, disability access, broadband access, and appointment availability are not fully captured.
- Race/ethnicity-style demographic measures should be used only for equity review, not as causal explanations or individual-level predictors.
- The sample dataset is illustrative and should be replaced before operational use.
- A risk score can guide questions and prioritization, but it cannot determine why access barriers exist without local context.

Responsible production use would require official source refreshes, data quality checks, stakeholder review, equity impact review, uncertainty analysis, and clear communication that the dashboard supports planning rather than clinical judgment.
