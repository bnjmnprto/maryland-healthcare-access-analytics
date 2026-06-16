import json
from pathlib import Path

from src.data_pipeline import run_pipeline
from src.risk_model import (
    METRICS_PATH,
    MODEL_PATH,
    PERFECT_OR_NEAR_PERFECT_WARNING,
    build_target,
    load_feature_table,
    train_and_evaluate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_model_metrics_are_created_for_best_available_target():
    run_pipeline()
    feature_table = load_feature_table()
    metrics = train_and_evaluate(feature_table, target_mode="auto")

    assert METRICS_PATH.exists()
    assert MODEL_PATH.exists()
    assert metrics["target_mode"] in {
        "independent_external",
        "external_proxy",
        "mixed_proxy",
        "demo_rule_derived",
    }
    assert metrics["target_name"] == metrics["target"]
    assert metrics["is_rule_derived_target"] is False
    assert metrics["selected_model"] == "logistic_regression"
    assert metrics["model_name"] == "logistic_regression"
    assert metrics["evaluation_design"]["random_state"] == 42
    assert metrics["evaluation_design"]["stratified_split"] is True
    assert "cross_validation" in metrics["evaluation_design"]
    assert PERFECT_OR_NEAR_PERFECT_WARNING in metrics["warning"]

    saved_metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    assert saved_metrics["target_mode"] == metrics["target_mode"]
    assert "models" in saved_metrics


def test_auto_target_prefers_hrsa_when_available():
    run_pipeline()
    feature_table = load_feature_table()
    _, target_config = build_target(feature_table, "auto")

    assert target_config["target_mode"] == "independent_external"
    assert target_config["target"] == "high_hrsa_provider_shortage_burden"
    assert "hpsa_primary_care_score" in target_config["source_feature_exclusions"]


def test_demo_score_target_is_explicitly_rule_derived():
    run_pipeline()
    feature_table = load_feature_table()
    _, target_config = build_target(feature_table, "demo_score")

    assert target_config["target"] == "high_access_risk"
    assert target_config["is_rule_derived_target"] is True


def test_model_prediction_output_exists():
    run_pipeline()
    feature_table = load_feature_table()
    train_and_evaluate(feature_table, target_mode="auto")
    prediction_path = PROJECT_ROOT / "data" / "processed" / "model_predictions.csv"
    assert prediction_path.exists()


def test_model_metrics_are_reproducible_across_runs():
    run_pipeline()
    feature_table = load_feature_table()

    first = train_and_evaluate(feature_table, target_mode="auto")
    second = train_and_evaluate(feature_table, target_mode="auto")

    assert first["selected_model"] == second["selected_model"] == "logistic_regression"
    assert first["models"]["logistic_regression"] == second["models"]["logistic_regression"]
    assert first["target_mode"] == second["target_mode"]
