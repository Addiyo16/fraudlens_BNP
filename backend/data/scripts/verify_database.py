
from pathlib import Path
import sys

# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

# Resolve the backend directory.
# File location: backend/data/scripts/verify_database.py
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Allow Python to locate the app package.
sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------
# DATABASE IMPORTS
# --------------------------------------------------

from app.db.database import SessionLocal
from app.db.models import Transaction, Flag, AnalystAction


# --------------------------------------------------
# DATABASE VERIFICATION
# --------------------------------------------------

def verify_database():
    print("=" * 60)
    print("FRAUDLENS - DATABASE VERIFICATION")
    print("=" * 60)

    print(f"\nBackend directory: {BACKEND_DIR}")
    print(f"Database file: {BACKEND_DIR / 'fraudlens.db'}")

    db = SessionLocal()

    try:
        # 1. Total transaction count
        total_transactions = db.query(Transaction).count()

        print("\n1. TRANSACTION SUMMARY")
        print("-" * 40)
        print(f"Total transactions: {total_transactions}")

        # 2. Ground-truth label distribution
        fraud_count = (
            db.query(Transaction)
            .filter(Transaction.label == 1)
            .count()
        )

        non_fraud_count = (
            db.query(Transaction)
            .filter(Transaction.label == 0)
            .count()
        )

        unlabeled_count = (
            db.query(Transaction)
            .filter(Transaction.label.is_(None))
            .count()
        )

        print(f"Label 1 transactions: {fraud_count}")
        print(f"Label 0 transactions: {non_fraud_count}")
        print(f"Unlabeled transactions: {unlabeled_count}")

        if total_transactions > 0:
            print(
                "Labeled transactions: "
                f"{fraud_count + non_fraud_count}"
            )

        # 3. Transaction amount statistics
        print("\n2. TRANSACTION AMOUNT STATISTICS")
        print("-" * 40)

        amounts = db.query(Transaction.amount)

        if total_transactions > 0:
            from sqlalchemy import func

            stats = db.query(
                func.min(Transaction.amount),
                func.max(Transaction.amount),
                func.avg(Transaction.amount),
            ).one()

            print(f"Minimum amount: {stats[0]}")
            print(f"Maximum amount: {stats[1]}")
            print(f"Average amount: {stats[2]:.2f}")

        else:
            print("No transaction data available.")

        # 4. Fraud flags
        total_flags = db.query(Flag).count()

        print("\n3. FRAUD FLAG SUMMARY")
        print("-" * 40)
        print(f"Total flags: {total_flags}")

        # 5. Analyst actions
        total_actions = db.query(AnalystAction).count()

        print("\n4. ANALYST ACTION SUMMARY")
        print("-" * 40)
        print(f"Total analyst actions: {total_actions}")

        # 6. Display a few transaction records
        print("\n5. SAMPLE TRANSACTIONS")
        print("-" * 40)

        sample_transactions = (
            db.query(Transaction)
            .order_by(Transaction.transaction_id)
            .limit(5)
            .all()
        )

        if not sample_transactions:
            print("No transactions found.")

        for transaction in sample_transactions:
            print(
                f"ID: {transaction.transaction_id} | "
                f"User: {transaction.user_id} | "
                f"Amount: {transaction.amount} | "
                f"Label: {transaction.label}"
            )

        print("\n" + "=" * 60)
        print("DATABASE VERIFICATION COMPLETED")
        print("=" * 60)

    finally:
        db.close()


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    verify_database()
