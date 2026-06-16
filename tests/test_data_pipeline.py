from pathlib import Path
import json

import pandas as pd

from src.data_pipeline import PROCESSED_DIR, RAW_DATA_PATH, REQUIRED_COLUMNS, RUN_METADATA_PATH, run_pipeline
from src.validate_data import MARYLAND_COUNTY_FIPS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_project_files_exist():
    required_files = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "sql" / "schema.sql",
        PROJECT_ROOT / "sql" / "queries.sql",
        PROJECT_ROOT / "dashboard" / "app.py",
        PROJECT_ROOT / "data" / "raw" / "maryland_counties.geojson",
        RAW_DATA_PATH,
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    assert not missing


def test_raw_data_has_required_columns():
    raw = pd.read_csv(RAW_DATA_PATH, dtype={"county_fips": str})
    assert REQUIRED_COLUMNS.issubset(raw.columns)


def test_pipeline_represents_all_maryland_jurisdictions():
    processed = run_pipeline()
    fips = set(processed["county_fips"].astype(str).str.zfill(5))
    assert fips == MARYLAND_COUNTY_FIPS
    assert len(processed) == 24
    assert "Baltimore City" in set(processed["county_name"])


def test_run_metadata_and_feature_table_are_created():
    run_pipeline()
    feature_table = PROCESSED_DIR / "healthcare_access_features.csv"
    assert feature_table.exists()
    assert RUN_METADATA_PATH.exists()

    metadata = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["data_mode"] in {
        "real_public_data",
        "mixed_real_and_demo_data",
        "demo_sample_data",
    }
    assert metadata["maryland_jurisdictions_represented"] == 24
    assert metadata["all_24_jurisdictions_present"] is True
    assert "sources_successfully_loaded" in metadata


def test_dashboard_and_documentation_dependencies_exist():
    required_files = [
        PROCESSED_DIR / "dashboard_county_risk.csv",
        PROCESSED_DIR / "run_metadata.json",
        PROJECT_ROOT / "docs" / "data_sources.md",
        PROJECT_ROOT / "docs" / "data_provenance.md",
        PROJECT_ROOT / "reports" / "data_quality_report.md",
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    assert not missing
