import sys
from pathlib import Path

# =========================================================
# PATH SETUP
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(BACKEND_DIR))


# =========================================================
# IMPORTS
# =========================================================

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    average_precision_score,
    roc_auc_score
)

from app.services.features import create_features


# =========================================================
# PATHS
# =========================================================

TRAIN_FILE = (
    BACKEND_DIR
    / "data"
    / "data"
    / "fraud_model"
    / "train.csv"
)

MODEL_PATH = (
    BACKEND_DIR
    / "models"
    / "fraud_model.pkl"
)

FEATURES_PATH = (
    BACKEND_DIR
    / "models"
    / "feature_columns.pkl"
)


# =========================================================
# START
# =========================================================

print("=" * 70)
print("FraudLens - Model Evaluation")
print("=" * 70)


# =========================================================
# CHECK FILES
# =========================================================

print("\nChecking required files...")

if not TRAIN_FILE.exists():
    print("\nERROR: train.csv not found.")
    print(f"Expected:\n{TRAIN_FILE}")
    sys.exit(1)

if not MODEL_PATH.exists():
    print("\nERROR: fraud_model.pkl not found.")
    print(f"Expected:\n{MODEL_PATH}")
    sys.exit(1)

if not FEATURES_PATH.exists():
    print("\nERROR: feature_columns.pkl not found.")
    print(f"Expected:\n{FEATURES_PATH}")
    sys.exit(1)

print("Training dataset : FOUND")
print("Trained model    : FOUND")
print("Feature columns  : FOUND")


# =========================================================
# LOAD MODEL
# =========================================================

print("\nLoading trained model...")

model = joblib.load(MODEL_PATH)

feature_columns = joblib.load(FEATURES_PATH)

print("Model loaded successfully.")


# =========================================================
# LOAD TRAIN DATA
# =========================================================

print("\nLoading labeled dataset...")

df = pd.read_csv(TRAIN_FILE)

print(f"Total rows: {len(df)}")


# =========================================================
# CHECK LABEL
# =========================================================

if "label" not in df.columns:

    print("\nERROR: label column not found.")

    sys.exit(1)


print("\nOriginal label distribution:")

print(df["label"].value_counts())


# =========================================================
# FEATURE ENGINEERING
# =========================================================

print("\n" + "=" * 70)
print("FEATURE ENGINEERING")
print("=" * 70)

print("\nCreating behavioral features...")

df = create_features(df)

print(
    f"Rows after feature engineering: {len(df)}"
)


# =========================================================
# CHRONOLOGICAL ORDER
# =========================================================

print("\nSorting chronologically...")

df = df.sort_values(
    "timestamp"
).reset_index(drop=True)


# =========================================================
# TARGET
# =========================================================

y = df["label"].astype(int)


# =========================================================
# REMOVE NON-MODEL COLUMNS
# =========================================================

drop_columns = [
    "transaction_id",
    "user_id",
    "device_id",
    "timestamp",
    "label",
    "previous_merchant_category",
    "previous_channel"
]

drop_columns = [
    column
    for column in drop_columns
    if column in df.columns
]

X = df.drop(
    columns=drop_columns
)


# =========================================================
# CATEGORICAL ENCODING
# =========================================================

categorical_columns = [
    "merchant_category",
    "country",
    "channel"
]

categorical_columns = [
    column
    for column in categorical_columns
    if column in X.columns
]

X = pd.get_dummies(
    X,
    columns=categorical_columns,
    dtype=int
)


# =========================================================
# MATCH TRAINING FEATURES
# =========================================================

X = X.reindex(
    columns=feature_columns,
    fill_value=0
)


# =========================================================
# CLEAN VALUES
# =========================================================

X = X.replace(
    [np.inf, -np.inf],
    0
)

X = X.fillna(0)


# =========================================================
# VALIDATION SPLIT
# =========================================================

print("\n" + "=" * 70)
print("VALIDATION SPLIT")
print("=" * 70)

# Last 20% = unseen validation data

split_index = int(
    len(X) * 0.80
)

X_validation = X.iloc[
    split_index:
]

y_validation = y.iloc[
    split_index:
]


print(
    f"\nTraining portion : {split_index}"
)

print(
    f"Validation rows  : {len(X_validation)}"
)

print(
    "\nValidation label distribution:"
)

print(
    y_validation.value_counts()
)


