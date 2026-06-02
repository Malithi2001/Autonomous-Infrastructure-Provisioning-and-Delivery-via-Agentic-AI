"""Train and report on the CI/CD failure classification model.

The MVP model uses TF-IDF features over raw CI/CD log text and a logistic
regression classifier. The script also compares a LinearSVC baseline, stores a
label-to-fix mapping, and writes reproducible evaluation reports.
"""
from __future__ import annotations

import json
import math
import struct
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


ML_DIR = Path(__file__).resolve().parent
DATASET_PATH = ML_DIR / "dataset.csv"
MODEL_PATH = ML_DIR / "failure_model.joblib"
FIX_MAPPING_PATH = ML_DIR / "fix_mapping.joblib"
REPORTS_DIR = ML_DIR / "reports"
METRICS_PATH = REPORTS_DIR / "metrics.json"
CLASSIFICATION_REPORT_PATH = REPORTS_DIR / "classification_report.txt"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.png"
MODEL_SUMMARY_PATH = REPORTS_DIR / "model_summary.md"

REQUIRED_COLUMNS = {"log_text", "label", "suggested_fix"}
RANDOM_STATE = 42
TEST_SIZE = 0.25


def load_dataset() -> pd.DataFrame:
    """Load, clean, and deduplicate the training dataset."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    df = df.fillna("")
    for column in REQUIRED_COLUMNS:
        df[column] = df[column].astype(str).str.strip()

    df = df[(df["log_text"] != "") & (df["label"] != "")]
    usable_row_count = len(df)
    df = df.drop_duplicates(subset=["log_text", "label", "suggested_fix"]).reset_index(drop=True)
    df.attrs["duplicates_removed"] = usable_row_count - len(df)
    if df.empty:
        raise ValueError("Dataset has no usable rows after preprocessing.")

    return df


def build_fix_mapping(df: pd.DataFrame) -> dict[str, str]:
    """Create one suggested fix per label from the dataset."""
    mapping: dict[str, str] = {}
    for label, group in df.groupby("label"):
        fixes = group["suggested_fix"][group["suggested_fix"] != ""]
        mapping[label] = fixes.iloc[0] if not fixes.empty else "Review the CI/CD logs for details."
    return mapping


def _can_stratify(labels: pd.Series) -> bool:
    """Return True when every class can appear in both train and test sets."""
    return labels.value_counts().min() >= 2


def _test_size_for(labels: pd.Series, stratify: bool) -> float | int:
    """Choose a safe test size, including for smaller class-balanced datasets."""
    if not stratify:
        return TEST_SIZE

    total_rows = len(labels)
    class_count = labels.nunique()
    test_rows = max(class_count, math.ceil(total_rows * TEST_SIZE))
    train_rows = total_rows - test_rows
    if train_rows < class_count:
        test_rows = max(1, total_rows - class_count)
    return test_rows


def split_dataset(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, bool]:
    """Split the dataset, using stratification when class counts allow it."""
    if len(df) < 2:
        raise ValueError("Dataset must contain at least two usable rows.")

    stratify = _can_stratify(df["label"])
    x_train, x_test, y_train, y_test = train_test_split(
        df["log_text"],
        df["label"],
        test_size=_test_size_for(df["label"], stratify),
        random_state=RANDOM_STATE,
        stratify=df["label"] if stratify else None,
    )
    return x_train, x_test, y_train, y_test, stratify


def _tfidf_step() -> tuple[str, TfidfVectorizer]:
    """Create the shared TF-IDF feature extraction step."""
    return (
        "tfidf",
        TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            stop_words="english",
        ),
    )


def build_logistic_regression_pipeline() -> Pipeline:
    """Build the production classifier with probability support."""
    return Pipeline(
        steps=[
            _tfidf_step(),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    solver="liblinear",
                ),
            ),
        ]
    )


def build_linear_svc_pipeline() -> Pipeline:
    """Build a LinearSVC baseline for comparison."""
    return Pipeline(
        steps=[
            _tfidf_step(),
            (
                "classifier",
                LinearSVC(
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    dual="auto",
                    max_iter=5000,
                ),
            ),
        ]
    )


def _evaluate_model(model: Pipeline, x_test: pd.Series, y_test: pd.Series) -> dict[str, Any]:
    """Return common classification metrics for a trained model."""
    predictions = model.predict(x_test)
    precision, recall, f1_score, _ = precision_recall_fscore_support(
        y_test,
        predictions,
        average="weighted",
        zero_division=0,
    )
    macro_precision, macro_recall, macro_f1_score, _ = precision_recall_fscore_support(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "weighted_precision": round(float(precision), 4),
        "weighted_recall": round(float(recall), 4),
        "weighted_f1": round(float(f1_score), 4),
        "macro_precision": round(float(macro_precision), 4),
        "macro_recall": round(float(macro_recall), 4),
        "macro_f1": round(float(macro_f1_score), 4),
    }


def _train_candidates(x_train: pd.Series, y_train: pd.Series) -> dict[str, Pipeline]:
    """Train the production model and an optional linear baseline."""
    candidates = {
        "logistic_regression": build_logistic_regression_pipeline(),
        "linear_svc": build_linear_svc_pipeline(),
    }
    for model in candidates.values():
        model.fit(x_train, y_train)
    return candidates


def _write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    """Write an RGB PNG without requiring matplotlib or Pillow."""
    raw_rows = []
    for y in range(height):
        start = y * width
        row = b"".join(bytes(pixel) for pixel in pixels[start:start + width])
        raw_rows.append(b"\x00" + row)

    def chunk(kind: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(raw_rows), level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def save_confusion_matrix_image(y_test: pd.Series, predictions: list[str], labels: list[str]) -> None:
    """Save a simple heatmap-style confusion matrix PNG."""
    matrix = confusion_matrix(y_test, predictions, labels=labels)
    cell_size = 34
    margin = 12
    width = margin * 2 + cell_size * len(labels)
    height = margin * 2 + cell_size * len(labels)
    pixels = [(248, 250, 252)] * (width * height)
    max_value = int(matrix.max()) or 1

    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            intensity = int(235 - (185 * int(value) / max_value))
            color = (intensity, intensity + 10, 255)
            x0 = margin + column_index * cell_size
            y0 = margin + row_index * cell_size
            for y in range(y0, y0 + cell_size - 1):
                for x in range(x0, x0 + cell_size - 1):
                    pixels[y * width + x] = color

    _write_png(CONFUSION_MATRIX_PATH, width, height, pixels)


def write_model_summary(metrics: dict[str, Any]) -> None:
    """Write a human-readable model evaluation summary for project evidence."""
    labels = metrics["labels"]
    model_metrics = metrics["models"]["logistic_regression"]
    summary = f"""# CI/CD Failure Classification Model Summary

