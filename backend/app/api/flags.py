from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas.schemas import AnalystActionRequest


router = APIRouter()


def build_flag_response(db: Session, flag):
    """
    Combine Flag data with its related Transaction data
    to produce the public API object expected by frontend.
    """

    transaction = crud.get_transaction(
        db,
        flag.txn_id
    )

    if transaction is None:
        return None

    return {
        "id": flag.id,
        "txn_id": transaction.txn_id,
        "customer_id": transaction.customer_id,
        "amount": transaction.amount,
        "timestamp": transaction.timestamp,
        "city": transaction.city,
        "beneficiary_id": transaction.beneficiary_id,
        "channel": transaction.channel,

        "risk_score": flag.risk_score,
        "risk_level": flag.risk_level,
        "triggered_rules": flag.triggered_rules,
        "explanation": flag.explanation,
        "status": flag.status,
    }


# --------------------------------------------------
# GET /flags
# --------------------------------------------------

@router.get("/flags")
def get_flags(
    risk_level: Optional[str] = Query(default=None),
    rule: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return all fraud flags.

    Optional filters:
    ?risk_level=High
    ?rule=HIGH_AMOUNT
    """

    valid_risk_levels = {
        "Low",
        "Medium",
        "High",
    }

    valid_rules = {
        "HIGH_AMOUNT",
        "NIGHT_TRANSACTION",
        "RAPID_FIRE",
        "NEW_LOCATION",
    }

    if risk_level is not None:
        if risk_level not in valid_risk_levels:
            raise HTTPException(
                status_code=400,
                detail="risk_level must be Low, Medium, or High."
            )

    if rule is not None:
        if rule not in valid_rules:
            raise HTTPException(
                status_code=400,
                detail="Invalid rule."
            )

    flags = crud.get_flags(db)

    results = []

    for flag in flags:

        # Risk-level filter
        if (
            risk_level is not None
            and flag.risk_level != risk_level
        ):
            continue

        # Rule filter
        if (
            rule is not None
            and rule not in flag.triggered_rules
        ):
            continue

        response = build_flag_response(
            db,
            flag
        )

        if response is not None:
            results.append(response)

    # Highest-risk transactions first
    results.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    return results


# --------------------------------------------------
# PATCH /flags/{id}
# --------------------------------------------------

@router.patch("/flags/{flag_id}")
def review_flag(
    flag_id: int,
    request: AnalystActionRequest,
    db: Session = Depends(get_db),
):
    """
    Record an analyst decision.

    create_analyst_action() performs:
    - analyst action insertion
    - flag status update
    - one atomic database commit
    """

    flag = crud.get_flag(
        db,
        flag_id
    )

    if flag is None:
        raise HTTPException(
            status_code=404,
            detail="Flag not found."
        )

    try:
        crud.create_analyst_action(
            db=db,
            flag_id=flag_id,
            action=request.action,
            notes=request.notes,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to record analyst action."
        )

    # Fetch updated flag
    updated_flag = crud.get_flag(
        db,
        flag_id
    )

    response = build_flag_response(
        db,
        updated_flag
    )

    return response