# =========================================================
# PREDICT
# =========================================================

print(
    "\nGenerating predictions..."
)

y_probability = model.predict_proba(
    X_validation
)[:, 1]


# =========================================================
# ROC-AUC
# =========================================================

roc_auc = roc_auc_score(
    y_validation,
    y_probability
)


# =========================================================
# PR-AUC
# =========================================================

pr_auc = average_precision_score(
    y_validation,
    y_probability
)


# =========================================================
# THRESHOLD ANALYSIS
# =========================================================

print(
    "\n" + "=" * 70
)

print(
    "THRESHOLD ANALYSIS"
)

print(
    "=" * 70
)


thresholds = [
    0.20,
    0.30,
    0.40,
    0.50,
    0.60,
    0.70,
    0.80
]


results = []


for threshold in thresholds:

    y_pred = (
        y_probability >= threshold
    ).astype(int)

    accuracy = accuracy_score(
        y_validation,
        y_pred
    )

    precision = precision_score(
        y_validation,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_validation,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_validation,
        y_pred,
        zero_division=0
    )

    results.append({

        "Threshold": threshold,

        "Accuracy": accuracy,

        "Precision": precision,

        "Recall": recall,

        "F1": f1
    })


results_df = pd.DataFrame(
    results
)


print()

print(
    results_df.to_string(
        index=False,
        formatters={
            "Threshold": "{:.2f}".format,
            "Accuracy": "{:.4f}".format,
            "Precision": "{:.4f}".format,
            "Recall": "{:.4f}".format,
            "F1": "{:.4f}".format
        }
    )
)


# =========================================================
# BEST F1 THRESHOLD
# =========================================================

best_row = results_df.loc[
    results_df["F1"].idxmax()
]

best_threshold = float(
    best_row["Threshold"]
)

best_f1 = float(
    best_row["F1"]
)


# =========================================================
# DEFAULT 0.50 EVALUATION
# =========================================================

DEFAULT_THRESHOLD = 0.50

y_pred = (
    y_probability >= DEFAULT_THRESHOLD
).astype(int)


# =========================================================
# CLASSIFICATION REPORT
# =========================================================

print(
    "\n" + "=" * 70
)

print(
    "CLASSIFICATION REPORT"
)

print(
    "=" * 70
)

print(
    classification_report(
        y_validation,
        y_pred,
        digits=4,
        zero_division=0
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_validation,
    y_pred
)


print(
    "\nConfusion Matrix:"
)

print(cm)


if cm.shape == (2, 2):

    tn, fp, fn, tp = cm.ravel()

    print(
        "\nConfusion Matrix Details:"
    )

    print(
        f"True Negatives  : {tn}"
    )

    print(
        f"False Positives : {fp}"
    )

    print(
        f"False Negatives : {fn}"
    )

    print(
        f"True Positives  : {tp}"
    )


# =========================================================
# FINAL METRICS
# =========================================================

accuracy = accuracy_score(
    y_validation,
    y_pred
)

precision = precision_score(
    y_validation,
    y_pred,
    zero_division=0
)

recall = recall_score(
    y_validation,
    y_pred,
    zero_division=0
)

f1 = f1_score(
    y_validation,
    y_pred,
    zero_division=0
)


# =========================================================
# FINAL RESULTS
# =========================================================

print(
    "\n" + "=" * 70
)

print(
    "FINAL MODEL METRICS"
)

print(
    "=" * 70
)

print(
    f"\nAccuracy  : {accuracy:.4f}"
)

print(
    f"Precision : {precision:.4f}"
)

print(
    f"Recall    : {recall:.4f}"
)

print(
    f"F1 Score  : {f1:.4f}"
)

print(
    f"PR-AUC    : {pr_auc:.4f}"
)

print(
    f"ROC-AUC   : {roc_auc:.4f}"
)


# =========================================================
# BEST THRESHOLD
# =========================================================

print(
    "\n" + "=" * 70
)

print(
    "BEST THRESHOLD"
)

print(
    "=" * 70
)

print(
    f"\nBest F1 threshold: {best_threshold:.2f}"
)

print(
    f"Best F1 score    : {best_f1:.4f}"
)


# =========================================================
# COMPLETED
# =========================================================

print(
    "\n" + "=" * 70
)

print(
    "EVALUATION COMPLETED"
)

print(
    "=" * 70
)