from datetime import datetime

from sqlalchemy import cast, desc, func, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Transaction, Flag, AnalystAction


# ============================================================
# TRANSACTIONS
# ============================================================

def create_transaction(db: Session, transaction_data: dict):
    """Create and persist a transaction."""

    allowed_fields = {
        "txn_id",
        "customer_id",
        "amount",
        "timestamp",
        "city",
        "beneficiary_id",
        "channel",
    }

    data = {
        key: value
        for key, value in transaction_data.items()
        if key in allowed_fields
    }

    required_fields = {
        "txn_id",
        "customer_id",
        "amount",
        "timestamp",
        "city",
        "beneficiary_id",
        "channel",
    }

    missing = required_fields - data.keys()

    if missing:
        raise ValueError(
            f"Missing required transaction fields: {sorted(missing)}"
        )

    if get_transaction(db, data["txn_id"]) is not None:
        raise ValueError(
            f"Transaction {data['txn_id']} already exists."
        )

    if data["amount"] < 0:
        raise ValueError("Transaction amount cannot be negative.")

    transaction = Transaction(**data)

    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    except IntegrityError:
        db.rollback()
        raise ValueError(
            "Could not create transaction due to duplicate or invalid data."
        )

    except Exception:
        db.rollback()
        raise


def get_transaction(db: Session, txn_id: str):
    return (
        db.query(Transaction)
        .filter(Transaction.txn_id == txn_id)
        .first()
    )


def get_all_transactions(db: Session, limit: int = 1000):
    return (
        db.query(Transaction)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_customer_transactions(
    db: Session,
    customer_id: str,
):
    """
    Return a customer's complete transaction history
    in chronological order.
    """

    return (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.timestamp.asc())
        .all()
    )


# Backward-compatible alias
def get_transactions_by_customer(
    db: Session,
    customer_id: str,
):
    return get_customer_transactions(db, customer_id)


def delete_transaction(db: Session, txn_id: str):
    transaction = get_transaction(db, txn_id)

    if transaction is None:
        return False

    try:
        db.delete(transaction)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


def get_total_transactions(db: Session):
    return db.query(Transaction).count()


# ============================================================
# FRAUD FLAGS
# ============================================================

def create_flag(db: Session, flag_data: dict):
    """Create a fraud flag linked to an existing transaction."""

    txn_id = flag_data.get("txn_id")
    risk_score = flag_data.get("risk_score")
    risk_level = flag_data.get("risk_level")
    triggered_rules = flag_data.get("triggered_rules", [])
    explanation = flag_data.get("explanation")
    status = flag_data.get("status", "Pending")

    if get_transaction(db, txn_id) is None:
        raise ValueError("Transaction does not exist.")

    if get_flag_by_transaction(db, txn_id) is not None:
        raise ValueError(
            "A flag already exists for this transaction."
        )

    if not isinstance(risk_score, int) or not 0 <= risk_score <= 100:
        raise ValueError(
            "risk_score must be an integer between 0 and 100."
        )

    if risk_level not in {"Low", "Medium", "High"}:
        raise ValueError("Invalid risk level.")

    if status not in {
        "Pending",
        "Fraud",
        "Genuine",
        "Escalate",
    }:
        raise ValueError("Invalid flag status.")

    if not isinstance(triggered_rules, list):
        raise ValueError("triggered_rules must be a list.")

    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError(
            "explanation must be a non-empty string."
        )

    flag = Flag(
        txn_id=txn_id,
        risk_score=risk_score,
        risk_level=risk_level,
        triggered_rules=triggered_rules,
        explanation=explanation,
        status=status,
    )

    try:
        db.add(flag)
        db.commit()
        db.refresh(flag)
        return flag

    except IntegrityError:
        db.rollback()
        raise ValueError(
            "Could not create flag. Check for duplicate or invalid data."
        )

    except Exception:
        db.rollback()
        raise


def get_flag(db: Session, flag_id: int):
    return (
        db.query(Flag)
        .filter(Flag.id == flag_id)
        .first()
    )


def get_flag_by_transaction(db: Session, txn_id: str):
    return (
        db.query(Flag)
        .filter(Flag.txn_id == txn_id)
        .first()
    )


def get_all_flags(
    db: Session,
    risk_level: str = None,
    rule: str = None,
    status: str = None,
    limit: int = 1000,
):
    query = db.query(Flag)

    if risk_level:
        query = query.filter(
            Flag.risk_level == risk_level
        )

    if status:
        query = query.filter(
            Flag.status == status
        )

    if rule:
        # SQLite JSON filtering
        query = query.filter(
            cast(
                Flag.triggered_rules,
                String,
            ).contains(f'"{rule}"')
        )

    # Highest risk first
    return (
        query
        .order_by(
            Flag.risk_score.desc(),
            Flag.id.desc(),
        )
        .limit(limit)
        .all()
    )


