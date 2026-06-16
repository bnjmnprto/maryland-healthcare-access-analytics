# Executive Summary: Maryland Healthcare Access Analytics

## Problem Statement

Healthcare access risk is shaped by overlapping factors: provider availability, insurance coverage, socioeconomic conditions, chronic disease burden, hospital capacity, and local context. A county may have strong hospital infrastructure but high uninsured rates, or relatively stable income levels but limited primary care and mental health provider supply. Public health leaders, healthcare organizations, and analytics teams need a practical way to identify where multiple access barriers appear to overlap.

This portfolio simulation asks: **which Maryland counties show elevated healthcare access risk signals when demographic need, provider access, chronic disease burden, and hospital quality/capacity indicators are evaluated together?**

The project is designed as an employer-facing analytics brief and dashboard for entry-level Data Analyst, Healthcare Data Analyst, Junior Data Scientist, AI/Data Analyst, and Analytics Engineer-adjacent roles. It emphasizes reproducible workflow design, transparent assumptions, and responsible communication rather than operational public-health claims.

## Methods

The repository includes a demonstration dataset with one row per Maryland county or county-equivalent jurisdiction. It also includes an optional public-data ingestion path for selected CDC PLACES, HRSA HPSA, and CMS Provider Data fields. The committed sample workflow mirrors the type of data structure that could be built from official public datasets such as U.S. Census ACS, CDC PLACES, HRSA shortage-area data, CMS Provider Data, County Health Rankings, Maryland Open Data, and Maryland Department of Health sources.

The analysis pipeline performs five core steps:

1. **Clean and validate county records.** County FIPS codes are standardized, required fields are checked, and numeric values are converted into analysis-ready columns.
2. **Engineer interpretable features.** Measures are grouped into four access risk components: provider access gap, socioeconomic need, chronic disease burden, and hospital quality/capacity gap.
3. **Normalize indicators.** Min-max scaling converts different units into comparable 0-100-style scores. Measures where higher values are better, such as provider supply or hospital star rating, are inverted so higher component scores consistently indicate greater risk.
4. **Calculate an access risk score.** The final score weights provider access gap at 35%, socioeconomic need at 25%, chronic disease burden at 25%, and hospital quality/capacity gap at 15%.
5. **Publish analytics outputs.** The pipeline writes dashboard-ready CSV files, a normalized SQLite database, SQL query outputs, model artifacts, and plain-English county summaries.

The machine learning workflow trains logistic regression and random forest models. By default, it uses an external-proxy target based on high poor/fair health rate rather than a label derived from the access risk score. The script also supports a separate score-derived demo mode. This modeling step demonstrates a data science workflow, but it is not a validated predictive model.

## Data Limitations

This project uses a demonstration dataset so the repository can run locally without credentials, paid services, or large downloads. The values are illustrative. They should not be interpreted as official public-health findings, operational surveillance results, or validated county rankings.

Key limitations:

- The committed default data is a sample portfolio dataset, not a fully refreshed official data extract.
- The optional live ingestion script fills selected fields from public feeds and retains documented sample fallback values for fields not covered by those feeds.
- County-level averages can hide neighborhood-level inequities and rural access barriers.
- The risk score is a transparent prioritization heuristic, not a causal model.
- The default machine learning target is an external-proxy sample target, not a validated operational outcome.
- The analysis does not include patient-level data, appointment availability, network adequacy, transportation times, language access, disability access, or community input.

## Key Findings From The Sample Dataset

Within the demonstration dataset, the counties with the highest access risk scores are those where multiple risk drivers overlap. Somerset, Dorchester, Caroline, Allegany, Garrett, and Wicomico appear near the top of the sample risk ranking. These counties combine signals such as higher socioeconomic need, stronger provider gap indicators, higher chronic disease burden, and weaker hospital quality/capacity measures.

Baltimore City also shows elevated risk in the sample workflow, primarily because of high socioeconomic need and chronic disease burden. This illustrates an important point for healthcare analytics: access risk can emerge from different local profiles. A rural county may be flagged because provider supply and travel burden are central concerns, while an urban jurisdiction may be flagged because poverty, insurance coverage, chronic disease prevalence, and hospital utilization pressures are more prominent.

The county comparison tool reinforces that counties should not be treated as interchangeable. Two counties can have similar total risk scores but different intervention needs. One may need workforce recruitment or mobile care access; another may need insurance enrollment support, chronic disease prevention, or community-based care coordination.

## Public-Health Interpretation

The dashboard should be interpreted as a triage and communication tool. It helps analysts identify where to ask better questions, where to compare counties against state averages, and where to investigate the mix of access barriers.

The sample workflow suggests that a useful public-health access review should separate at least three questions:

- Is the primary barrier related to provider availability and shortage-area signals?
- Is the primary barrier related to affordability, poverty, or insurance coverage?
- Is the county also carrying a high chronic disease or preventable utilization burden?

This distinction matters because different risk profiles imply different next steps. Provider scarcity may point toward workforce incentives, telehealth, transportation support, or mobile clinics. High uninsured rates may point toward enrollment outreach and affordability programs. High chronic disease burden may point toward prevention, primary care continuity, and community health worker models.

## Recommended Next Steps

1. **Replace remaining sample fallback values with official public datasets.** Use ACS county demographics, CDC PLACES chronic disease indicators, HRSA HPSA/provider shortage data, CMS hospital quality data, County Health Rankings, and Maryland public health sources.
2. **Add data lineage.** Document extract dates, source URLs, table IDs, variable names, and refresh schedules.
3. **Validate against an external outcome.** Use preventable hospitalizations, avoidable emergency department visits, ambulatory care sensitive condition admissions, appointment wait times, or unmet care due to cost.
4. **Expand geography.** Keep the county choropleth and add sub-county geographies where privacy, data quality, and source availability allow.
5. **Add trend analysis.** Multiple years would allow monitoring whether access risk is improving or worsening.
6. **Review weights with stakeholders.** Public-health leaders, community representatives, clinicians, and operations teams should review whether the component weights match the intended use case.
7. **Document equity considerations.** Add checks for whether county averages hide disparities by geography, language, disability, income, race/ethnicity, or insurance type.

## Responsible-Use Warning

This dashboard is not a clinical decision tool. It does not diagnose patients, predict individual outcomes, determine eligibility, or justify denial of services. It uses aggregate county-level indicators and should support planning conversations only.

The model metrics should not be overinterpreted. Strong metrics in this project reflect a small demonstration dataset and either an external-proxy sample target or an optional score-derived demo target. They show that the code path works; they do not prove that the model can predict real-world healthcare access outcomes.

## Future Production Version

A production version would replace the demonstration dataset with official public datasets and validate the workflow against an independently observed outcome. It would include automated source refreshes, data quality tests, transparent versioning, uncertainty checks, and a stakeholder-reviewed scoring methodology.

The strongest next validation target would be county-level preventable hospitalizations or avoidable emergency department utilization from an official source. That outcome would allow the team to test whether the access risk score identifies counties with measurable access-related utilization burden, rather than only reproducing a rule-based score.

Used responsibly, this project demonstrates how a healthcare analyst can combine public data, SQL, Python, machine learning workflow, dashboard design, and executive communication into a practical analytics product while staying honest about limitations.
