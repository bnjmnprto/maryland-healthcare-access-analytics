from pathlib import Path

import pandas as pd

from src.data_pipeline import RAW_DATA_PATH, REQUIRED_COLUMNS, run_pipeline
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