## Model Type

The trained production model is a scikit-learn `Pipeline` with TF-IDF text
features and a balanced Logistic Regression classifier.

## Dataset Size

- Total usable examples: {metrics["dataset_size"]}
- Training examples: {metrics["train_size"]}
- Test examples: {metrics["test_size"]}
- Number of labels: {metrics["number_of_labels"]}

## Labels

{chr(10).join(f"- `{label}`" for label in labels)}

## Preprocessing

- Empty log text and empty labels are removed.
- `log_text`, `label`, and `suggested_fix` values are converted to stripped strings.
- Duplicate `(log_text, label, suggested_fix)` rows are removed.
- Text is vectorized with TF-IDF using lowercase normalization, English stop words, and 1-2 gram features.

## Train/Test Split

- Random state: {metrics["split"]["random_state"]}
- Stratified split used: {metrics["split"]["used_stratify"]}
- Test split target: {TEST_SIZE}

## Evaluation Metrics

| Metric | Value |
| --- | ---: |
| Accuracy | {model_metrics["accuracy"]:.4f} |
| Macro precision | {model_metrics["macro_precision"]:.4f} |
| Macro recall | {model_metrics["macro_recall"]:.4f} |
| Macro F1 | {model_metrics["macro_f1"]:.4f} |
| Weighted precision | {model_metrics["weighted_precision"]:.4f} |
| Weighted recall | {model_metrics["weighted_recall"]:.4f} |
| Weighted F1 | {model_metrics["weighted_f1"]:.4f} |

