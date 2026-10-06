import sys
from pathlib import Path

# =========================================================
# MAKE BACKEND DIRECTORY AVAILABLE FOR IMPORTS
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(BACKEND_DIR)
)


# =========================================================
# IMPORTS
# =========================================================

import joblib
import pandas as pd

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    average_precision_score,
    roc_auc_score
)

from xgboost import XGBClassifier

from app.services.features import create_features


# =========================================================
# PATHS
# =========================================================

# Current dataset location:
#
# backend/
# └── data/
#     └── data/
#         └── fraud_model/
#             ├── train.csv
#             ├── test.csv
#             └── sample_submission.csv

TRAIN_FILE = (
    BACKEND_DIR
    / "data"
    / "data"
    / "fraud_model"
    / "train.csv"
)

# Models will be saved here:
#
# backend/
# └── models/
#     ├── fraud_model.pkl
#     └── feature_columns.pkl

MODEL_DIR = (
    BACKEND_DIR
    / "models"
)

MODEL_DIR.mkdir(
    exist_ok=True
)


# =========================================================
# START
# =========================================================

print("=" * 60)
print("FraudLens - Fraud Model Training")
print("=" * 60)


# =========================================================
# CHECK DATASET
# =========================================================

print("\nChecking dataset...")

if not TRAIN_FILE.exists():

    print("\nERROR: Training dataset not found.")

    print(
        f"Expected location:\n{TRAIN_FILE}"
    )

    sys.exit(1)


print(
    f"Dataset found:\n{TRAIN_FILE}"
)


# =========================================================
# LOAD DATASET
# =========================================================

print("\nLoading dataset...")

df = pd.read_csv(
    TRAIN_FILE
)

print(
    f"Raw rows: {len(df)}"
)

print(
    f"Raw columns: {len(df.columns)}"
)

print("\nColumns:")

print(
    list(df.columns)
)


# =========================================================
# CHECK TARGET
# =========================================================

if "label" not in df.columns:

    print(
        "\nERROR: 'label' column not found."
    )

    sys.exit(1)


print("\nOriginal label distribution:")

print(
    df["label"].value_counts()
)


# =========================================================
# FEATURE ENGINEERING
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "FEATURE ENGINEERING"
)

print(
    "=" * 60
)

print(
    "\nCreating behavioral features..."
)

df = create_features(
    df
)

print(
    f"\nRows after feature engineering: {len(df)}"
)

print(
    f"Columns after feature engineering: {len(df.columns)}"
)


# =========================================================
# SORT CHRONOLOGICALLY
# =========================================================

print(
    "\nSorting transactions chronologically..."
)

df = df.sort_values(
    "timestamp"
).reset_index(
    drop=True
)


# =========================================================
# TARGET
# =========================================================

print(
    "\nPreparing target..."
)

y = df["label"].astype(int)


# =========================================================
# REMOVE NON-MODEL COLUMNS
# =========================================================

print(
    "\nPreparing feature matrix..."
)

drop_columns = [
    "transaction_id",
    "user_id",
    "device_id",
    "timestamp",
    "label",
    "previous_merchant_category",
    "previous_channel"
]

# Only remove columns that actually exist

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

print(
    "\nEncoding categorical features..."
)

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
# CLEAN FEATURE VALUES
# =========================================================

print(
    "\nCleaning feature values..."
)

X = X.replace(
    [float("inf"), float("-inf")],
    0
)

X = X.fillna(0)


# =========================================================
# CHECK FEATURE MATRIX
# =========================================================

print(
    f"\nFinal feature count: {X.shape[1]}"
)

print(
    f"Final dataset shape: {X.shape}"
)


# =========================================================
# TRAIN / TEST SPLIT
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "TRAIN / TEST SPLIT"
)

print(
    "=" * 60
)

# Chronological split:
#
# First 80%  -> training
# Last 20%   -> testing
#
# This is better for behavioral fraud detection
# because we want to test on later transactions.

split_index = int(
    len(X) * 0.80
)

X_train = X.iloc[
    :split_index
]

X_test = X.iloc[
    split_index:
]

y_train = y.iloc[
    :split_index
]

y_test = y.iloc[
    split_index:
]


print(
    f"\nTraining rows: {len(X_train)}"
)

print(
    f"Testing rows : {len(X_test)}"
)


# =========================================================
# LABEL DISTRIBUTION
# =========================================================

print(
    "\nTraining label distribution:"
)

print(
    y_train.value_counts()
)

print(
    "\nTesting label distribution:"
)

print(
    y_test.value_counts()
)


print(
    "\nTraining fraud rate:"
)

