
from pathlib import Path
import sys

# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------
# DATABASE AND CRUD IMPORTS
# --------------------------------------------------

from app.db.database import SessionLocal
from app.db.models import Transaction, Flag, AnalystAction
from app.db.crud import (
    get_transaction,
    create_flag,
    get_flag_by_transaction,
    update_flag_status,
    create_analyst_action,
    get_actions_by_flag,
    get_summary_data,
)


def test_database_workflow():
    db = SessionLocal()

    try:
        print("=" * 60)
        print("FRAUDLENS - DATABASE WORKFLOW TEST")
        print("=" * 60)

        # 1. Find an existing transaction that has no flag.
        transaction = (
            db.query(Transaction)
            .outerjoin(
                Flag,
                Transaction.transaction_id == Flag.transaction_id,
            )
            .filter(Flag.id.is_(None))
            .order_by(Transaction.transaction_id.asc())
            .first()
        )

        if transaction is None:
            print("\nNo unflagged transaction is available for testing.")
            print("No changes were made.")
            return

        transaction_id = transaction.transaction_id

        print("\n1. TRANSACTION RETRIEVAL")
        print("-" * 40)
        print(f"Transaction ID: {transaction_id}")
        print(f"User ID: {transaction.user_id}")
        print(f"Amount: {transaction.amount}")
        print(f"Ground-truth label: {transaction.label}")
        print("Transaction retrieval: PASSED")

        # 2. Create a test flag.
        # This is a workflow test, not a real model prediction.
        flag_data = {
            "transaction_id": transaction_id,
            "risk_score": 85,
            "risk_level": "High",
            "triggered_rules": [
                "database_workflow_test"
            ],
            "explanation": (
                "Test flag created to validate the FraudLens "
                "database workflow. This is not a real fraud prediction."
            ),
            "status": "Pending",
        }

        flag = create_flag(db, flag_data)

        print("\n2. FRAUD FLAG CREATION")
        print("-" * 40)
        print(f"Flag ID: {flag.id}")
        print(f"Transaction ID: {flag.transaction_id}")
        print(f"Risk score: {flag.risk_score}")
        print(f"Risk level: {flag.risk_level}")
        print(f"Status: {flag.status}")
        print("Flag creation: PASSED")

        # 3. Verify the flag can be retrieved.
        retrieved_flag = get_flag_by_transaction(
            db,
            transaction_id,
        )

        assert retrieved_flag is not None
        assert retrieved_flag.id == flag.id

        print("\n3. FLAG RETRIEVAL")
        print("-" * 40)
        print("Flag retrieved successfully: PASSED")

        # 4. Test updating the status.
        updated_flag = update_flag_status(
            db,
            flag.id,
            "Pending",
        )

        assert updated_flag is not None
        assert updated_flag.status == "Pending"

        print("\n4. FLAG STATUS UPDATE")
        print("-" * 40)
        print(f"Current status: {updated_flag.status}")
        print("Status update: PASSED")

        # 5. Record a simulated analyst decision.
        action = create_analyst_action(
            db=db,
            flag_id=flag.id,
            action="Genuine",
            notes=(
                "Simulated analyst decision for database testing. "
                "Not a real fraud investigation."
            ),
        )

        print("\n5. ANALYST ACTION")
        print("-" * 40)
        print(f"Action ID: {action.id}")
        print(f"Flag ID: {action.flag_id}")
        print(f"Action: {action.action}")
        print(f"Updated flag status: {flag.status}")
        print("Analyst action creation: PASSED")

        # 6. Verify the analyst action is persisted.
        actions = get_actions_by_flag(db, flag.id)

        assert len(actions) >= 1
        assert any(item.id == action.id for item in actions)

        print("\n6. ANALYST ACTION RETRIEVAL")
        print("-" * 40)
        print(f"Actions recorded for this flag: {len(actions)}")
        print("Action retrieval: PASSED")

        # 7. Verify dashboard summary data.
        summary = get_summary_data(db)

        print("\n7. DASHBOARD SUMMARY")
        print("-" * 40)
        print(
            "Total transactions:",
            summary["total_transactions"],
        )
        print("Total flags:", summary["total_flags"])
        print("Pending flags:", summary["pending_flags"])
        print("Risk breakdown:", summary["risk_breakdown"])
        print("Status breakdown:", summary["status_breakdown"])
        print("Top risky users:", summary["top_risky_users"])

        assert summary["total_transactions"] == (
            db.query(Transaction).count()
        )
        assert summary["total_flags"] == db.query(Flag).count()

        print("\nDashboard summary: PASSED")

        print("\n" + "=" * 60)
        print("ALL DATABASE WORKFLOW CHECKS PASSED")
        print("=" * 60)

        print("\nNote:")
        print(
            "One test flag and one simulated analyst action "
            "were saved to the database."
        )
        print(
            "The flag is marked Genuine by the simulated analyst "
            "workflow. This does not change the transaction's "
            "ground-truth label."
        )

    finally:
        db.close()


if __name__ == "__main__":
    test_database_workflow()