## Limitations

- The dataset is project-sized and synthetic/demo-oriented, so results should
  not be treated as production-grade reliability.
- CI/CD logs can contain project-specific tooling, secret redactions, and noisy
  output that may differ from the training examples.
- Some labels may have fewer examples than others, which can reduce recall for minority failure categories.
- The model predicts a likely failure category; human review is still needed before applying repository changes.

Generated at: {metrics["generated_at"]}
"""
    MODEL_SUMMARY_PATH.write_text(summary, encoding="utf-8")


def train_model(df: pd.DataFrame) -> tuple[Pipeline, dict[str, Any]]:
    """Train, compare, report, and return the production classifier."""
    x_train, x_test, y_train, y_test, used_stratify = split_dataset(df)
    candidates = _train_candidates(x_train, y_train)

    model_metrics = {
        name: _evaluate_model(model, x_test, y_test)
        for name, model in candidates.items()
    }

    production_model = candidates["logistic_regression"]
    predictions = list(production_model.predict(x_test))
    labels = sorted(df["label"].unique())
    report_text = classification_report(
        y_test,
        predictions,
        labels=labels,
        zero_division=0,
    )

    metrics = {
        "dataset_size": int(len(df)),
        "number_of_labels": int(len(labels)),
        "labels": labels,
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
        "accuracy": model_metrics["logistic_regression"]["accuracy"],
        "macro_precision": model_metrics["logistic_regression"]["macro_precision"],
        "macro_recall": model_metrics["logistic_regression"]["macro_recall"],
        "macro_f1": model_metrics["logistic_regression"]["macro_f1"],
        "weighted_precision": model_metrics["logistic_regression"]["weighted_precision"],
        "weighted_recall": model_metrics["logistic_regression"]["weighted_recall"],
        "weighted_f1": model_metrics["logistic_regression"]["weighted_f1"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(DATASET_PATH),
            "rows": int(len(df)),
            "labels": dict(sorted(Counter(df["label"]).items())),
            "duplicates_removed": int(df.attrs.get("duplicates_removed", 0)),
        },
        "split": {
            "random_state": RANDOM_STATE,
            "test_size": int(len(x_test)),
            "train_size": int(len(x_train)),
            "used_stratify": bool(used_stratify),
        },
        "models": model_metrics,
        "saved_model": "logistic_regression",
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CLASSIFICATION_REPORT_PATH.write_text(report_text, encoding="utf-8")
    save_confusion_matrix_image(y_test, predictions, labels)
    write_model_summary(metrics)

    lr_metrics = model_metrics["logistic_regression"]
    print("Logistic Regression")
    print(f"Accuracy: {lr_metrics['accuracy']:.4f}")
    print(f"Precision: {lr_metrics['weighted_precision']:.4f}")
    print(f"Recall: {lr_metrics['weighted_recall']:.4f}")
    print(f"F1-score: {lr_metrics['weighted_f1']:.4f}")
    print()
    print("Model comparison")
    for model_name, values in model_metrics.items():
        print(
            f"- {model_name}: accuracy={values['accuracy']:.4f}, "
            f"precision={values['weighted_precision']:.4f}, "
            f"recall={values['weighted_recall']:.4f}, "
            f"f1={values['weighted_f1']:.4f}"
        )
    print()
    print(report_text)

    return production_model, metrics


def main() -> None:
    """Train the model and persist artifacts next to this script."""
    df = load_dataset()
    model, _metrics = train_model(df)
    fix_mapping = build_fix_mapping(df)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(fix_mapping, FIX_MAPPING_PATH)

    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved fix mapping to: {FIX_MAPPING_PATH}")
    print(f"Saved metrics to: {METRICS_PATH}")
    print(f"Saved classification report to: {CLASSIFICATION_REPORT_PATH}")
    print(f"Saved confusion matrix to: {CONFUSION_MATRIX_PATH}")
    print(f"Saved model summary to: {MODEL_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
