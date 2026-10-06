from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


# Allowed values
RiskLevel = Literal["Low", "Medium", "High"]

FlagStatus = Literal[
    "Pending",
    "Fraud",
    "Genuine",
    "Escalate"
]

AnalystAction = Literal[
    "Fraud",
    "Genuine",
    "Escalate"
]


# -------------------------
# TRANSACTION
# -------------------------

class TransactionSchema(BaseModel):
    txn_id: str
    customer_id: str
    amount: float = Field(gt=0)
    timestamp: datetime
    city: str
    beneficiary_id: str
    channel: str


# -------------------------
# FLAG
# -------------------------

class FlagCreate(BaseModel):
    txn_id: str
    risk_score: int
    risk_level: RiskLevel
    triggered_rules: List[str]
    explanation: str
    status: FlagStatus = "Pending"


class FlagResponse(BaseModel):
    id: int

    txn_id: str
    customer_id: str
    amount: float
    timestamp: datetime
    city: str
    beneficiary_id: str
    channel: str

    risk_score: int
    risk_level: RiskLevel
    triggered_rules: List[str]
    explanation: str
    status: FlagStatus


# -------------------------
# ANALYST ACTION
# -------------------------

class AnalystActionRequest(BaseModel):
    action: AnalystAction
    notes: Optional[str] = ""


# -------------------------
# UPLOAD RESPONSE
# -------------------------

class UploadResponse(BaseModel):
    uploaded_count: int
    flagged_count: int
    errors: List[str] = []


# -------------------------
# SUMMARY
# -------------------------

class RiskyCustomer(BaseModel):
    customer_id: str
    max_risk_score: int
    flag_count: int


class SummaryResponse(BaseModel):
    total_transactions: int
    total_flagged: int
    rule_breakdown: dict[str, int]
    top_risky_customers: List[RiskyCustomer]