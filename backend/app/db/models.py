
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    # Fields from train.csv and test.csv
    transaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    merchant_category = Column(Integer, nullable=False)
    country = Column(Integer, nullable=False)
    device_id = Column(Integer, nullable=False)
    channel = Column(Integer, nullable=False)
    hours_since_prev_txn = Column(Float, nullable=False)

    # Present in train.csv; NULL for unlabelled test transactions
    label = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transaction_amount"),
        CheckConstraint(
            "hours_since_prev_txn >= 0",
            name="ck_transaction_previous_hours",
        ),
        CheckConstraint(
            "label IS NULL OR label IN (0, 1)",
            name="ck_transaction_label",
        ),
    )

    flags = relationship(
        "Flag",
        back_populates="transaction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Flag(Base):
    __tablename__ = "flags"

    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_flag_risk_score",
        ),
        CheckConstraint(
            "risk_level IN ('Low', 'Medium', 'High')",
            name="ck_flag_risk_level",
        ),
        CheckConstraint(
            "status IN ('Pending', 'Fraud', 'Genuine', 'Escalate')",
            name="ck_flag_status",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    transaction_id = Column(
        Integer,
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    triggered_rules = Column(JSON, nullable=False, default=list)
    explanation = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="Pending", index=True)

    transaction = relationship("Transaction", back_populates="flags")

    analyst_actions = relationship(
        "AnalystAction",
        back_populates="flag",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AnalystAction.timestamp",
    )


class AnalystAction(Base):
    __tablename__ = "analyst_actions"

    __table_args__ = (
        CheckConstraint(
            "action IN ('Fraud', 'Genuine', 'Escalate')",
            name="ck_analyst_action",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    flag_id = Column(
        Integer,
        ForeignKey("flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)

    flag = relationship("Flag", back_populates="analyst_actions")
