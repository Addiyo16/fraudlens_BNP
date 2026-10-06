
from pathlib import Path
import sys

import pandas as pd

# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

# Project structure:
# fraudlens/
# └── backend/
#     ├── app/
#     │   └── db/
#     │       ├── database.py
#     │       └── models.py
#     ├── data/
#     │   ├── data/
#     │   │   └── fraud_model/
#     │   │       ├── train.csv
#     │   │       ├── test.csv
#     │   │       └── sample_submission.csv
#     │   └── scripts/
#     │       └── import_transactions.py
#     └── fraudlens.db

# import_transactions.py is inside backend/data/scripts/
# parents[0] = backend/data/scripts
# parents[1] = backend/data
# parents[2] = backend

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Allow imports from backend/app
sys.path.insert(0, str(BACKEND_DIR))

# Correct location of train.csv
CSV_PATH = (
    BACKEND_DIR
    / "data"
    / "data"
    / "fraud_model"
    / "train.csv"
)

# --------------------------------------------------
# DATABASE IMPORTS
# --------------------------------------------------

from app.db.database import SessionLocal, init_db
from app.db.models import Transaction

# --------------------------------------------------
# IMPORT CONFIGURATION
# --------------------------------------------------

BATCH_SIZE = 250
IMPORT_LIMIT = 1000

REQUIRED_COLUMNS = [
    "transaction_id",
    "user_id",
    "timestamp",
    "amount",
    "merchant_category",
    "country",
    "device_id",
    "channel",
    "hours_since_prev_txn",
    "label",
]


# --------------------------------------------------
# DATA VALIDATION
# --------------------------------------------------

def load_and_validate_data():
    """Load and validate the training CSV."""

    print("=" * 60)
    print("FRAUDLENS - TRANSACTION DATA IMPORT")
    print("=" * 60)

    print(f"\nBackend directory: {BACKEND_DIR}")
    print(f"CSV file: {CSV_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"\nCSV file not found: {CSV_PATH}\n"
            "Check that train.csv exists inside "
            "backend/data/data/fraud_model/."
        )

    df = pd.read_csv(CSV_PATH, nrows=IMPORT_LIMIT)

    print(f"\nRows read: {len(df)}")

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Keep only columns supported by the Transaction model.
    df = df[REQUIRED_COLUMNS].copy()

    print("\nMissing values per column:")
    print(df.isna().sum().to_string())

    if df.empty:
        raise ValueError("The CSV contains no rows.")

    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(
            "Missing values were found in required columns. "
            "Inspect the report above before importing."
        )

    # Check duplicate transaction IDs within the CSV batch.
    if df["transaction_id"].duplicated().any():
        raise ValueError(
            "Duplicate transaction_id values found in the CSV."
        )

    # Ensure numeric columns contain valid numeric values.
    numeric_columns = REQUIRED_COLUMNS

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    # Validate the ground-truth fraud labels.
    if not df["label"].isin([0, 1]).all():
        raise ValueError(
            "Training labels must contain only 0 or 1."
        )

    if (df["amount"] < 0).any():
        raise ValueError("Negative transaction amounts found.")

    if (df["hours_since_prev_txn"] < 0).any():
        raise ValueError(
            "Negative hours_since_prev_txn values found."
        )

    # Integer-valued database columns must contain integers.
    integer_columns = [
        "transaction_id",
        "user_id",
        "timestamp",
        "merchant_category",
        "country",
        "device_id",
        "channel",
        "label",
    ]

    for column in integer_columns:
        if not (df[column] % 1 == 0).all():
            raise ValueError(
                f"Column '{column}' contains non-integer values."
            )

    print("\nLabel distribution in import batch:")
    print(df["label"].value_counts().sort_index().to_string())

    print("\nData validation completed successfully.")

    return df


# --------------------------------------------------
# DATABASE IMPORT
# --------------------------------------------------

def import_transactions():
    """Import validated training records into SQLite."""

    df = load_and_validate_data()

    # Convert NumPy scalar values to ordinary Python values.
    records = df.to_dict(orient="records")

    records = [
        {
            key: value.item() if hasattr(value, "item") else value
            for key, value in record.items()
        }
        for record in records
    ]

    # Create tables if they do not already exist.
    init_db()

    db = SessionLocal()

    inserted = 0
    skipped = 0

    try:
        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start:start + BATCH_SIZE]

            ids = [row["transaction_id"] for row in batch]

            # Avoid importing transaction IDs already in the database.
            existing = {
                row[0]
                for row in (
                    db.query(Transaction.transaction_id)
                    .filter(Transaction.transaction_id.in_(ids))
                    .all()
                )
            }

            new_records = [
                row
                for row in batch
                if row["transaction_id"] not in existing
            ]

            skipped += len(batch) - len(new_records)

            if new_records:
                db.add_all(
                    [
                        Transaction(**record)
                        for record in new_records
                    ]
                )

                # Detect database errors before processing the next batch.
                db.flush()

                inserted += len(new_records)

        db.commit()

        total_transactions = db.query(Transaction).count()

        print("\n" + "=" * 60)
        print("IMPORT COMPLETED")
        print("=" * 60)

        print(f"Rows processed: {len(records)}")
        print(f"Inserted: {inserted}")
        print(f"Skipped existing IDs: {skipped}")
        print(f"Total database transactions: {total_transactions}")

        print("\nDatabase import finished successfully.")

    except Exception:
        db.rollback()
        print("\nImport failed. Database changes were rolled back.")
        raise

    finally:
        db.close()


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    import_transactions()
