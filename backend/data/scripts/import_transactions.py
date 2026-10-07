from datetime import datetime
from pathlib import Path
import sys

import pandas as pd


# ============================================================
# PATH CONFIGURATION
# ============================================================

# fraudlens/
# └── backend/
#     ├── app/
#     │   └── db/
#     │       ├── database.py
#     │       └── models.py
#     ├── data/
#     │   ├── data/
#     │   │   └── transactions.csv
#     │   └── scripts/
#     │       └── import_transactions.py
#     └── fraudlens.db

BACKEND_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(BACKEND_DIR))


CSV_PATH = (
    BACKEND_DIR
    / "data"
    / "data"
    / "transactions.csv"
)


# ============================================================
# DATABASE IMPORTS
# ============================================================

from app.db.database import SessionLocal, init_db
from app.db.models import Transaction


# ============================================================
# IMPORT CONFIGURATION
# ============================================================

BATCH_SIZE = 250

REQUIRED_COLUMNS = [
    "txn_id",
    "customer_id",
    "amount",
    "timestamp",
    "city",
    "beneficiary_id",
    "channel",
]


# ============================================================
# DATA VALIDATION
# ============================================================

def load_and_validate_data():
    """Load and validate the application transaction dataset."""

    print("=" * 60)
    print("FRAUDLENS - TRANSACTION DATA IMPORT")
    print("=" * 60)

    print(f"\nBackend directory: {BACKEND_DIR}")
    print(f"CSV file: {CSV_PATH}")

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"\nCSV file not found: {CSV_PATH}\n"
            "Run generate_data.py first."
        )

    df = pd.read_csv(CSV_PATH)

    print(f"\nRows read: {len(df)}")

    missing_columns = (
        set(REQUIRED_COLUMNS) - set(df.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing required columns: "
            f"{sorted(missing_columns)}"
        )

    # Keep only application-supported fields
    df = df[REQUIRED_COLUMNS].copy()

    if df.empty:
        raise ValueError(
            "The CSV contains no rows."
        )

    print("\nMissing values per column:")
    print(df.isna().sum().to_string())

    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(
            "Missing values found in required columns."
        )

    # Check duplicate transaction IDs
    if df["txn_id"].duplicated().any():
        raise ValueError(
            "Duplicate txn_id values found in CSV."
        )

    # Validate amount
    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="raise",
    )

    if (df["amount"] < 0).any():
        raise ValueError(
            "Negative transaction amounts found."
        )

    # Convert timestamp to datetime
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="raise",
    )

    # Convert timestamp to Python datetime
    df["timestamp"] = df["timestamp"].apply(
        lambda value: value.to_pydatetime()
    )

    print("\nData validation completed successfully.")

    return df


# ============================================================
# DATABASE IMPORT
# ============================================================

def import_transactions():
    """Import validated transactions into SQLite."""

    df = load_and_validate_data()

    records = df.to_dict(
        orient="records"
    )

    init_db()

    db = SessionLocal()

    inserted = 0
    skipped = 0

    try:

        for start in range(
            0,
            len(records),
            BATCH_SIZE,
        ):

            batch = records[
                start:start + BATCH_SIZE
            ]

            ids = [
                row["txn_id"]
                for row in batch
            ]

            # Find existing transactions
            existing = {
                row[0]
                for row in (
                    db.query(
                        Transaction.txn_id
                    )
                    .filter(
                        Transaction.txn_id.in_(ids)
                    )
                    .all()
                )
            }

            new_records = [
                row
                for row in batch
                if row["txn_id"] not in existing
            ]

            skipped += (
                len(batch)
                - len(new_records)
            )

            if new_records:

                db.add_all(
                    [
                        Transaction(**record)
                        for record in new_records
                    ]
                )

                db.flush()

                inserted += len(
                    new_records
                )

        db.commit()

        total_transactions = (
            db.query(Transaction).count()
        )

        print("\n" + "=" * 60)
        print("IMPORT COMPLETED")
        print("=" * 60)

        print(
            f"Rows processed: "
            f"{len(records)}"
        )

        print(
            f"Inserted: {inserted}"
        )

        print(
            f"Skipped existing IDs: "
            f"{skipped}"
        )

        print(
            f"Total database transactions: "
            f"{total_transactions}"
        )

        print(
            "\nDatabase import finished successfully."
        )

    except Exception:

        db.rollback()

        print(
            "\nImport failed. "
            "Database changes were rolled back."
        )

        raise

    finally:
        db.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import_transactions()