from src.data_pipeline import REQUIRED_COLUMNS
from src.public_data_ingestion import build_sample_fallback


def test_public_ingestion_sample_fallback_schema():
    frame, provenance = build_sample_fallback("network unavailable in test")

    assert REQUIRED_COLUMNS.issubset(frame.columns)
    assert len(frame) == 24
    assert provenance["mode"] == "sample_fallback"
    assert provenance["project"] == "Maryland Healthcare Access Analytics"
    assert provenance["field_sources"]["county_fips"]["fallback_used"] is True
