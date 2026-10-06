
from pathlib import Path

import pandas as pd
import numpy as np


# ============================================================
# FRAUDLENS — DATA DIAGNOSTICS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

TRAIN_FILE = (
    BACKEND_DIR
    / "data"
    / "data"
    / "fraud_model"
    / "train.csv"
)

MIN_GROUP_SIZE = 50


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def print_section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def fraud_rate_table(df, column, min_size=MIN_GROUP_SIZE):
    """Display fraud counts and rates for a feature."""

    if column not in df.columns:
        return

    result = (
        df.groupby(column, dropna=False)["label"]
        .agg(
            transactions="count",
            frauds="sum",
            fraud_rate="mean",
        )
    )

    result = result[result["transactions"] >= min_size]
    result["fraud_rate_pct"] = result["fraud_rate"] * 100

    print(f"\nFraud rate by {column}:")

    if result.empty:
        print("No groups meet the minimum sample size.")
        return

    print(
        result.sort_values(
            "fraud_rate",
            ascending=False,
        ).head(20).to_string()
    )


def numeric_timestamp_analysis(df):
    """
    Analyze numeric timestamps without assuming their units.

    This avoids incorrectly interpreting integer timestamps
    as nanoseconds since the Unix epoch.
    """

    print_section("NUMERIC TIMESTAMP ANALYSIS")

    if "timestamp" not in df.columns:
        print("ERROR: timestamp column is missing.")
        return

    raw = df["timestamp"]
    numeric = pd.to_numeric(raw, errors="coerce")

    invalid_count = int(numeric.isna().sum())

    print("Original dtype:", raw.dtype)
    print("Invalid numeric timestamps:", invalid_count)

    if numeric.notna().sum() == 0:
        print("No usable numeric timestamps were found.")
        return

    print("Minimum raw value:", numeric.min())
    print("Maximum raw value:", numeric.max())
    print("Unique timestamp values:", numeric.nunique())

    print(
        "\nTimestamp unit is NOT assumed. "
        "No calendar dates are generated."
    )

    # Numeric timestamps can establish relative ordering,
    # provided that larger values represent later events.
    ordered = df.loc[numeric.notna()].copy()
    ordered["_numeric_timestamp"] = numeric.loc[numeric.notna()]

    ordered = ordered.sort_values(
        "_numeric_timestamp",
        kind="stable",
    ).reset_index(drop=True)

    print("Rows with valid timestamps:", len(ordered))
    print(
        "Timestamp values nondecreasing after sorting:",
        ordered["_numeric_timestamp"].is_monotonic_increasing,
    )

    print("\nEarliest 10 records by numeric timestamp:")

    sample_columns = [
        column
        for column in [
            "transaction_id",
            "user_id",
            "timestamp",
            "amount",
            "label",
        ]
        if column in ordered.columns
    ]

    print(ordered[sample_columns].head(10).to_string(index=False))

    print("\nLatest 10 records by numeric timestamp:")
    print(ordered[sample_columns].tail(10).to_string(index=False))

    # Divide the chronological data into ten groups.
    # These are ordering-based groups, not calendar periods.
    if len(ordered) >= 10:
        ordered["chronological_group"] = pd.qcut(
            np.arange(len(ordered)),
            q=10,
            labels=False,
            duplicates="drop",
        )

        trend = (
            ordered.groupby("chronological_group", observed=True)["label"]
            .agg(
                transactions="count",
                frauds="sum",
                fraud_rate="mean",
            )
        )

        trend["fraud_rate_pct"] = trend["fraud_rate"] * 100

        print("\nFraud rate across chronological groups:")
        print(trend.to_string())

        print(
            "\nNote: chronological groups assume larger numeric "
            "timestamps represent later transactions."
        )

    return ordered


# ============================================================
# MAIN DIAGNOSTIC
# ============================================================

