from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.db.database import engine, Base, get_db
from app.db import models
from app.db.crud import create_transaction

from app.api import upload, flags, summary


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="FraudLens API",
    version="1.0.0"
)


# Allow React frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# FraudLens API routes
app.include_router(upload.router)
app.include_router(flags.router)
app.include_router(summary.router)


@app.get("/")
def root():
    return {
        "name": "FraudLens",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# Temporary database test endpoint from Dev 2
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