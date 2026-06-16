# Data Dictionary

This dictionary covers the final feature table: `data/processed/healthcare_access_features.csv`.

Risk direction means whether higher values generally increase risk, decrease risk, or are descriptive in this project.

| Column | Definition | Type | Source | Expected range | Risk direction | Notes |
|---|---|---|---|---|---|---|
| `data_year` | Primary data year used for the row | integer | ACS release year / fallback | 2000+ | Descriptive | Current ACS release year when available |
| `county_fips` | Five-character county-equivalent FIPS code | text | FIPS / source scaffold | 5 chars | Descriptive | Includes Baltimore City `24510` |
| `county_name` | Maryland jurisdiction name | text | Source scaffold | 24 names | Descriptive | 23 counties plus Baltimore City |
| `region` | Maryland region grouping | text | Sample fallback | category | Descriptive | Planning label |
| `population` | Total population | integer | ACS | 0+ | Descriptive | ACS B01003 |
| `median_household_income` | Median household income in dollars | float | ACS | 0+ | Decreases risk | Inverted in socioeconomic component |
| `poverty_pct` | Population below poverty percentage | float | ACS | 0-100 | Increases risk | ACS B17001 |
| `uninsured_pct` | Population without health insurance percentage | float | ACS | 0-100 | Increases risk | ACS B27010 |
| `pct_age_65_plus` | Population age 65+ percentage | float | ACS | 0-100 | Increases risk | ACS B01001 |
| `pct_nonwhite` | Nonwhite population percentage | float | Sample fallback | 0-100 | Descriptive | Included for equity context, not causal claims |
| `rural_flag` | Rural county indicator | integer | Sample fallback | 0 or 1 | Descriptive | Planning context |
| `primary_care_physicians_per_100k` | Primary care physician rate | float | Sample fallback | 0+ | Decreases risk | Lower values increase provider gap |
| `mental_health_providers_per_100k` | Mental health provider rate | float | Sample fallback | 0+ | Decreases risk | Lower values increase provider gap |
| `dental_providers_per_100k` | Dental provider rate | float | Sample fallback | 0+ | Decreases risk | Lower values increase provider gap |
| `hospital_beds_per_1000` | Hospital beds per 1,000 residents | float | Sample fallback | 0+ | Decreases risk | Lower values increase hospital burden |
| `readmission_rate_pct` | Readmission-rate proxy | float | Sample fallback | 0-100 | Increases risk | Kept as fallback because CMS feed lacks county rate |
| `diabetes_pct` | Diabetes prevalence | float | CDC PLACES | 0-100 | Increases risk | Crude prevalence |
| `obesity_pct` | Obesity prevalence | float | CDC PLACES | 0-100 | Increases risk | Crude prevalence |
| `hypertension_pct` | High blood pressure prevalence | float | CDC PLACES | 0-100 | Increases risk | CDC `bphigh_crudeprev` |
| `poor_or_fair_health_pct` | Poor/fair self-rated health prevalence | float | CDC PLACES | 0-100 | Increases risk | Used as fallback target if HRSA unavailable |
| `preventable_hospital_stays_per_100k` | Preventable stays proxy | float | Sample fallback | 0+ | Increases risk | Production version should replace with official source |
| `life_expectancy` | Life expectancy in years | float | Sample fallback | 0+ | Decreases risk | Descriptive outcome context |
| `acs_source_year` | ACS release years | text | ACS | text | Descriptive | Example: `2020-2024` |
| `age_65_plus_pct` | Alias for age 65+ percentage | float | ACS | 0-100 | Increases risk | Dashboard/model-friendly duplicate |
| `disability_pct` | Civilian noninstitutionalized population with disability | float | ACS | 0-100 | Increases risk | ACS B18101 |
| `transportation_access_proxy` | Households with no vehicle available | float | ACS | 0-100 | Increases risk | ACS B08201 |
| `internet_access_gap_pct` | Households with no internet access | float | ACS | 0-100 | Increases risk | ACS B28002 |
| `high_blood_pressure_pct` | High blood pressure prevalence alias | float | CDC PLACES | 0-100 | Increases risk | Same source as `hypertension_pct` |
| `smoking_pct` | Current smoking prevalence | float | CDC PLACES | 0-100 | Increases risk | Crude prevalence |
| `frequent_physical_distress_pct` | Frequent physical distress prevalence | float | CDC PLACES | 0-100 | Increases risk | Crude prevalence |
| `routine_checkup_pct` | Routine checkup prevalence | float | CDC PLACES | 0-100 | Usually decreases risk | Kept as context, not currently weighted |
| `places_uninsured_pct` | CDC PLACES access-to-care uninsured proxy | float | CDC PLACES | 0-100 | Increases risk | ACS uninsured is preferred in final score |
| `hpsa_primary_care_count` | Count of designated primary care HPSA records | integer | HRSA HPSA | 0+ | Increases risk | Aggregated to county FIPS |
| `hpsa_primary_care_designated` | Primary care HPSA designation flag | integer | HRSA HPSA | 0 or 1 | Increases risk | 1 if any designation exists |
| `hpsa_mental_health_count` | Count of designated mental health HPSA records | integer | HRSA HPSA | 0+ | Increases risk | Aggregated to county FIPS |
| `hpsa_mental_health_designated` | Mental health HPSA designation flag | integer | HRSA HPSA | 0 or 1 | Increases risk | 1 if any designation exists |
| `hpsa_dental_count` | Count of designated dental HPSA records | integer | HRSA HPSA | 0+ | Increases risk | Aggregated to county FIPS |
| `hpsa_dental_score` | Maximum dental HPSA score | float | HRSA HPSA | 0+ | Increases risk | Higher score means greater shortage |
| `hpsa_dental_designated` | Dental HPSA designation flag | integer | HRSA HPSA | 0 or 1 | Increases risk | 1 if any designation exists |
| `hrsa_date_accessed` | HRSA access date | text | HRSA HPSA | ISO date | Descriptive | Source audit field |
| `source_hrsa_hpsa` | HRSA source status | text | Pipeline metadata | status | Descriptive | `real_public_data` or fallback |
| `hpsa_primary_care_score` | Maximum primary care HPSA score | float | HRSA HPSA | 0+ | Increases risk | Higher score means greater shortage |
| `hpsa_mental_health_score` | Maximum mental health HPSA score | float | HRSA HPSA | 0+ | Increases risk | Higher score means greater shortage |
| `hospital_count` | CMS hospital facility count | float | CMS | 0+ | Decreases risk | Lower count per population increases burden |
| `emergency_services_count` | Hospitals reporting emergency services | float | CMS | 0+ | Decreases risk | Lower count per population increases burden |
| `readmission_worse_measure_count` | CMS worse readmission measure count proxy | float | CMS | 0+ | Increases risk | Proxy, not a true county readmission rate |
| `cms_date_accessed` | CMS access date | text | CMS | ISO date | Descriptive | Source audit field |
| `source_cms_hospital_quality` | CMS source status | text | Pipeline metadata | status | Descriptive | `real_public_data` or fallback |
| `acute_care_hospitals` | Acute-care hospital count | float | CMS | 0+ | Decreases risk | Lower count increases hospital burden |
| `avg_hospital_star_rating` | Average CMS overall hospital rating | float | CMS | 0-5 | Decreases risk | Inverted in hospital component |
| `source_acs` | ACS source status | text | Pipeline metadata | status | Descriptive | `real_public_data` or fallback |
| `source_cdc_places` | CDC source status | text | Pipeline metadata | status | Descriptive | `real_public_data` or fallback |
| `data_mode` | Run mode | text | Pipeline metadata | enum | Descriptive | `real_public_data`, `mixed_real_and_demo_data`, or `demo_sample_data` |
| `fallback_fields_note` | Fields using sample fallback | text | Pipeline metadata | text | Descriptive | Explains non-public fallback fields |
| `hospital_count_per_100k` | Hospital count per 100,000 residents | float | CMS + ACS | 0+ | Decreases risk | Lower values increase hospital burden |
| `emergency_services_per_100k` | Emergency-service hospital count per 100,000 residents | float | CMS + ACS | 0+ | Decreases risk | Lower values increase hospital burden |
| `primary_care_gap` | Scaled inverted primary care provider rate | float | Derived | 0-100 | Increases risk | Higher means lower provider supply |
| `mental_health_gap` | Scaled inverted mental health provider rate | float | Derived | 0-100 | Increases risk | Higher means lower provider supply |
| `dental_gap` | Scaled inverted dental provider rate | float | Derived | 0-100 | Increases risk | Higher means lower provider supply |
| `hpsa_primary_need` | Scaled primary care HPSA need | float | Derived from HRSA | 0-100 | Increases risk | Min-max scaled |
| `hpsa_mental_need` | Scaled mental health HPSA need | float | Derived from HRSA | 0-100 | Increases risk | Min-max scaled |
| `hpsa_dental_need` | Scaled dental HPSA need | float | Derived from HRSA | 0-100 | Increases risk | Min-max scaled |
| `hpsa_designation_burden` | Scaled count of HPSA designation types | float | Derived from HRSA | 0-100 | Increases risk | Primary, mental, dental flags summed |
| `provider_gap_index` | Provider shortage burden component | float | Derived | 0-100 | Increases risk | Weighted HPSA and provider-rate gap |
| `provider_shortage_burden_index` | Alias for provider gap index | float | Derived | 0-100 | Increases risk | Dashboard/model-friendly duplicate |
| `provider_access_index` | Provider access index | float | Derived | 0-100 | Decreases risk | `100 - provider_gap_index` |
| `socioeconomic_need_index` | Socioeconomic vulnerability component | float | Derived | 0-100 | Increases risk | Poverty, income, age, disability |
| `insurance_access_burden_index` | Insurance/transportation/digital access component | float | Derived | 0-100 | Increases risk | ACS uninsured, no vehicle, no internet |
| `chronic_burden_index` | Chronic disease burden component | float | Derived | 0-100 | Increases risk | CDC PLACES indicators |
| `hospital_quality_gap_index` | Hospital availability/quality burden component | float | Derived | 0-100 | Increases risk | CMS + fallback hospital fields |
| `hospital_availability_quality_burden_index` | Alias for hospital quality gap | float | Derived | 0-100 | Increases risk | Dashboard/model-friendly duplicate |
| `access_risk_score` | Overall access risk score | float | Derived | 0-100 | Increases risk | Weighted component index |
| `high_access_risk` | High access risk demo label | integer | Derived | 0 or 1 | Increases risk | Top quartile of score |
| `access_risk_tier` | Risk category | text | Derived | Low/Moderate/Elevated/High | Increases risk | Based on fixed score bins |
| `top_risk_factor` | Highest risk component label | text | Derived | category | Descriptive | Used in dashboard and summaries |
