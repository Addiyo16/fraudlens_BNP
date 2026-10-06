
from datetime import datetime

from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Transaction, Flag, AnalystAction


# --------------------------------------------------
# TRANSACTIONS
# --------------------------------------------------

def create_transaction(db: Session, transaction_data: dict):
    """Create and persist a transaction from dataset-compatible fields."""

    allowed_fields = {
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
    }

    data = {
        key: value
        for key, value in transaction_data.items()
        if key in allowed_fields
    }

    transaction = Transaction(**data)

    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction
    except Exception:
        db.rollback()
        raise


def get_transaction(db: Session, transaction_id: int):
    return (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )


def get_all_transactions(db: Session, limit: int = 1000):
    return (
        db.query(Transaction)
        .order_by(Transaction.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_transactions_by_customer(db: Session, user_id: int):
    """Retrieve transactions belonging to a particular user."""
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )


def delete_transaction(db: Session, transaction_id: int):
    transaction = get_transaction(db, transaction_id)

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


# --------------------------------------------------
# FRAUD FLAGS
# --------------------------------------------------

def create_flag(db: Session, flag_data: dict):
    """Create a fraud flag linked to an existing transaction."""

    transaction_id = flag_data.get("transaction_id")
    risk_score = flag_data.get("risk_score")
    risk_level = flag_data.get("risk_level")
    triggered_rules = flag_data.get("triggered_rules", [])
    explanation = flag_data.get("explanation")
    status = flag_data.get("status", "Pending")

    if get_transaction(db, transaction_id) is None:
        raise ValueError("Transaction does not exist.")

    existing_flag = get_flag_by_transaction(db, transaction_id)
    if existing_flag is not None:
        raise ValueError("A flag already exists for this transaction.")

    if not isinstance(risk_score, int) or not 0 <= risk_score <= 100:
        raise ValueError("risk_score must be an integer between 0 and 100.")

    if risk_level not in {"Low", "Medium", "High"}:
        raise ValueError("Invalid risk level.")

    if status not in {"Pending", "Fraud", "Genuine", "Escalate"}:
        raise ValueError("Invalid flag status.")

    if not isinstance(triggered_rules, list):
        raise ValueError("triggered_rules must be a list.")

    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("explanation must be a non-empty string.")

    flag = Flag(
        transaction_id=transaction_id,
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
        raise ValueError("Could not create flag. Check for duplicate or invalid data.")
    except Exception:
        db.rollback()
        raise


def get_flag(db: Session, flag_id: int):
    return db.query(Flag).filter(Flag.id == flag_id).first()


def get_flag_by_transaction(db: Session, transaction_id: int):
    return (
        db.query(Flag)
        .filter(Flag.transaction_id == transaction_id)
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
        query = query.filter(Flag.risk_level == risk_level)

    if status:
        query = query.filter(Flag.status == status)

    if rule:
        query = query.filter(Flag.triggered_rules.contains([rule]))

    return query.order_by(Flag.id.desc()).limit(limit).all()


def get_flags(db: Session):
    return get_all_flags(db)


def get_flags_by_risk_level(db: Session, risk_level: str):
    return (
        db.query(Flag)
        .filter(Flag.risk_level == risk_level)
        .order_by(Flag.id.desc())
        .all()
    )


def get_total_flags(db: Session):
    return db.query(Flag).count()


def get_pending_flags(db: Session):
    return (
        db.query(Flag)
        .filter(Flag.status == "Pending")
        .order_by(Flag.id.desc())
        .all()
    )


def update_flag_status(db: Session, flag_id: int, status: str):
    allowed_statuses = {"Pending", "Fraud", "Genuine", "Escalate"}

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


# --------------------------------------------------
# ANALYST ACTIONS
# --------------------------------------------------

def create_analyst_action(
    db: Session,
    flag_id: int,
    action: str,
    notes: str = None,
):
    """Record an analyst decision and update the associated flag."""

    allowed_actions = {"Fraud", "Genuine", "Escalate"}

    if action not in allowed_actions:
        raise ValueError("Action must be Fraud, Genuine, or Escalate.")

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
        flag.status = action
        db.commit()
        db.refresh(analyst_action)
        return analyst_action
    except Exception:
        db.rollback()
        raise


def get_analyst_action(db: Session, action_id: int):
    return (
        db.query(AnalystAction)
        .filter(AnalystAction.id == action_id)
        .first()
    )


def get_actions_by_flag(db: Session, flag_id: int):
    return (
        db.query(AnalystAction)
        .filter(AnalystAction.flag_id == flag_id)
        .order_by(AnalystAction.timestamp.desc())
        .all()
    )


def get_all_analyst_actions(db: Session, limit: int = 1000):
    return (
        db.query(AnalystAction)
        .order_by(AnalystAction.timestamp.desc())
        .limit(limit)
        .all()
    )


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------

def get_summary_data(db: Session):
    """Return database-backed metrics for the FraudLens dashboard."""

    total_transactions = get_total_transactions(db)
    total_flags = get_total_flags(db)

    pending_flags = (
        db.query(Flag)
        .filter(Flag.status == "Pending")
        .count()
    )

    risk_breakdown = {
        level: (
            db.query(Flag)
            .filter(Flag.risk_level == level)
            .count()
        )
        for level in ("Low", "Medium", "High")
    }

    status_breakdown = {
        status: (
            db.query(Flag)
            .filter(Flag.status == status)
            .count()
        )
        for status in ("Pending", "Fraud", "Genuine", "Escalate")
    }

    # Aggregate flagged risk scores by user.
    top_risky_users = (
        db.query(
            Transaction.user_id,
            func.count(Flag.id).label("flag_count"),
            func.sum(Flag.risk_score).label("total_risk_score"),
        )
        .join(
            Flag,
            Flag.transaction_id == Transaction.transaction_id,
        )
        .group_by(Transaction.user_id)
        .order_by(desc("total_risk_score"))
        .limit(5)
        .all()
    )

    top_risky_users_data = [
        {
            "user_id": row.user_id,
            "flag_count": row.flag_count,
            "total_risk_score": row.total_risk_score or 0,
        }
        for row in top_risky_users
    ]

    return {
        "total_transactions": total_transactions,
        "total_flags": total_flags,
        "pending_flags": pending_flags,
        "risk_breakdown": risk_breakdown,
        "status_breakdown": status_breakdown,
        "top_risky_users": top_risky_users_data,
    }