def main():

    if not TRAIN_FILE.exists():
        print(f"ERROR: Training file not found:\n{TRAIN_FILE}")
        return

    df = pd.read_csv(TRAIN_FILE)

    print_section("FRAUDLENS — DATASET OVERVIEW")

    print("Dataset:", TRAIN_FILE)
    print("Rows:", f"{len(df):,}")
    print("Columns:", len(df.columns))
    print("Column names:", df.columns.tolist())

    required_columns = {"label", "timestamp"}

    missing_required = required_columns - set(df.columns)

    if missing_required:
        print("ERROR: Missing required columns:", missing_required)
        return

    # --------------------------------------------------------
    # RAW TIMESTAMP INSPECTION
    # --------------------------------------------------------

    print_section("RAW TIMESTAMP INSPECTION")

    print("Timestamp dtype:", df["timestamp"].dtype)
    print("First 10 raw values:")
    print(df["timestamp"].head(10).to_list())

    print("\nLast 10 raw values:")
    print(df["timestamp"].tail(10).to_list())

    # --------------------------------------------------------
    # LABEL DISTRIBUTION
    # --------------------------------------------------------

    print_section("LABEL DISTRIBUTION")

    print(df["label"].value_counts(dropna=False).to_string())

    label_counts = df["label"].value_counts()

    if 0 in label_counts.index and 1 in label_counts.index:

        normal_count = int(label_counts[0])
        fraud_count = int(label_counts[1])
        total = normal_count + fraud_count

        prevalence = fraud_count / total if total else 0

        print(f"\nLegitimate transactions: {normal_count:,}")
        print(f"Fraudulent transactions: {fraud_count:,}")
        print(f"Fraud prevalence: {prevalence:.4%}")
        print(f"Baseline PR-AUC reference: {prevalence:.5f}")

        if fraud_count:
            print(
                "Normal-to-fraud ratio:",
                f"{normal_count / fraud_count:.2f}:1",
            )

    # --------------------------------------------------------
    # DATA QUALITY
    # --------------------------------------------------------

    print_section("DATA QUALITY")

    missing_values = df.isna().sum()
    missing_values = missing_values[missing_values > 0]

    if missing_values.empty:
        print("No missing values.")
    else:
        print("Missing values by column:")
        print(missing_values.to_string())

    if "transaction_id" in df.columns:
        print(
            "Duplicate transaction IDs:",
            df["transaction_id"].duplicated().sum(),
        )

    print("Duplicate complete rows:", df.duplicated().sum())

    signature_columns = [
        column
        for column in [
            "user_id",
            "timestamp",
            "amount",
            "merchant_category",
            "country",
            "device_id",
            "channel",
        ]
        if column in df.columns
    ]

    if signature_columns:
        duplicate_signatures = df.duplicated(
            subset=signature_columns,
            keep=False,
        ).sum()

        print(
            "Rows sharing transaction signatures:",
            duplicate_signatures,
        )

    # --------------------------------------------------------
    # NUMERIC FEATURE ANALYSIS
    # --------------------------------------------------------

    print_section("NUMERIC FEATURES BY LABEL")

    numeric_candidates = [
        column
        for column in ["amount", "hours_since_prev_txn"]
        if column in df.columns
    ]

    for column in numeric_candidates:

        print(f"\nFeature: {column}")

        feature = pd.to_numeric(df[column], errors="coerce")

        stats = (
            pd.DataFrame(
                {
                    "feature": feature,
                    "label": df["label"],
                }
            )
            .groupby("label")["feature"]
            .agg(
                [
                    "count",
                    "mean",
                    "median",
                    "std",
                    "min",
                    "max",
                ]
            )
        )

        print(stats.to_string())

        correlation_data = pd.DataFrame(
            {
                "feature": feature,
                "label": df["label"],
            }
        ).dropna()

        if (
            len(correlation_data) > 1
            and correlation_data["feature"].nunique() > 1
            and correlation_data["label"].nunique() > 1
        ):
            correlation = correlation_data["feature"].corr(
                correlation_data["label"],
                method="spearman",
            )

            print(
                "Spearman correlation with label:",
                f"{correlation:.5f}",
            )

        valid_feature = feature.dropna()

        if len(valid_feature) > 1 and valid_feature.nunique() > 1:
            try:
                bins = pd.qcut(
                    feature,
                    q=10,
                    duplicates="drop",
                )

                quantile_stats = (
                    df.assign(_feature_bin=bins)
                    .groupby("_feature_bin", observed=True)["label"]
                    .agg(
                        transactions="count",
                        frauds="sum",
                        fraud_rate="mean",
                    )
                )

                quantile_stats["fraud_rate_pct"] = (
                    quantile_stats["fraud_rate"] * 100
                )

                print("\nFraud rate by feature quantile:")
                print(quantile_stats.to_string())

            except (ValueError, TypeError) as exc:
                print("Could not calculate quantiles:", exc)

    # --------------------------------------------------------
    # CATEGORICAL FEATURE ANALYSIS
    # --------------------------------------------------------

    print_section("FRAUD RATES BY CATEGORY")

    categorical_candidates = [
        column
        for column in [
            "merchant_category",
            "country",
            "channel",
            "device_id",
        ]
        if column in df.columns
    ]

    for column in categorical_candidates:
        fraud_rate_table(df, column)

    # --------------------------------------------------------
    # TIMESTAMP ANALYSIS
    # --------------------------------------------------------

    numeric_timestamp_analysis(df)

    # --------------------------------------------------------
    # ADDITIONAL DATASET CHECKS
    # --------------------------------------------------------

    print_section("ADDITIONAL CHECKS")

    for column in [
        "user_id",
        "device_id",
        "merchant_category",
        "country",
        "channel",
    ]:
        if column in df.columns:
            print(
                f"Unique {column} values:",
                df[column].nunique(dropna=True),
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print_section("DIAGNOSTICS COMPLETE")

    print("Original CSV modified: No")
    print("Model trained: No")
    print("Timestamp unit inferred: No")
    print("Calendar timestamps fabricated: No")

    print(
        "\nNext step: confirm the timestamp unit and meaning "
        "before generating hour-of-day, weekday, or calendar features."
    )


if __name__ == "__main__":
    main()
