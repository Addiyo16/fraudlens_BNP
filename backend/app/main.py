from datetime import datetime

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.db.database import engine, Base, get_db
from app.db import models
from app.db.crud import create_transaction


Base.metadata.create_all(bind=engine)

app = FastAPI(title="FraudLens")


@app.get("/")
def root():
    return {"message": "FraudLens backend running"}


@app.post("/test-transaction")
def test_transaction(db: Session = Depends(get_db)):

    transaction_data = {
        "txn_id": "T0001",
        "customer_id": "C001",
        "amount": 5000.0,
        "timestamp": datetime(2026, 9, 30, 10, 30),
        "city": "Pune",
        "beneficiary_id": "B001",
        "channel": "UPI"
    }

    transaction = create_transaction(db, transaction_data)

    return {
        "txn_id": transaction.txn_id,
        "customer_id": transaction.customer_id,
        "amount": transaction.amount
    }