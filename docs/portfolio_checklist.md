# Portfolio Publishing Checklist

Use this checklist before publishing the project on GitHub, LinkedIn, a portfolio site, or a resume.

## GitHub Readiness

- [ ] README displays correctly on GitHub.
- [ ] Dashboard screenshots are real and not placeholders.
- [ ] Main dashboard screenshot appears near the top of the README.
- [ ] GitHub repository description is added.
- [ ] GitHub topics are added:
  - `healthcare-analytics`
  - `data-science`
  - `python`
  - `sql`
  - `sqlite`
  - `streamlit`
  - `machine-learning`
  - `public-health`
  - `responsible-ai`
  - `portfolio-project`
- [ ] Repository is pinned on GitHub.

## Reproducibility

- [ ] `requirements.txt` installs successfully in a clean virtual environment.
- [ ] Dashboard runs locally with `streamlit run dashboard/app.py`.
- [ ] Data pipeline runs with `python src/data_pipeline.py`.
- [ ] ML script runs with `python src/risk_model.py`.
- [ ] AI summary script runs with `python src/ai_summary.py`.
- [ ] SQLite database is generated in `data/processed/`.
- [ ] SQL files are documented and run successfully.
- [ ] No API keys, secrets, private files, or patient-level data are included.

## Documentation

- [ ] Data dictionary is complete.
- [ ] Methodology explains risk components, scaling, weights, and limitations.
- [ ] Executive summary reads like a professional public-health analytics brief.
- [ ] Data source docs identify real public sources and fallback fields.
- [ ] Screenshot guide is up to date.
- [ ] Interview talking points are ready for employer conversations.

## Responsible Use

- [ ] Model caveat is visible in `model_metrics.json`.
- [ ] Model caveat is visible in the dashboard.
- [ ] README states that this is not a clinical decision tool.
- [ ] README states the current `mixed_real_and_demo_data` status honestly.
- [ ] No claims imply validated public-health conclusions.

## Resume And Portfolio

- [ ] Strong general resume bullet is added to resume.
- [ ] Role-specific bullet is selected for target job.
- [ ] LinkedIn/GitHub portfolio description is added.
- [ ] Screenshots are added to portfolio page.
- [ ] Project is described as a real public-data analytics project with documented fallback fields.

## Final Pre-Publication Checklist

- [ ] Screenshots are real.
- [ ] Live dashboard link is updated or marked coming soon.
- [ ] `data/processed/run_metadata.json` records data mode and source coverage.
- [ ] ACS and CDC PLACES processed extracts are present.
- [ ] HRSA and CMS status is documented as real or fallback.
- [ ] `make all` passes.
- [ ] `pytest` passes.
- [ ] GitHub Actions badge works after push.
- [ ] After merging this branch, update the README GitHub Actions badge branch from `final-real-data-upgrade` to `main`.
- [ ] Repository description is updated.
- [ ] GitHub topics are added.
- [ ] Repository is renamed after review.
- [ ] Repository is pinned on GitHub.
- [ ] Resume bullet is added.
