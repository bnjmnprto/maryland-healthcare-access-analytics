"""Train beginner-friendly models for county-level healthcare access signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
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
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FEATURE_TABLE_PATH = PROCESSED_DIR / "model_feature_table.csv"
MODEL_PATH = PROCESSED_DIR / "access_risk_model.joblib"
METRICS_PATH = PROCESSED_DIR / "model_metrics.json"
DEFAULT_RANDOM_STATE = 42
EVALUATION_TEST_SIZE = 0.30
SELECTED_MODEL_NAME = "logistic_regression"

PERFECT_OR_NEAR_PERFECT_WARNING = (
    "Perfect or near-perfect metrics can occur with small county-level datasets and should "
    "not be interpreted as validated predictive performance."
)
DEMONSTRATION_WARNING = (
    "This target is derived from the project risk score and is included only as a last-resort "
    "workflow demonstration. It should not be interpreted as validated predictive performance."
)
EXTERNAL_PROXY_WARNING = (
    "This target is an external proxy from public aggregate data. It supports workflow "
    "demonstration, not validated operational prediction."
)


BASE_FEATURE_COLUMNS = [
    "poverty_pct",
    "median_household_income",
    "uninsured_pct",
    "pct_age_65_plus",
    "disability_pct",
    "transportation_access_proxy",
    "internet_access_gap_pct",
    "primary_care_physicians_per_100k",
    "mental_health_providers_per_100k",
    "dental_providers_per_100k",
    "hpsa_primary_care_score",
    "hpsa_primary_care_count",
    "hpsa_primary_care_designated",
    "hpsa_mental_health_score",
    "hpsa_mental_health_count",
    "hpsa_mental_health_designated",
    "hpsa_dental_score",
    "hpsa_dental_count",
    "hpsa_dental_designated",
    "hospital_count",
    "acute_care_hospitals",
    "emergency_services_count",
    "avg_hospital_star_rating",
    "hospital_count_per_100k",
    "diabetes_pct",
    "obesity_pct",
    "hypertension_pct",
    "poor_or_fair_health_pct",
    "smoking_pct",
    "frequent_physical_distress_pct",
    "routine_checkup_pct",
    "socioeconomic_need_index",
    "insurance_access_burden_index",
    "chronic_burden_index",
    "hospital_quality_gap_index",
]

HPSA_FEATURES = {
    "hpsa_primary_care_score",
    "hpsa_primary_care_count",
    "hpsa_primary_care_designated",
    "hpsa_mental_health_score",
    "hpsa_mental_health_count",
    "hpsa_mental_health_designated",
    "hpsa_dental_score",
    "hpsa_dental_count",
    "hpsa_dental_designated",
    "primary_care_physicians_per_100k",
    "mental_health_providers_per_100k",
    "dental_providers_per_100k",
}


def load_feature_table(path: Path = FEATURE_TABLE_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Feature table not found at {path}. Run `python src/data_pipeline.py` first."
        )
    return pd.read_csv(path, dtype={"county_fips": str})


def min_max_scale(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    span = numeric.max() - numeric.min()
    if pd.isna(span) or span == 0:
        return pd.Series(50.0, index=series.index)
    return ((numeric - numeric.min()) / span) * 100


def build_models(random_state: int = DEFAULT_RANDOM_STATE) -> dict[str, Pipeline | RandomForestClassifier]:
    logistic = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=random_state,
                ),
            ),
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


def _top_quartile_target(feature_table: pd.DataFrame, column: str) -> tuple[pd.Series, float]:
    cutoff = float(feature_table[column].quantile(0.75))
    return (feature_table[column] >= cutoff).astype(int), round(cutoff, 3)


def _has_real_source(feature_table: pd.DataFrame, source_column: str) -> bool:
    return source_column in feature_table.columns and feature_table[source_column].eq("real_public_data").any()


def _hrsa_burden(feature_table: pd.DataFrame) -> pd.Series:
    components = []
    for column in [
        "hpsa_primary_care_score",
        "hpsa_primary_care_count",
        "hpsa_mental_health_score",
        "hpsa_mental_health_count",
        "hpsa_dental_score",
        "hpsa_dental_count",
    ]:
        if column in feature_table.columns:
            components.append(min_max_scale(feature_table[column]))
    if not components:
        return pd.Series(dtype=float)
    return pd.concat(components, axis=1).mean(axis=1)


def build_target(feature_table: pd.DataFrame, target_mode: str = "auto") -> tuple[pd.Series, dict]:
    if target_mode == "demo_score":
        target_mode = "demo_rule_derived"

    if target_mode in {"auto", "independent_external"} and _has_real_source(
        feature_table, "source_hrsa_hpsa"
    ):
        burden = _hrsa_burden(feature_table)
        if not burden.empty and burden.nunique() > 1:
            cutoff = float(burden.quantile(0.75))
            y = (burden >= cutoff).astype(int)
            if y.nunique() == 2:
                return y, {
                    "target": "high_hrsa_provider_shortage_burden",
                    "target_mode": "independent_external",
                    "source_column": "hrsa_hpsa_count_score_burden",
                    "source_feature_exclusions": sorted(HPSA_FEATURES),
                    "description": (
                        "High HRSA provider-shortage burden based on the top quartile of county "
                        "HPSA score/count burden. HPSA-derived predictor fields are excluded to "
                        "avoid silently training on the target inputs."
                    ),
                    "source": "HRSA HPSA public downloads aggregated to Maryland county FIPS.",
                    "cutoff": round(cutoff, 3),
                    "is_rule_derived_target": False,
                    "warning": EXTERNAL_PROXY_WARNING,
                }

    if target_mode in {"auto", "external_proxy"} and "poor_or_fair_health_pct" in feature_table:
        y, cutoff = _top_quartile_target(feature_table, "poor_or_fair_health_pct")
        return y, {
            "target": "high_poor_or_fair_health_rate",
            "target_mode": "external_proxy",
            "source_column": "poor_or_fair_health_pct",
            "source_feature_exclusions": ["poor_or_fair_health_pct"],
            "description": (
                "High poor/fair health rate based on the top quartile of CDC PLACES county "
                "poor_or_fair_health_pct."
            ),
            "source": "CDC PLACES public county-level poor/fair health indicator.",
            "cutoff": cutoff,
            "is_rule_derived_target": False,
            "warning": EXTERNAL_PROXY_WARNING,
        }

    if target_mode in {"auto", "mixed_proxy"} and "uninsured_pct" in feature_table:
        y, cutoff = _top_quartile_target(feature_table, "uninsured_pct")
        return y, {
            "target": "high_uninsured_rate",
            "target_mode": "mixed_proxy",
            "source_column": "uninsured_pct",
            "source_feature_exclusions": ["uninsured_pct", "insurance_access_burden_index"],
            "description": "High uninsured rate based on the top quartile of ACS uninsured_pct.",
            "source": "U.S. Census ACS uninsured estimate.",
            "cutoff": cutoff,
            "is_rule_derived_target": False,
            "warning": EXTERNAL_PROXY_WARNING,
        }

    if target_mode in {"auto", "demo_rule_derived"} and "high_access_risk" in feature_table:
        y = feature_table["high_access_risk"].astype(int)
        return y, {
            "target": "high_access_risk",
            "target_mode": "demo_rule_derived",
            "source_column": "high_access_risk",
            "source_feature_exclusions": [],
            "description": (
                "High access risk label derived from the project access_risk_score top quartile. "
                "Use this only to demonstrate the modeling workflow."
            ),
            "source": "Rule-derived label from src/data_pipeline.py.",
            "cutoff": "Top quartile of access_risk_score from data pipeline",
            "is_rule_derived_target": True,
            "warning": DEMONSTRATION_WARNING,
        }

    raise ValueError("No usable target could be built from the feature table.")


def feature_columns_for_target(feature_table: pd.DataFrame, target_config: dict) -> list[str]:
    exclusions = set(target_config.get("source_feature_exclusions", []))
    return [
        column
        for column in BASE_FEATURE_COLUMNS
        if column in feature_table.columns and column not in exclusions
    ]


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


def cross_validation_summary(model, x: pd.DataFrame, y: pd.Series, random_state: int) -> dict:
    class_counts = y.value_counts()
    min_class_count = int(class_counts.min())
    if min_class_count < 3:
        return {
            "enabled": False,
            "reason": "Too few positive or negative examples for stable stratified cross-validation.",
        }

    n_splits = min(3, min_class_count)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = cross_val_score(model, x, y, cv=cv, scoring="accuracy")
    return {
        "enabled": True,
        "n_splits": n_splits,
        "scoring": "accuracy",
        "scores": [round(float(score), 3) for score in scores],
        "mean_accuracy": round(float(np.mean(scores)), 3),
        "std_accuracy": round(float(np.std(scores)), 3),
    }


def should_warn_about_metrics(results: dict[str, dict]) -> bool:
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


def build_warning(target_config: dict, results: dict[str, dict]) -> str:
    warnings = []
    if should_warn_about_metrics(results):
        warnings.append(PERFECT_OR_NEAR_PERFECT_WARNING)
    if target_config.get("warning"):
        warnings.append(target_config["warning"])
    return " ".join(warnings)


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
            "direction": ["increases target likelihood" if value > 0 else "decreases target likelihood" for value in coefficients],
            "coefficient": coefficients,
        }
    )
    return interpretation.sort_values("importance", ascending=False)


def train_and_evaluate(
    feature_table: pd.DataFrame,
    random_state: int = DEFAULT_RANDOM_STATE,
    target_mode: str = "auto",
) -> dict:
    y, target_config = build_target(feature_table, target_mode)
    feature_columns = feature_columns_for_target(feature_table, target_config)
    x = feature_table[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0)

    stratify = y if y.nunique() == 2 and y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=EVALUATION_TEST_SIZE,
        random_state=random_state,
        stratify=stratify,
    )

    results = {}
    fitted_models = {}
    cv_results = {}
    for model_name, model in build_models(random_state).items():
        model.fit(x_train, y_train)
        results[model_name] = evaluate_model(model, x_test, y_test)
        cv_results[model_name] = cross_validation_summary(model, x, y, random_state)
        fitted_models[model_name] = model

    selected_model_name = SELECTED_MODEL_NAME
    selected_model = fitted_models[selected_model_name]

    probabilities = selected_model.predict_proba(x)[:, 1]
    predictions = selected_model.predict(x)
    prediction_frame = feature_table[["county_fips", "county_name", "access_risk_score"]].copy()
    prediction_frame["target_mode"] = target_config["target_mode"]
    prediction_frame["target"] = target_config["target"]
    prediction_frame["actual_target"] = y
    prediction_frame["predicted_target"] = predictions
    prediction_frame["predicted_target_probability"] = probabilities.round(3)
    prediction_frame["predicted_high_risk"] = predictions
    prediction_frame["predicted_high_risk_probability"] = probabilities.round(3)

    interpretation = extract_feature_interpretation(selected_model, selected_model_name, feature_columns)

    payload = {
        "selected_model": selected_model_name,
        "model_name": selected_model_name,
        "target": target_config["target"],
        "target_name": target_config["target"],
        "target_mode": target_config["target_mode"],
        "target_description": target_config["description"],
        "target_source": target_config["source"],
        "target_cutoff": target_config["cutoff"],
        "is_rule_derived_target": target_config["is_rule_derived_target"],
        "feature_columns": feature_columns,
        "excluded_target_source_features": target_config.get("source_feature_exclusions", []),
        "warning": build_warning(target_config, results),
        "evaluation_note": (
            "Small county-level dataset used for a portfolio demonstration. Metrics are useful "
            "for workflow validation, not for operational performance claims."
        ),
        "evaluation_design": {
            "test_size": EVALUATION_TEST_SIZE,
            "random_state": random_state,
            "stratified_split": stratify is not None,
            "cross_validation": cv_results,
            "selection_policy": (
                "Selected logistic_regression intentionally for reproducibility; "
                "random_forest is retained as a comparison model."
            ),
        },
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
        choices=["auto", "independent_external", "external_proxy", "mixed_proxy", "demo_rule_derived"],
        default="auto",
        help="auto uses the best available non-circular target, preferring HRSA provider shortage.",
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
