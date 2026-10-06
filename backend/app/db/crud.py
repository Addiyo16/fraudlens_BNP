
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Transaction, Flag, AnalystAction


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

ALLOWED_ACTIONS = {"Fraud", "Genuine", "Escalate"}

ALLOWED_STATUSES = {
    "Pending",
    "Fraud",
    "Genuine",
    "Escalate",
}

ALLOWED_RISK_LEVELS = {
    "Low",
    "Medium",
    "High",
}


# --------------------------------------------------
# TRANSACTION CRUD
# --------------------------------------------------

def create_transaction(db: Session, transaction_data: dict):
    """Create a new transaction."""

    required_fields = [
        "txn_id",
        "customer_id",
        "amount",
        "timestamp",
        "city",
        "beneficiary_id",
        "channel",
    ]

    for field in required_fields:
        if field not in transaction_data:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(transaction_data["timestamp"], datetime):
        raise ValueError("timestamp must be a datetime object")

    if db.get(Transaction, transaction_data["txn_id"]) is not None:
        raise ValueError("Transaction ID already exists")

    transaction = Transaction(**transaction_data)

    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Could not create transaction. Check the transaction ID and data."
        ) from exc


def get_transaction(db: Session, txn_id: str):
    """Get a transaction by its ID."""

    return db.get(Transaction, txn_id)


def get_all_transactions(db: Session):
    """Return all transactions in chronological order."""

    return (
        db.query(Transaction)
        .order_by(Transaction.timestamp.desc())
        .all()
    )


def get_transactions_by_customer(db: Session, customer_id: str):
    """Return transactions belonging to one customer."""

    return (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )


def delete_transaction(db: Session, txn_id: str):
    """Delete a transaction by its ID."""

    transaction = db.get(Transaction, txn_id)

    if transaction is None:
        return False

    try:
        db.delete(transaction)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# FRAUD FLAG CRUD
# --------------------------------------------------

def create_flag(db: Session, flag_data: dict):
    """Create a fraud flag for an existing transaction."""

    required_fields = [
        "txn_id",
        "risk_score",
        "risk_level",
        "triggered_rules",
        "explanation",
    ]

    for field in required_fields:
        if field not in flag_data:
            raise ValueError(f"Missing required field: {field}")

    txn_id = flag_data["txn_id"]

    if db.get(Transaction, txn_id) is None:
        raise ValueError("Transaction does not exist")

    existing_flag = (
        db.query(Flag)
        .filter(Flag.txn_id == txn_id)
        .first()
    )

    if existing_flag is not None:
        raise ValueError("A flag already exists for this transaction")

    risk_score = flag_data["risk_score"]

    if (
        isinstance(risk_score, bool)
        or not isinstance(risk_score, int)
        or not 0 <= risk_score <= 100
    ):
        raise ValueError("risk_score must be an integer between 0 and 100")

    if flag_data["risk_level"] not in ALLOWED_RISK_LEVELS:
        raise ValueError("Invalid risk level")

    status = flag_data.get("status", "Pending")

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid flag status")

    if not isinstance(flag_data["triggered_rules"], list):
        raise ValueError("triggered_rules must be a list")

    data = flag_data.copy()
    data["status"] = status

    flag = Flag(**data)

    try:
        db.add(flag)
        db.commit()
        db.refresh(flag)
        return flag

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Could not create flag. Verify the transaction and flag data."
        ) from exc


def get_flag(db: Session, flag_id: int):
    """Get a flag by its database ID."""

    return db.get(Flag, flag_id)


def get_flag_by_transaction(db: Session, txn_id: str):
    """Get the flag associated with a transaction."""

    return (
        db.query(Flag)
        .filter(Flag.txn_id == txn_id)
        .first()
    )


def get_all_flags(
    db: Session,
    risk_level: Optional[str] = None,
    rule: Optional[str] = None,
    status: Optional[str] = None,
):
    """Return flags with optional filters, highest risk first."""

    query = db.query(Flag)

    if risk_level is not None:
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise ValueError("Invalid risk level")

        query = query.filter(Flag.risk_level == risk_level)

    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise ValueError("Invalid flag status")

        query = query.filter(Flag.status == status)

    results = query.order_by(
        Flag.risk_score.desc(),
        Flag.id.asc(),
    ).all()

    # Filter JSON rule lists in Python for SQLite compatibility.
    if rule is not None:
        results = [
            flag
            for flag in results
            if rule in (flag.triggered_rules or [])
        ]

    return results


