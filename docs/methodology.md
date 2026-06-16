# Methodology

## Project Framing

Maryland Healthcare Access Analytics is a county-level public-health analytics workflow. The default pipeline attempts real public data first and uses a documented sample fallback only where a public feed does not provide the required field or is unavailable. The current committed run is `mixed_real_and_demo_data`: ACS, CDC PLACES, HRSA HPSA, and CMS Hospital General Information loaded successfully, while selected reference fields remain fallback values.

The score is a transparent prioritization index. It is not clinically validated and should not be used for diagnosis, treatment, eligibility, denial of care, or automated resource allocation.

## Why These Five Risk Components Were Chosen

### Socioeconomic Vulnerability

Variables: poverty rate, median household income, age 65+ percentage, disability percentage.

Source: ACS for poverty, income, age, and disability in the current run.

Directionality: higher poverty, older adult share, and disability increase risk; lower median household income increases risk.

Weight in final score: 25%.

Rationale: affordability, disability access, aging, and income constraints can shape whether residents can obtain timely care.

### Insurance And Access Burden

Variables: uninsured percentage, no-vehicle household percentage, no-internet household percentage.

Source: ACS.

Directionality: higher uninsured, no-vehicle, and no-internet percentages increase risk.

Weight in final score: 20%.

Rationale: insurance coverage, transportation, and digital access are practical barriers to appointment scheduling, telehealth, follow-up, and routine care.

### Chronic Disease Burden

Variables: diabetes, obesity, high blood pressure, poor/fair health, current smoking, frequent physical distress.

Source: CDC PLACES.

Directionality: higher values increase risk.

Weight in final score: 25%.

Rationale: chronic disease prevalence can indicate higher demand for preventive, primary, and ongoing care.

### Provider Shortage Burden

Variables: HRSA primary care HPSA score/count, mental health HPSA score/count, dental HPSA score/count, and fallback provider rates per 100,000 residents.

Source: HRSA HPSA public downloads plus documented provider-rate fallback fields.

Directionality: higher HPSA scores/counts increase risk; lower provider rates increase risk.

Weight in final score: 20%.

Rationale: formal shortage-area designations are strong public-health planning signals for access constraints.

### Hospital Availability/Quality Burden

Variables: CMS hospital count, acute-care count, emergency services count, average hospital rating, fallback hospital beds, and readmission proxy.

Source: CMS Hospital General Information plus documented fallback fields for beds/readmission.

Directionality: lower hospital availability/rating increases risk; higher readmission proxy increases risk.

Weight in final score: 10%.

Rationale: hospitals are not the only access channel, but acute-care availability and quality context are relevant to county-level access planning.

## Normalization

The pipeline uses min-max scaling to convert indicators with different units into a common 0-100 scale:

```text
scaled_value = ((county_value - minimum_county_value) / (maximum_county_value - minimum_county_value)) * 100
```

For measures where higher raw values are better, such as hospital rating or provider supply, the scaled value is inverted:

```text
inverted_scaled_value = 100 - scaled_value
```

After transformation, higher component values consistently mean higher access-related risk or burden.

Limitations: min-max scaling is sensitive to the set of counties and to outliers. It produces a relative Maryland comparison, not an absolute national benchmark.

## Score Formula

```text
access_risk_score =
    socioeconomic_need_index * 0.25
  + insurance_access_burden_index * 0.20
  + chronic_burden_index * 0.25
  + provider_gap_index * 0.20
  + hospital_quality_gap_index * 0.10
```

These weights are transparent assumptions. They are chosen to balance affordability/social vulnerability, practical access barriers, chronic disease demand, provider shortage, and hospital context. A production version should review weights with public-health leaders, community stakeholders, clinicians, and healthcare operations teams.

## Machine Learning Target

The model target hierarchy is:

1. HRSA provider shortage burden, when available
2. High poor/fair health rate from CDC PLACES
3. High uninsured rate from ACS
4. Demo rule-derived access-risk target as last fallback

The current default target is `high_hrsa_provider_shortage_burden`, with target mode `independent_external`. It labels counties in the top quartile of a HRSA HPSA score/count burden index. HPSA-derived predictor fields are excluded from the model inputs when this target is used.

This target is stronger than a score-derived demo label because it comes from an external public source, but it is still a county-level proxy. It is not a validated outcome.

## Future Validated Outcome

A future production model should validate against an observed external outcome not constructed inside this project, such as:

- Avoidable emergency department visits
- Preventable hospitalizations
- Ambulatory care sensitive admissions
- Appointment wait times
- Unmet care due to cost
- Preventable hospital stays from an official public source

## Ethical Limitations

- No patient-level data is used.
- County averages can hide neighborhood-level inequities.
- Demographic fields should be used for descriptive equity review, not causal claims.
- Fallback fields must be replaced or reviewed before operational use.
- Perfect or near-perfect metrics can occur with small county-level datasets and should not be interpreted as validated predictive performance.
- The dashboard is a planning and communication artifact, not a clinical, eligibility, or resource-denial tool.
