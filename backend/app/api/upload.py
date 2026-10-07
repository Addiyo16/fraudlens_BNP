import io

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import crud
from app.schemas.schemas import TransactionSchema
from app.services.detection import evaluate_transaction


router = APIRouter()


REQUIRED_COLUMNS = {
    "txn_id",
    "customer_id",
    "amount",
    "timestamp",
    "city",
    "beneficiary_id",
    "channel",
}


def db_transaction_to_schema(transaction):
    """
    Convert a SQLAlchemy Transaction object into the
    TransactionSchema expected by the detection engine.
    """
    return TransactionSchema(
        txn_id=transaction.txn_id,
        customer_id=transaction.customer_id,
        amount=transaction.amount,
        timestamp=transaction.timestamp,
        city=transaction.city,
        beneficiary_id=transaction.beneficiary_id,
        channel=transaction.channel,
    )


@router.post("/upload")
async def upload_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------
    # 1. Validate file type
    # --------------------------------------------------
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed."
        )

    # --------------------------------------------------
    # 2. Read CSV
    # --------------------------------------------------
    try:
        contents = await file.read()

        df = pd.read_csv(
            io.BytesIO(contents)
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Unable to read CSV file."
        )

    # --------------------------------------------------
    # 3. Validate required columns
    # --------------------------------------------------
    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )
        )

    # --------------------------------------------------
    # 4. Find duplicate txn_id values inside this CSV
    # --------------------------------------------------
    duplicate_ids = df[
        df["txn_id"].duplicated(keep=False)
    ]["txn_id"].tolist()

    duplicate_id_set = {
        str(txn_id)
        for txn_id in duplicate_ids
    }

    errors = []
    valid_transactions = []

    # --------------------------------------------------
    # 5. Validate each CSV row
    # --------------------------------------------------
    for index, row in df.iterrows():

        row_number = index + 2

        row_errors = []

        # Check required fields
        for column in REQUIRED_COLUMNS:
            if (
                pd.isna(row[column])
                or str(row[column]).strip() == ""
            ):
                row_errors.append(
                    f"missing {column}"
                )

        # Duplicate inside uploaded CSV
        if str(row["txn_id"]) in duplicate_id_set:
            row_errors.append(
                "duplicate txn_id"
            )

        # Validate amount
        try:
            amount = float(row["amount"])

            if amount <= 0:
                row_errors.append(
                    "amount must be greater than 0"
                )

        except (ValueError, TypeError):
            amount = None
            row_errors.append(
                "invalid amount"
            )

        # Validate timestamp
        try:
            timestamp = pd.to_datetime(
                row["timestamp"],
                errors="raise"
            ).to_pydatetime()

        except Exception:
            timestamp = None
            row_errors.append(
                "invalid timestamp"
            )

        # If validation failed, don't process this row
        if row_errors:
            errors.append(
                f"Row {row_number}: "
                + ", ".join(row_errors)
            )

            continue

        # --------------------------------------------------
        # Create clean transaction object
        # --------------------------------------------------
        transaction_data = {
            "txn_id": str(row["txn_id"]).strip(),
            "customer_id": str(row["customer_id"]).strip(),
            "amount": amount,
            "timestamp": timestamp,
            "city": str(row["city"]).strip(),
            "beneficiary_id": str(
                row["beneficiary_id"]
            ).strip(),
            "channel": str(row["channel"]).strip(),
        }

        valid_transactions.append(
            (
                row_number,
                transaction_data
            )
        )

    # --------------------------------------------------
    # 6. Process chronologically
    # --------------------------------------------------
    valid_transactions.sort(
        key=lambda item: item[1]["timestamp"]
    )

    uploaded_count = 0
    flagged_count = 0

    # --------------------------------------------------
    # 7. Store + detect + flag
    # --------------------------------------------------
    for row_number, transaction_data in valid_transactions:

        txn_id = transaction_data["txn_id"]
        customer_id = transaction_data["customer_id"]

        # ----------------------------------------------
        # Check duplicate against existing database
        # ----------------------------------------------
        existing_transaction = crud.get_transaction(
            db,
            txn_id
        )

        if existing_transaction is not None:
            errors.append(
                f"Row {row_number}: txn_id {txn_id} "
                f"already exists in database"
            )

            continue

        # ----------------------------------------------
        # Fetch PREVIOUS customer history
        #
        # Important:
        # this happens BEFORE current transaction insert.
        # ----------------------------------------------
        db_history = crud.get_customer_transactions(
            db,
            customer_id
        )

        customer_history = [
            db_transaction_to_schema(transaction)
            for transaction in db_history
        ]

        current_transaction = TransactionSchema(
            **transaction_data
        )

        # ----------------------------------------------
        # Run fraud detection
        # ----------------------------------------------
        result = evaluate_transaction(
            current_transaction,
            customer_history
        )

        # ----------------------------------------------
        # Store transaction
        # ----------------------------------------------
        try:
            crud.create_transaction(
                db,
                transaction_data
            )

            uploaded_count += 1

        except Exception as exc:
            errors.append(
                f"Row {row_number}: "
                f"failed to store transaction - {str(exc)}"
            )

            continue

        # ----------------------------------------------
        # Create flag only if a rule fired
        # ----------------------------------------------
        if result["risk_score"] > 0:

            flag_data = {
                "txn_id": txn_id,
                "risk_score": result["risk_score"],
                "risk_level": result["risk_level"],
                "triggered_rules": result["triggered_rules"],
                "explanation": result["explanation"],
                "status": "Pending",
            }

            try:
                crud.create_flag(
                    db,
                    flag_data
                )

                flagged_count += 1

            except Exception as exc:
                errors.append(
                    f"Row {row_number}: "
                    f"transaction stored but flag creation failed - "
                    f"{str(exc)}"
                )

    # --------------------------------------------------
    # 8. Final API response
    # --------------------------------------------------
    return {
        "uploaded_count": uploaded_count,
        "flagged_count": flagged_count,
        "errors": errors
    }