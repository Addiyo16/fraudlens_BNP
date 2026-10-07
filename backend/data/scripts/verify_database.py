from pathlib import Path
import sys

from sqlalchemy import func

# ============================================================
# PATH CONFIGURATION
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(BACKEND_DIR))


# ============================================================
# DATABASE IMPORTS
# ============================================================

from app.db.database import SessionLocal
from app.db.models import Transaction, Flag, AnalystAction


# ============================================================
# VERIFICATION
# ============================================================

def verify_database():

    print("=" * 60)
    print("FRAUDLENS - DATABASE VERIFICATION")
    print("=" * 60)

    print(f"\nBackend directory: {BACKEND_DIR}")

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # 1. TRANSACTION SUMMARY
        # ----------------------------------------------------

        print("\n1. TRANSACTION SUMMARY")
        print("-" * 40)

        total_transactions = (
            db.query(Transaction).count()
        )

        print(
            f"Total transactions: "
            f"{total_transactions}"
        )

        # ----------------------------------------------------
        # 2. REQUIRED FIELDS
        # ----------------------------------------------------

        print("\n2. TRANSACTION SCHEMA")
        print("-" * 40)

        first_transaction = (
            db.query(Transaction)
            .first()
        )

        if first_transaction is None:
            print("No transactions found.")
            return

        print(
            f"txn_id: "
            f"{first_transaction.txn_id}"
        )

        print(
            f"customer_id: "
            f"{first_transaction.customer_id}"
        )

        print(
            f"amount: "
            f"{first_transaction.amount}"
        )

        print(
            f"timestamp: "
            f"{first_transaction.timestamp}"
        )

        print(
            f"city: "
            f"{first_transaction.city}"
        )

        print(
            f"beneficiary_id: "
            f"{first_transaction.beneficiary_id}"
        )

        print(
            f"channel: "
            f"{first_transaction.channel}"
        )

        # ----------------------------------------------------
        # 3. CUSTOMER HISTORY
        # ----------------------------------------------------

        print("\n3. CUSTOMER HISTORY")
        print("-" * 40)

        customer_id = (
            first_transaction.customer_id
        )

        history = (
            db.query(Transaction)
            .filter(
                Transaction.customer_id
                == customer_id
            )
            .order_by(
                Transaction.timestamp.asc()
            )
            .all()
        )

        print(
            f"Customer: {customer_id}"
        )

        print(
            f"Transaction count: "
            f"{len(history)}"
        )

        if history:

            print(
                f"First transaction: "
                f"{history[0].timestamp}"
            )

            print(
                f"Last transaction: "
                f"{history[-1].timestamp}"
            )

        # Verify chronological ordering
        timestamps = [
            transaction.timestamp
            for transaction in history
        ]

        if timestamps == sorted(timestamps):
            print(
                "Chronological order: PASS"
            )
        else:
            print(
                "Chronological order: FAIL"
            )

        # ----------------------------------------------------
        # 4. FLAG SUMMARY
        # ----------------------------------------------------

        print("\n4. FLAG SUMMARY")
        print("-" * 40)

        total_flags = (
            db.query(Flag).count()
        )

        print(
            f"Total flags: {total_flags}"
        )

        risk_breakdown = {}

        for risk_level in (
            "Low",
            "Medium",
            "High",
        ):

            count = (
                db.query(Flag)
                .filter(
                    Flag.risk_level
                    == risk_level
                )
                .count()
            )

            risk_breakdown[risk_level] = count

        print(
            f"Risk breakdown: "
            f"{risk_breakdown}"
        )

        # ----------------------------------------------------
        # 5. FLAG -> TRANSACTION RELATIONSHIP
        # ----------------------------------------------------

        print("\n5. FLAG RELATIONSHIP")
        print("-" * 40)

        if total_flags > 0:

            flag = (
                db.query(Flag)
                .first()
            )

            transaction = (
                db.query(Transaction)
                .filter(
                    Transaction.txn_id
                    == flag.txn_id
                )
                .first()
            )

            if transaction:

                print(
                    "Flag -> Transaction: PASS"
                )

                print(
                    f"Flag ID: {flag.id}"
                )

                print(
                    f"Flag txn_id: "
                    f"{flag.txn_id}"
                )

                print(
                    f"Transaction txn_id: "
                    f"{transaction.txn_id}"
                )

            else:

                print(
                    "Flag -> Transaction: FAIL"
                )

        else:

            print(
                "No flags available yet."
            )

        # ----------------------------------------------------
        # 6. DATABASE COUNTS
        # ----------------------------------------------------

        print("\n6. DATABASE COUNTS")
        print("-" * 40)

        print(
            f"Transactions: "
            f"{db.query(Transaction).count()}"
        )

        print(
            f"Flags: "
            f"{db.query(Flag).count()}"
        )

        print(
            f"Analyst actions: "
            f"{db.query(AnalystAction).count()}"
        )

        # ----------------------------------------------------
        # 7. CUSTOMER DISTRIBUTION
        # ----------------------------------------------------

        print("\n7. CUSTOMER DISTRIBUTION")
        print("-" * 40)

        customer_count = (
            db.query(
                func.count(
                    func.distinct(
                        Transaction.customer_id
                    )
                )
            )
            .scalar()
        )

        print(
            f"Unique customers: "
            f"{customer_count}"
        )

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("DATABASE VERIFICATION COMPLETED")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    verify_database()