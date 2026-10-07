from datetime import datetime

from app.db.database import SessionLocal
from app.db import crud


def main():
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. GET EXISTING TRANSACTION
        # --------------------------------------------------

        transaction = crud.get_transaction(
            db,
            "T0001",
        )

        if transaction is None:
            transaction = crud.get_all_transactions(
                db,
                limit=1,
            )[0]

        print("\n1. TRANSACTION")
        print("-" * 40)
        print("txn_id:", transaction.txn_id)
        print("customer_id:", transaction.customer_id)
        print("amount:", transaction.amount)
        print("timestamp:", transaction.timestamp)
        print("city:", transaction.city)
        print("beneficiary_id:", transaction.beneficiary_id)
        print("channel:", transaction.channel)

        # --------------------------------------------------
        # 2. CUSTOMER HISTORY
        # --------------------------------------------------

        history = crud.get_customer_transactions(
            db,
            transaction.customer_id,
        )

        print("\n2. CUSTOMER HISTORY")
        print("-" * 40)
        print(
            "Customer:",
            transaction.customer_id,
        )
        print(
            "Transactions:",
            len(history),
        )

        print(
            "Chronological:",
            all(
                history[i].timestamp
                <= history[i + 1].timestamp
                for i in range(len(history) - 1)
            ),
        )

        # --------------------------------------------------
        # 3. CREATE FLAG
        # --------------------------------------------------

        existing_flag = crud.get_flag_by_transaction(
            db,
            transaction.txn_id,
        )

        if existing_flag:
            flag = existing_flag
            print("\n3. FLAG")
            print("-" * 40)
            print(
                "Existing flag:",
                flag.id,
            )

        else:
            flag = crud.create_flag(
                db,
                {
                    "txn_id": transaction.txn_id,
                    "risk_score": 85,
                    "risk_level": "High",
                    "triggered_rules": [
                        "High Amount",
                        "Unusual Location",
                    ],
                    "explanation": (
                        "Test fraud flag created "
                        "for database workflow validation."
                    ),
                    "status": "Pending",
                },
            )

            print("\n3. FLAG")
            print("-" * 40)
            print("Created flag:", flag.id)

        print("txn_id:", flag.txn_id)
        print("risk_score:", flag.risk_score)
        print("risk_level:", flag.risk_level)
        print(
            "triggered_rules:",
            flag.triggered_rules,
        )
        print("status:", flag.status)

        # --------------------------------------------------
        # 4. ANALYST ACTION
        # --------------------------------------------------

        action = crud.create_analyst_action(
            db,
            flag.id,
            "Genuine",
            "Database workflow test.",
        )

        print("\n4. ANALYST ACTION")
        print("-" * 40)
        print("action_id:", action.id)
        print("action:", action.action)
        print("notes:", action.notes)

        # Refresh flag
        flag = crud.get_flag(
            db,
            flag.id,
        )

        print(
            "Updated flag status:",
            flag.status,
        )

        # --------------------------------------------------
        # 5. SUMMARY
        # --------------------------------------------------

        summary = crud.get_summary_data(db)

        print("\n5. SUMMARY")
        print("-" * 40)

        print(
            "total_transactions:",
            summary["total_transactions"],
        )

        print(
            "total_flagged:",
            summary["total_flagged"],
        )

        print(
            "risk_breakdown:",
            summary["risk_breakdown"],
        )

        print(
            "rule_breakdown:",
            summary["rule_breakdown"],
        )

        print(
            "top_risky_customers:",
            summary["top_risky_customers"],
        )

        print("\n" + "=" * 60)
        print("DATABASE WORKFLOW TEST PASSED")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()