def get_flags(
    db: Session,
    risk_level: str = None,
    rule: str = None,
):
    return get_all_flags(
        db,
        risk_level=risk_level,
        rule=rule,
    )


def get_flags_by_risk_level(
    db: Session,
    risk_level: str,
):
    return (
        db.query(Flag)
        .filter(Flag.risk_level == risk_level)
        .order_by(
            Flag.risk_score.desc(),
            Flag.id.desc(),
        )
        .all()
    )


def get_total_flags(db: Session):
    return db.query(Flag).count()


def get_pending_flags(db: Session):
    return (
        db.query(Flag)
        .filter(Flag.status == "Pending")
        .order_by(
            Flag.risk_score.desc(),
            Flag.id.desc(),
        )
        .all()
    )


def update_flag_status(
    db: Session,
    flag_id: int,
    status: str,
):
    allowed_statuses = {
        "Pending",
        "Fraud",
        "Genuine",
        "Escalate",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid flag status.")

    flag = get_flag(db, flag_id)

    if flag is None:
        return None

    try:
        flag.status = status
        db.commit()
        db.refresh(flag)
        return flag

    except Exception:
        db.rollback()
        raise


# ============================================================
# ANALYST ACTIONS
# ============================================================

def create_analyst_action(
    db: Session,
    flag_id: int,
    action: str,
    notes: str = None,
):
    """
    Record an analyst decision and update the flag status
    atomically.
    """

    allowed_actions = {
        "Fraud",
        "Genuine",
        "Escalate",
    }

    if action not in allowed_actions:
        raise ValueError(
            "Action must be Fraud, Genuine, or Escalate."
        )

    flag = get_flag(db, flag_id)

    if flag is None:
        raise ValueError("Flag does not exist.")

    analyst_action = AnalystAction(
        flag_id=flag_id,
        action=action,
        notes=notes,
        timestamp=datetime.utcnow(),
    )

    try:
        db.add(analyst_action)

        # Update flag status in the same transaction
        flag.status = action

        db.commit()
        db.refresh(analyst_action)

        return analyst_action

    except Exception:
        db.rollback()
        raise


def get_analyst_action(
    db: Session,
    action_id: int,
):
    return (
        db.query(AnalystAction)
        .filter(AnalystAction.id == action_id)
        .first()
    )


def get_actions_by_flag(
    db: Session,
    flag_id: int,
):
    return (
        db.query(AnalystAction)
        .filter(AnalystAction.flag_id == flag_id)
        .order_by(
            AnalystAction.timestamp.desc()
        )
        .all()
    )


def get_all_analyst_actions(
    db: Session,
    limit: int = 1000,
):
    return (
        db.query(AnalystAction)
        .order_by(
            AnalystAction.timestamp.desc()
        )
        .limit(limit)
        .all()
    )


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def get_summary_data(db: Session):
    """Return database-backed metrics for the FraudLens dashboard."""

    total_transactions = get_total_transactions(db)
    total_flagged = get_total_flags(db)

    risk_breakdown = {
        level: (
            db.query(Flag)
            .filter(Flag.risk_level == level)
            .count()
        )
        for level in (
            "Low",
            "Medium",
            "High",
        )
    }

    # Count each triggered rule across all flags
    rule_breakdown = {}

    flags = db.query(Flag).all()

    for flag in flags:
        for rule in flag.triggered_rules or []:
            rule_breakdown[rule] = (
                rule_breakdown.get(rule, 0) + 1
            )

    # Top risky customers
    top_risky_customers = (
        db.query(
            Transaction.customer_id,
            func.count(Flag.id).label("flag_count"),
            func.sum(Flag.risk_score).label(
                "total_risk_score"
            ),
        )
        .join(
            Flag,
            Flag.txn_id == Transaction.txn_id,
        )
        .group_by(
            Transaction.customer_id
        )
        .order_by(
            desc("total_risk_score")
        )
        .limit(5)
        .all()
    )

    top_risky_customers_data = [
        {
            "customer_id": row.customer_id,
            "flag_count": row.flag_count,
            "total_risk_score": (
                row.total_risk_score or 0
            ),
        }
        for row in top_risky_customers
    ]

    return {
        "total_transactions": total_transactions,
        "total_flagged": total_flagged,
        "risk_breakdown": risk_breakdown,
        "rule_breakdown": rule_breakdown,
        "top_risky_customers": top_risky_customers_data,
    }