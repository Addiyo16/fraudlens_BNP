import io

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException

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


@router.post("/upload")
async def upload_transactions(file: UploadFile = File(...)):
    # --------------------------------------------------
    # 1. Validate file type
    # --------------------------------------------------
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed."
        )

    # --------------------------------------------------
    # 2. Read CSV file
    # --------------------------------------------------
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

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
    # 4. Find duplicate transaction IDs
    # --------------------------------------------------
    duplicate_ids = df[
        df["txn_id"].duplicated(keep=False)
    ]["txn_id"].tolist()

    duplicate_id_set = {
        str(txn_id)
        for txn_id in duplicate_ids
    }

    # --------------------------------------------------
    # 5. Validate rows
    # --------------------------------------------------
    errors = []
    valid_rows = []

    for index, row in df.iterrows():

        # +2 because:
        # dataframe index starts from 0
        # CSV row 1 contains headers
        row_number = index + 2

        row_errors = []

        # ----------------------------------------------
        # Check duplicate txn_id
        # ----------------------------------------------
        if str(row["txn_id"]) in duplicate_id_set:
            row_errors.append("duplicate txn_id")

        # ----------------------------------------------
        # Check empty required fields
        # ----------------------------------------------
        for column in REQUIRED_COLUMNS:

            if pd.isna(row[column]) or str(row[column]).strip() == "":
                row_errors.append(
                    f"missing {column}"
                )

        # ----------------------------------------------
        # Validate amount
        # ----------------------------------------------
        try:
            amount = float(row["amount"])

            if amount <= 0:
                row_errors.append(
                    "amount must be greater than 0"
                )

        except (ValueError, TypeError):
            row_errors.append(
                "invalid amount"
            )

        # ----------------------------------------------
        # Validate timestamp
        # ----------------------------------------------
        try:
            pd.to_datetime(row["timestamp"])

        except Exception:
            row_errors.append(
                "invalid timestamp"
            )

        # ----------------------------------------------
        # Store result
        # ----------------------------------------------
        if row_errors:

            errors.append(
                f"Row {row_number}: "
                + ", ".join(row_errors)
            )

        else:

            valid_rows.append(
                row.to_dict()
            )

    # --------------------------------------------------
    # 6. Temporary response
    #
    # Database storage + detection will be connected
    # during Phase 2 integration.
    # --------------------------------------------------
    return {
        "uploaded_count": len(valid_rows),
        "flagged_count": 0,
        "errors": errors
    }