def get_flags(
    db: Session,
    risk_level: Optional[str] = None,
    rule: Optional[str] = None,
    status: Optional[str] = None,
):
    """Alias for get_all_flags."""

    return get_all_flags(
        db=db,
        risk_level=risk_level,
        rule=rule,
        status=status,
    )


def get_flags_by_risk_level(db: Session, risk_level: str):
    """Return flags matching a risk level."""

    if risk_level not in ALLOWED_RISK_LEVELS:
        raise ValueError("Invalid risk level")

    return (
        db.query(Flag)
        .filter(Flag.risk_level == risk_level)
        .order_by(Flag.risk_score.desc(), Flag.id.asc())
        .all()
    )


def update_flag_status(db: Session, flag_id: int, status: str):
    """Update the review status of a flag."""

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid flag status")

    flag = db.get(Flag, flag_id)

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
# ANALYST ACTION CRUD
# --------------------------------------------------

def create_analyst_action(
    db: Session,
    flag_id: int,
    action: str,
    notes: Optional[str] = None,
):
    """Record an analyst decision and update the flag status."""

    if action not in ALLOWED_ACTIONS:
        raise ValueError(
            "Invalid action. Use Fraud, Genuine, or Escalate."
        )

    flag = db.get(Flag, flag_id)

    if flag is None:
        raise ValueError("Flag does not exist")

    try:
        analyst_action = AnalystAction(
            flag_id=flag_id,
            action=action,
            notes=notes,
            timestamp=datetime.utcnow(),
        )

        # Keep the flag's current status synchronized with the decision.
        flag.status = action

        db.add(analyst_action)
        db.commit()
        db.refresh(analyst_action)

        return analyst_action

    except Exception:
        db.rollback()
        raise


def get_analyst_action(db: Session, action_id: int):
    """Get an analyst action by its ID."""

    return db.get(AnalystAction, action_id)


def get_actions_by_flag(db: Session, flag_id: int):
    """Return all analyst actions for a flag."""

    return (
        db.query(AnalystAction)
        .filter(AnalystAction.flag_id == flag_id)
        .order_by(AnalystAction.timestamp.desc())
        .all()
    )


def get_all_analyst_actions(db: Session):
    """Return all analyst actions, newest first."""

    return (
        db.query(AnalystAction)
        .order_by(AnalystAction.timestamp.desc())
        .all()
    )


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------

def get_total_transactions(db: Session) -> int:
    """Return the total number of transactions."""

    return db.query(Transaction).count()


def get_total_flags(db: Session) -> int:
    """Return the total number of fraud flags."""

    return db.query(Flag).count()


def get_pending_flags(db: Session) -> int:
    """Return the number of flags awaiting review."""

    return (
        db.query(Flag)
        .filter(Flag.status == "Pending")
        .count()
    )


def get_summary_data(db: Session) -> dict:
    """Return summary metrics for the FraudLens dashboard."""

    transactions = get_total_transactions(db)
    flags = get_total_flags(db)
    pending = get_pending_flags(db)

    all_flags = db.query(Flag).all()

    risk_breakdown = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
    }

    rule_breakdown = {}

    for flag in all_flags:
        if flag.risk_level in risk_breakdown:
            risk_breakdown[flag.risk_level] += 1

        for rule_name in (flag.triggered_rules or []):
            rule_breakdown[rule_name] = (
                rule_breakdown.get(rule_name, 0) + 1
            )

    # Aggregate risk scores by customer using flagged transactions.
    customer_scores = {}

    for flag in all_flags:
        transaction = (
            db.query(Transaction)
            .filter(Transaction.txn_id == flag.txn_id)
            .first()
        )

        if transaction is None:
            continue

        customer_id = transaction.customer_id

        customer_scores[customer_id] = (
            customer_scores.get(customer_id, 0) + flag.risk_score
        )

    top_risky_customers = sorted(
        [
            {
                "customer_id": customer_id,
                "combined_risk_score": score,
            }
            for customer_id, score in customer_scores.items()
        ],
        key=lambda item: item["combined_risk_score"],
        reverse=True,
    )[:5]

    return {
        "total_transactions": transactions,
        "total_flagged": flags,
        "pending_flags": pending,
        "risk_breakdown": risk_breakdown,
        "rule_breakdown": rule_breakdown,
        "top_risky_customers": top_risky_customers,
    }
