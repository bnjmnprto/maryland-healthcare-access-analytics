"""Train beginner-friendly models for healthcare access risk signals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FEATURE_TABLE_PATH = PROCESSED_DIR / "model_feature_table.csv"
MODEL_PATH = PROCESSED_DIR / "access_risk_model.joblib"
METRICS_PATH = PROCESSED_DIR / "model_metrics.json"

DEMONSTRATION_WARNING = (
    "These metrics reflect a small demonstration dataset and a rule-derived target. "
    "They should not be interpreted as validated predictive performance."
)
EXTERNAL_PROXY_WARNING = (
    "These metrics use an external-proxy target from the demonstration dataset. "
    "They validate the modeling workflow, not real-world predictive performance. "
    "Replace the sample data with official public datasets before operational use."
)


FEATURE_COLUMNS = [
    "poverty_pct",
    "uninsured_pct",
    "pct_age_65_plus",
    "primary_care_physicians_per_100k",
    "mental_health_providers_per_100k",
    "dental_providers_per_100k",
    "hpsa_primary_care_score",
    "hpsa_mental_health_score",
    "diabetes_pct",
    "obesity_pct",
    "hypertension_pct",
    "poor_or_fair_health_pct",
    "preventable_hospital_stays_per_100k",
    "avg_hospital_star_rating",
    "readmission_rate_pct",
]


TARGET_MODES = {
    "external_proxy": {
        "target": "high_poor_or_fair_health_rate",
        "source_column": "poor_or_fair_health_pct",
        "source_feature_exclusions": ["poor_or_fair_health_pct"],
        "description": (
            "High poor/fair health rate based on the top quartile of the county-level "
            "poor_or_fair_health_pct field. This is an external-proxy target because it "
            "is not derived from the project access risk score, but the included values "
            "are still sample data."
        ),
        "source": (
            "Portfolio sample field modeled after CDC PLACES / County Health Rankings-style "
            "poor-or-fair-health estimates. Replace with official public data for production."
        ),
        "is_rule_derived_target": False,
        "warning": EXTERNAL_PROXY_WARNING,
    },
    "demo_score": {
        "target": "high_access_risk",
        "source_column": "high_access_risk",
        "source_feature_exclusions": [],
        "description": (
            "High access risk label derived from the project access_risk_score top quartile. "
            "Use this only to demonstrate the modeling workflow."
        ),
        "source": "Rule-derived label from src/data_pipeline.py.",
        "is_rule_derived_target": True,
        "warning": DEMONSTRATION_WARNING,
    },
}


def load_feature_table(path: Path = FEATURE_TABLE_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Feature table not found at {path}. Run `python src/data_pipeline.py` first."
        )
    return pd.read_csv(path, dtype={"county_fips": str})


def build_models(random_state: int = 42) -> dict[str, Pipeline | RandomForestClassifier]:
    logistic = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    forest = RandomForestClassifier(
        n_estimators=300,
        max_depth=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
    )
    return {"logistic_regression": logistic, "random_forest": forest}


def build_target(feature_table: pd.DataFrame, target_mode: str) -> tuple[pd.Series, dict]:
    if target_mode not in TARGET_MODES:
        choices = ", ".join(sorted(TARGET_MODES))
        raise ValueError(f"Unknown target mode '{target_mode}'. Choose one of: {choices}")

    target_config = TARGET_MODES[target_mode].copy()
    source_column = target_config["source_column"]
    if source_column not in feature_table.columns:
        raise ValueError(f"Target source column '{source_column}' is not present in the feature table.")

    if target_mode == "external_proxy":
        cutoff = feature_table[source_column].quantile(0.75)
        y = (feature_table[source_column] >= cutoff).astype(int)
        target_config["cutoff"] = round(float(cutoff), 3)
        return y, target_config

    y = feature_table[source_column].astype(int)
    target_config["cutoff"] = "Top quartile of access_risk_score from data pipeline"
    return y, target_config


def feature_columns_for_target(target_config: dict) -> list[str]:
    exclusions = set(target_config.get("source_feature_exclusions", []))
    return [column for column in FEATURE_COLUMNS if column not in exclusions]


def evaluate_model(model, x_test: pd.DataFrame, y_test: pd.Series) -> dict:
    predictions = model.predict(x_test)
    probabilities = (
        model.predict_proba(x_test)[:, 1] if hasattr(model, "predict_proba") else predictions
    )
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="binary", zero_division=0
    )

    try:
        roc_auc = roc_auc_score(y_test, probabilities)
    except ValueError:
        roc_auc = None

    return {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 3),
        "precision": round(float(precision), 3),
        "recall": round(float(recall), 3),
        "f1": round(float(f1), 3),
        "roc_auc": None if roc_auc is None else round(float(roc_auc), 3),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": classification_report(
            y_test, predictions, zero_division=0, output_dict=True
        ),
    }


def should_warn_about_metrics(results: dict[str, dict]) -> bool:
    """Flag metrics that look deployment-ready on a sample that is not validation-ready."""
    near_perfect_threshold = 0.95
    for metrics in results.values():
        tracked_values = [
            metrics.get("accuracy"),
            metrics.get("precision"),
            metrics.get("recall"),
            metrics.get("f1"),
            metrics.get("roc_auc"),
        ]
        numeric_values = [value for value in tracked_values if value is not None]
        if numeric_values and max(numeric_values) >= near_perfect_threshold:
            return True
    return False


def extract_feature_interpretation(
    model, model_name: str, feature_columns: list[str]
) -> pd.DataFrame:
    if model_name == "random_forest":
        values = model.feature_importances_
        interpretation = pd.DataFrame(
            {"feature": feature_columns, "importance": values, "direction": "nonlinear"}
        )
        return interpretation.sort_values("importance", ascending=False)

    coefficients = model.named_steps["model"].coef_[0]
    interpretation = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": abs(coefficients),
            "direction": ["increases risk" if value > 0 else "decreases risk" for value in coefficients],
            "coefficient": coefficients,
        }
    )
    return interpretation.sort_values("importance", ascending=False)


def train_and_evaluate(
    feature_table: pd.DataFrame,
    random_state: int = 42,
    target_mode: str = "external_proxy",
) -> dict:
    y, target_config = build_target(feature_table, target_mode)
    feature_columns = feature_columns_for_target(target_config)
    x = feature_table[feature_columns]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.30,
        random_state=random_state,
        stratify=y,
    )

    results = {}
    fitted_models = {}
    for model_name, model in build_models(random_state).items():
        model.fit(x_train, y_train)
        results[model_name] = evaluate_model(model, x_test, y_test)
        fitted_models[model_name] = model

    selected_model_name = max(results, key=lambda name: results[name]["f1"])
    selected_model = fitted_models[selected_model_name]

    probabilities = selected_model.predict_proba(x)[:, 1]
    predictions = selected_model.predict(x)
    prediction_frame = feature_table[["county_fips", "county_name", "access_risk_score"]].copy()
    prediction_frame["target_mode"] = target_mode
    prediction_frame["target"] = target_config["target"]
    prediction_frame["actual_target"] = y
    prediction_frame["predicted_target"] = predictions
    prediction_frame["predicted_target_probability"] = probabilities.round(3)
    prediction_frame["predicted_high_risk"] = predictions
    prediction_frame["predicted_high_risk_probability"] = probabilities.round(3)

    interpretation = extract_feature_interpretation(selected_model, selected_model_name, feature_columns)

    payload = {
        "selected_model": selected_model_name,
        "target": target_config["target"],
        "target_mode": target_mode,
        "target_description": target_config["description"],
        "target_source": target_config["source"],
        "target_cutoff": target_config["cutoff"],
        "is_rule_derived_target": target_config["is_rule_derived_target"],
        "feature_columns": feature_columns,
        "warning": target_config["warning"] if should_warn_about_metrics(results) else "",
        "evaluation_note": (
            "Small county-level sample used for a portfolio demonstration. Metrics are useful "
            "for workflow validation, not for operational performance claims."
        ),
        "models": results,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected_model, MODEL_PATH)
    prediction_frame.to_csv(PROCESSED_DIR / "model_predictions.csv", index=False)
    interpretation.to_csv(PROCESSED_DIR / "feature_importance.csv", index=False)
    METRICS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature-table",
        type=Path,
        default=FEATURE_TABLE_PATH,
        help="Processed feature table generated by the data pipeline.",
    )
    parser.add_argument(
        "--target-mode",
        choices=sorted(TARGET_MODES),
        default="external_proxy",
        help=(
            "external_proxy uses high poor/fair health as a non-score-derived target; "
            "demo_score uses the rule-derived high_access_risk label."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    feature_table = load_feature_table(args.feature_table)
    metrics = train_and_evaluate(feature_table, target_mode=args.target_mode)
    selected = metrics["selected_model"]
    print("Model training completed.")
    print(f"Selected model: {selected}")
    print(f"Target mode: {metrics['target_mode']}")
    print(f"Target: {metrics['target']}")
    print(f"Metrics file: {METRICS_PATH}")
    print(json.dumps(metrics["models"][selected], indent=2))


if __name__ == "__main__":
    main()
