# Dashboard Screenshot Guide

Before publishing the project on GitHub, LinkedIn, or a portfolio website, capture a small set of dashboard screenshots that show the actual working dashboard.

## Required Screenshots

1. `docs/images/dashboard_overview.png`
   - Show the Overview tab with headline metrics, data mode, source coverage, and jurisdiction coverage.
   - If space allows, include the top of the risk ranking chart below the data-mode section.
   - Use the default filters so all counties are visible.

2. `docs/images/risk_ranking.png`
   - Show the Risk Ranking tab with the county table and risk driver profile chart.

3. `docs/images/county_comparison.png`
   - Show the County Comparison tab.
   - Recommended comparison: a high-risk county against a lower-risk county.

4. `docs/images/model_results.png`
   - Show the Model Results tab with metrics, the model warning, and feature importance chart.
   - The warning should be visible so reviewers understand the modeling caveat.

5. `docs/images/responsible_use.png`
   - Show the Responsible Use tab.
   - This is useful for healthcare employers because it demonstrates awareness of ethical and operational limits.

6. `docs/images/data_sources_quality.png`
   - Show the Data Sources / Data Quality tab with data mode, source coverage, fallback fields, and source-status table.

7. `docs/images/map.png`
   - Show the dedicated Map tab with the Maryland county choropleth.
   - Hover details should include county name, risk score, risk tier, and top risk factor when interacting with the dashboard.

## Optional Screenshot

- `docs/images/county_summary.png`
  - Show the County Summary tab for one county with a clear plain-English summary.
  - Recommended sample county: Somerset, Dorchester, or Baltimore City.

## Capture Tips

- Run `streamlit run dashboard/app.py` locally before capturing screenshots.
- Use a desktop browser width around 1280-1440 pixels so charts and tabs are readable.
- Avoid screenshots that include browser bookmarks, personal information, or unrelated desktop windows.
- Keep filenames lowercase and stable so the README links do not break.
- After adding screenshots, update the README image links if the filenames differ.

## README Image Links

The README includes image references for:

- `docs/images/dashboard_overview.png`
- `docs/images/risk_ranking.png`
- `docs/images/county_comparison.png`
- `docs/images/map.png`
- `docs/images/model_results.png`
- `docs/images/data_sources_quality.png`
- `docs/images/responsible_use.png`

These files should contain real Streamlit screenshots before publishing.