print(
    f"{y_train.mean():.4f}"
)

print(
    "\nTesting fraud rate:"
)

print(
    f"{y_test.mean():.4f}"
)


# =========================================================
# HANDLE CLASS IMBALANCE
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "CLASS IMBALANCE"
)

print(
    "=" * 60
)

fraud_count = int(
    y_train.sum()
)

normal_count = (
    len(y_train)
    - fraud_count
)


if fraud_count == 0:

    print(
        "\nERROR: No fraud transactions found in training data."
    )

    sys.exit(1)


scale_pos_weight = (
    normal_count
    / fraud_count
)


print(
    f"\nNormal transactions: {normal_count}"
)

print(
    f"Fraud transactions : {fraud_count}"
)

print(
    f"scale_pos_weight    : {scale_pos_weight:.2f}"
)


# =========================================================
# XGBOOST MODEL
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "XGBOOST MODEL"
)

print(
    "=" * 60
)


model = XGBClassifier(

    n_estimators=300,

    max_depth=6,

    learning_rate=0.05,

    subsample=0.8,

    colsample_bytree=0.8,

    objective="binary:logistic",

    eval_metric="aucpr",

    scale_pos_weight=scale_pos_weight,

    random_state=42,

    n_jobs=-1
)


# =========================================================
# TRAIN MODEL
# =========================================================

print(
    "\nTraining XGBoost..."
)

model.fit(
    X_train,
    y_train
)


print(
    "\nTraining completed successfully."
)


# =========================================================
# PREDICTION
# =========================================================

print(
    "\nGenerating predictions..."
)

y_probability = model.predict_proba(
    X_test
)[:, 1]


# =========================================================
# CLASSIFICATION THRESHOLD
# =========================================================

THRESHOLD = 0.50

y_pred = (
    y_probability >= THRESHOLD
).astype(int)


# =========================================================
# MODEL EVALUATION
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "MODEL EVALUATION"
)

print(
    "=" * 60
)


# ---------------------------------------------------------
# CLASSIFICATION REPORT
# ---------------------------------------------------------

print(
    "\nClassification Report:"
)

print(
    classification_report(
        y_test,
        y_pred,
        digits=4,
        zero_division=0
    )
)


# ---------------------------------------------------------
# CONFUSION MATRIX
# ---------------------------------------------------------

print(
    "\nConfusion Matrix:"
)

cm = confusion_matrix(
    y_test,
    y_pred
)

print(
    cm
)


# ---------------------------------------------------------
# PR-AUC
# ---------------------------------------------------------

pr_auc = average_precision_score(
    y_test,
    y_probability
)


# ---------------------------------------------------------
# ROC-AUC
# ---------------------------------------------------------

roc_auc = roc_auc_score(
    y_test,
    y_probability
)


print(
    f"\nPR-AUC : {pr_auc:.4f}"
)

print(
    f"ROC-AUC: {roc_auc:.4f}"
)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "TOP FEATURE IMPORTANCE"
)

print(
    "=" * 60
)


feature_importance = pd.DataFrame({

    "feature": X.columns,

    "importance": model.feature_importances_

})


feature_importance = (
    feature_importance
    .sort_values(
        "importance",
        ascending=False
    )
)


print(
    feature_importance
    .head(20)
    .to_string(index=False)
)


# =========================================================
# SAVE MODEL
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "SAVING MODEL"
)

print(
    "=" * 60
)


model_path = (
    MODEL_DIR
    / "fraud_model.pkl"
)

features_path = (
    MODEL_DIR
    / "feature_columns.pkl"
)


# Save trained model

joblib.dump(
    model,
    model_path
)


# Save exact feature columns
#
# These will be required later when
# the FastAPI backend makes predictions.

joblib.dump(
    list(X.columns),
    features_path
)


print(
    "\nModel saved to:"
)

print(
    model_path
)


print(
    "\nFeature columns saved to:"
)

print(
    features_path
)


# =========================================================
# FINAL SUMMARY
# =========================================================

print(
    "\n" + "=" * 60
)

print(
    "TRAINING COMPLETED"
)

print(
    "=" * 60
)

print(
    f"""
Dataset:
    {TRAIN_FILE}

Training rows:
    {len(X_train)}

Testing rows:
    {len(X_test)}

Features:
    {X.shape[1]}

Fraud training samples:
    {fraud_count}

Normal training samples:
    {normal_count}

PR-AUC:
    {pr_auc:.4f}

ROC-AUC:
    {roc_auc:.4f}

Model:
    {model_path}

Feature columns:
    {features_path}
"""
)

print(
    "FraudLens model training completed successfully."
)