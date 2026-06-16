# Future Real-Data Upgrade Plan

This project now attempts real public county-level data by default and uses documented fallback fields where public feeds do not provide an equivalent measure. The current run uses ACS, CDC PLACES, HRSA HPSA, and CMS Hospital General Information data with remaining sample fallback fields. A production-quality version should replace those fallback fields with official public datasets, preserve source lineage, and validate the risk score against an external outcome.

## U.S. Census ACS County Demographics

**What it provides**

ACS 5-year data provides county-level population, income, poverty, age, health insurance, education, housing, and demographic estimates.

**Why it matters**

Healthcare access is shaped by affordability, insurance coverage, age structure, and socioeconomic conditions. ACS gives the core denominator and context variables needed for county comparisons.

**How it would improve the project**

It would replace sample demographic fields with official estimates and allow consistent year-over-year refreshes.

**Feeds these tables or feature groups**

- `demographics`
- `socioeconomic_need_index`
- County denominators for provider and hospital rates

Official source: https://www.census.gov/data/developers/data-sets/acs-5year.html

## CDC PLACES Chronic Disease Indicators

**What it provides**

CDC PLACES provides local estimates for chronic disease prevalence, health outcomes, prevention measures, health behaviors, and health status.

**Why it matters**

Chronic disease burden increases demand for primary care, specialty care, medication access, prevention, and care coordination.

**How it would improve the project**

It would replace sample chronic disease fields with official county-level estimates for diabetes, obesity, hypertension, poor/fair health, and related indicators.

**Feeds these tables or feature groups**

- `health_outcomes`
- `chronic_burden_index`
- Dashboard outcome charts

Official source: https://www.cdc.gov/places/

## HRSA HPSA / Provider Shortage Data

**What it provides**

HRSA shortage-area data identifies primary care, dental, and mental health professional shortage areas and related shortage scores.

**Why it matters**

Provider availability is one of the most direct healthcare access signals. Shortage-area data helps distinguish counties with provider scarcity or unmet workforce need.

**How it would improve the project**

It would replace sample HPSA scores and strengthen the provider access component with official shortage-area designations.

**Feeds these tables or feature groups**

- `provider_shortages`
- `provider_gap_index`
- `provider_access_index`

Official source: https://data.hrsa.gov/topics/health-workforce/shortage-areas

## County Health Rankings

**What it provides**

County Health Rankings includes county-level health outcomes, clinical care measures, social and economic factors, and physical environment indicators.

**Why it matters**

It offers a broad public-health benchmark for comparing counties and can provide measures such as preventable hospital stays, premature death, and clinical care access.

**How it would improve the project**

It would support external validation, benchmark comparisons, and stronger county-level outcome measures.

**Feeds these tables or feature groups**

- `health_outcomes`
- `provider_shortages`
- `chronic_burden_index`
- Future validation target

Official source: https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation

## CMS Hospital Quality Or Provider Data

**What it provides**

CMS Provider Data includes hospital facility information, quality measures, ratings, readmission measures, and related provider datasets.

**Why it matters**

Hospital capacity and quality are not the whole access picture, but they help describe the acute-care environment and potential care continuity issues.

**How it would improve the project**

It would replace sample hospital star rating, readmission, hospital count, and capacity-related fields with official facility measures.

**Feeds these tables or feature groups**

- `hospital_quality`
- `hospital_quality_gap_index`
- Dashboard hospital quality charts

Official source: https://data.cms.gov/provider-data/

## Maryland Open Data / Maryland Department Of Health

**What it provides**

Maryland public data sources can provide state-specific public health indicators, facility information, utilization measures, vital statistics, or program-level data when available at the county level.

**Why it matters**

State-specific sources can add local context that national datasets may not capture, such as Maryland-specific public-health programs, county reporting definitions, or state facility metadata.

**How it would improve the project**

It would make the dashboard more Maryland-specific and could support operationally relevant outcomes or validation measures.

**Feeds these tables or feature groups**

- `health_outcomes`
- `hospital_quality`
- Future validation target
- Future trend analysis

Official source: https://opendata.maryland.gov/

## Recommended Production Build Order

1. Replace demographics with ACS county estimates.
2. Replace chronic burden measures with CDC PLACES.
3. Add HRSA HPSA shortage-area indicators.
4. Add CMS hospital quality/facility indicators.
5. Add County Health Rankings or Maryland public-health outcomes.
6. Select one external validation outcome.
7. Revisit score weights with stakeholders.
8. Add automated refresh scripts and data quality checks.
