import pandas as pd
import numpy as np


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create behavioral fraud-detection features.

    Important:
    All historical features use only transactions that occurred
    BEFORE the current transaction.
    """

    df = df.copy()

    # =========================================================
    # 1. DATETIME
    # =========================================================

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Remove rows with invalid timestamps
    df = df.dropna(
        subset=["timestamp"]
    )

    # Sort by user and time so historical calculations
    # only use previous transactions.
    df = df.sort_values(
        ["user_id", "timestamp"]
    ).reset_index(drop=True)

    # =========================================================
    # 2. TIME FEATURES
    # =========================================================

    df["hour"] = df["timestamp"].dt.hour

    df["day_of_week"] = (
        df["timestamp"].dt.dayofweek
    )

    df["day"] = (
        df["timestamp"].dt.day
    )

    df["month"] = (
        df["timestamp"].dt.month
    )

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    df["is_night"] = (
        (df["hour"] >= 0) &
        (df["hour"] < 5)
    ).astype(int)

    # =========================================================
    # 3. AMOUNT FEATURES
    # =========================================================

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    df["amount"] = (
        df["amount"]
        .fillna(0)
    )

    # Helps reduce the effect of very large amounts
    df["log_amount"] = np.log1p(
        df["amount"]
    )

    # =========================================================
    # 4. USER HISTORICAL TRANSACTION COUNT
    # =========================================================

    # Number of transactions BEFORE current transaction
    df["user_previous_count"] = (
        df.groupby("user_id")
        .cumcount()
    )

    # =========================================================
    # 5. USER HISTORICAL AVERAGE AMOUNT
    # =========================================================

    # Cumulative sum including current transaction
    cumulative_amount = (
        df.groupby("user_id")["amount"]
        .cumsum()
    )

    # Remove current transaction
    previous_amount_sum = (
        cumulative_amount -
        df["amount"]
    )

    df["user_avg_amount"] = np.where(
        df["user_previous_count"] > 0,
        previous_amount_sum /
        df["user_previous_count"],
        0
    )

    # Current amount compared with user's
    # historical average
    df["amount_vs_user_avg"] = np.where(
        df["user_avg_amount"] > 0,
        df["amount"] /
        df["user_avg_amount"],
        0
    )

    # =========================================================
    # 6. USER HISTORICAL MAXIMUM
    # =========================================================

    # Shift the cumulative maximum so that the current
    # transaction is NOT included.
    df["user_previous_max"] = (
        df.groupby("user_id")["amount"]
        .cummax()
        .groupby(df["user_id"])
        .shift(1)
    )

    df["user_previous_max"] = (
        df["user_previous_max"]
        .fillna(0)
    )

    df["amount_vs_user_max"] = np.where(
        df["user_previous_max"] > 0,
        df["amount"] /
        df["user_previous_max"],
        0
    )

    # =========================================================
    # 7. TRANSACTION VELOCITY
    # =========================================================

    df["hours_since_prev_txn"] = pd.to_numeric(
        df["hours_since_prev_txn"],
        errors="coerce"
    )

    df["hours_since_prev_txn"] = (
        df["hours_since_prev_txn"]
        .fillna(999)
    )

    # Transaction within 10 minutes
    df["rapid_transaction"] = (
        df["hours_since_prev_txn"] <=
        (10 / 60)
    ).astype(int)

    # Transaction within 5 minutes
    df["very_rapid_transaction"] = (
        df["hours_since_prev_txn"] <=
        (5 / 60)
    ).astype(int)

    # =========================================================
    # 8. NEW DEVICE
    # =========================================================

    seen_devices = {}

    new_device = []

    for _, row in df.iterrows():

        user = row["user_id"]
        device = row["device_id"]

        if user not in seen_devices:
            seen_devices[user] = set()

        # Check BEFORE adding current device
        if device in seen_devices[user]:
            new_device.append(0)
        else:
            new_device.append(1)

        seen_devices[user].add(device)

    df["new_device"] = new_device

    # =========================================================
    # 9. NEW COUNTRY
    # =========================================================

    seen_countries = {}

    new_country = []

    for _, row in df.iterrows():

        user = row["user_id"]
        country = row["country"]

        if user not in seen_countries:
            seen_countries[user] = set()

        # Check BEFORE adding current country
        if country in seen_countries[user]:
            new_country.append(0)
        else:
            new_country.append(1)

        seen_countries[user].add(country)

    df["new_country"] = new_country

    # =========================================================
    # 10. MERCHANT CATEGORY CHANGE
    # =========================================================

    df["previous_merchant_category"] = (
        df.groupby("user_id")[
            "merchant_category"
        ].shift(1)
    )

    df["merchant_category_change"] = (
        (
            df["merchant_category"]
            != df["previous_merchant_category"]
        )
        &
        df["previous_merchant_category"].notna()
    ).astype(int)

    # =========================================================
    # 11. CHANNEL CHANGE
    # =========================================================

    df["previous_channel"] = (
        df.groupby("user_id")[
            "channel"
        ].shift(1)
    )

    df["channel_change"] = (
        (
            df["channel"]
            != df["previous_channel"]
        )
        &
        df["previous_channel"].notna()
    ).astype(int)

    # =========================================================
    # 12. USER TRANSACTION COUNT
    # =========================================================

    # Same as previous_count, kept as a descriptive
    # behavioral feature.
    df["user_transaction_count"] = (
        df.groupby("user_id")
        .cumcount()
    )

    # =========================================================
    # 13. CLEAN NUMERIC VALUES
    # =========================================================

    numeric_columns = [
        "amount",
        "log_amount",
        "user_previous_count",
        "user_avg_amount",
        "amount_vs_user_avg",
        "user_previous_max",
        "amount_vs_user_max",
        "hours_since_prev_txn",
        "rapid_transaction",
        "very_rapid_transaction",
        "new_device",
        "new_country",
        "merchant_category_change",
        "channel_change",
        "user_transaction_count"
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # Replace infinite values
    df = df.replace(
        [np.inf, -np.inf],
        0
    )

    # Replace remaining numeric NaN values
    for column in numeric_columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna(0)
            )

    return df