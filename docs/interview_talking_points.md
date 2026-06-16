# Interview Talking Points

## 30-Second Explanation

I built Maryland Healthcare Access Analytics, a public-health analytics project for Maryland counties using Python, SQL, SQLite, scikit-learn, and Streamlit. The project cleans county-level healthcare and demographic data, supports optional public-data ingestion with sample fallback, engineers interpretable risk indicators, stores the data in a SQLite database, runs SQL analysis, trains demonstration ML models, and presents the results in an interactive dashboard with responsible-use caveats.

## 2-Minute Explanation

This project is a healthcare analytics portfolio simulation focused on county-level access risk in Maryland. I created a reproducible workflow that starts with a stable sample CSV by default, includes optional live ingestion for selected public sources, validates and cleans county records, engineers four access risk components, and calculates a transparent risk score.

The four components are provider access gap, socioeconomic need, chronic disease burden, and hospital quality/capacity gap. I then publish the outputs to a normalized SQLite database and dashboard-ready CSV files. The SQL layer answers questions like which counties have the highest risk, which combine poverty and uninsured burden with poor provider access, and how counties compare to the state average.

For machine learning, I trained logistic regression and random forest models using a default external-proxy target: counties in the top quartile of poor/fair health rate. I also support a separate demo mode that uses a score-derived target. I explicitly document that both modes are demonstration-oriented because the dataset is small and sample-based. The dashboard includes model results, feature importance, county comparison tools, and template-based plain-English summaries that do not require an API key.

The main thing I wanted to show is that I can build an end-to-end healthcare analytics project while communicating clearly and avoiding overclaims.

## Technical Explanation

- `src/data_pipeline.py` loads the raw county-level sample, validates required columns, standardizes FIPS codes, creates min-max scaled features, calculates composite risk components, writes processed CSVs, and populates SQLite tables.
- `sql/schema.sql` defines the database tables: counties, demographics, health outcomes, provider shortages, hospital quality, and access risk scores.
- `sql/queries.sql` answers portfolio-ready healthcare analytics questions using joins and state-average comparisons.
- `src/risk_model.py` trains logistic regression and random forest models, supports external-proxy and demo target modes, exports metrics, predictions, feature importance, and a warning when metrics look too strong for the demonstration setting.
- `src/ai_summary.py` creates template-based county summaries without requiring an API key.
- `dashboard/app.py` presents the workflow in Streamlit using tabs for overview, risk ranking, county comparison, model results, county summaries, and responsible-use notes.

## Healthcare / Business Explanation

The business question is: where do healthcare access barriers appear to overlap at the county level? This matters because healthcare organizations and public-health teams often need to prioritize limited outreach, workforce, prevention, or care coordination resources.

The project helps separate different types of need. A county may have high chronic disease burden, low provider availability, high uninsured rates, or weaker hospital quality/capacity indicators. Those profiles imply different interventions, so the dashboard is designed to support discussion rather than produce a single black-box answer.

## What I Would Improve In A Production Version

- Replace remaining sample fallback fields with official public data extracts.
- Automate source refreshes and log extract dates.
- Validate the risk score against an external outcome such as preventable hospitalizations, avoidable emergency department use, ambulatory care sensitive admissions, appointment wait times, or unmet care due to cost.
- Expand maps with sub-county views where data quality and privacy rules allow, and add multi-year trend analysis.
- Add data quality tests and source-specific data dictionaries.
- Review risk score weights with public-health stakeholders.
- Add equity checks for neighborhood-level variation, language access, disability access, transportation burden, and insurance network adequacy.

## How I Used AI Responsibly

The AI-style summary module is template-based by default. It does not require an API key, does not send data to a paid API, and uses only aggregate county-level metrics. I also documented how future OpenAI integration should be treated as an optional extension that requires organizational review, careful prompt design, and no patient-level data.

The project uses AI assistance as a communication layer, not as a substitute for public-health judgment.

## Why The ML Metrics Should Not Be Overinterpreted

The default target is not derived from the project risk score; it is based on the top quartile of poor/fair health rate. That is a better portfolio target, but it is still built from sample data and only 24 county rows. The optional `demo_score` mode is explicitly score-derived and should only be used to demonstrate workflow mechanics.

Perfect or near-perfect metrics show that the code path works, but they do not prove validated predictive performance. In a production model, I would use an external outcome such as preventable hospitalizations or avoidable emergency department visits and validate across multiple years.

## Connection To Healthcare Data Analyst Roles

This project maps well to healthcare data analyst work because it combines:

- Public-health data interpretation
- SQL querying and database design
- Data cleaning and reproducible pipelines
- Dashboarding for nontechnical stakeholders
- Clear documentation of assumptions and limitations
- Responsible handling of aggregate health data
- Communication of findings without overclaiming

## Likely Employer Questions And Strong Answers

### Why did you choose these four risk components?

They cover access supply, socioeconomic barriers, care demand, and facility context. Provider access is weighted most heavily because the project is focused on access risk. Socioeconomic need and chronic burden are also important because affordability and disease burden can drive delayed care and preventable utilization.

### Is this model ready for deployment?

No. The model is demonstration-oriented. The default target is an external-proxy sample target, and the optional demo target is score-derived. The workflow is useful for showing feature engineering, modeling, evaluation, and dashboard integration, but production use would require official data and external validation.

### What outcome would you use for validation?

I would start with preventable hospitalizations or avoidable emergency department visits, ideally county-level and multi-year. Those outcomes are more directly connected to healthcare access barriers than a rule-derived label.

### How did you avoid overclaiming?

I labeled the sample data as illustrative, documented responsible-use limitations, added a dashboard warning for near-perfect metrics, and wrote the executive summary as a portfolio simulation rather than an operational public-health report.

### What is the strongest part of this project?

The strongest part is the end-to-end structure: raw data, processed outputs, SQLite schema, SQL queries, feature engineering, ML workflow, dashboard, summary module, documentation, and executive communication all connect into one reproducible project.

### What would you do next?

I would replace remaining sample fallback fields with official ACS, CDC PLACES, HRSA, CMS, County Health Rankings, and Maryland public health extracts; harden the source refresh script; validate against preventable hospitalizations; and add trend analysis.
