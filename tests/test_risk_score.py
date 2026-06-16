from src.data_pipeline import run_pipeline


def test_risk_scores_are_between_zero_and_one_hundred():
    processed = run_pipeline()
    assert processed["access_risk_score"].between(0, 100).all()


def test_component_scores_are_between_zero_and_one_hundred():
    processed = run_pipeline()
    component_columns = [
        "provider_gap_index",
        "socioeconomic_need_index",
        "chronic_burden_index",
        "hospital_quality_gap_index",
    ]
    for column in component_columns:
        assert processed[column].between(0, 100).all()


def test_no_duplicate_county_year_rows():
    processed = run_pipeline()
    assert not processed.duplicated(["county_fips", "data_year"]).any()


def test_top_risk_factor_is_populated():
    processed = run_pipeline()
    assert processed["top_risk_factor"].notna().all()
    assert processed["top_risk_factor"].nunique() >= 2
