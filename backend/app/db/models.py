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

    txn_id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    city = Column(String, nullable=False)
    beneficiary_id = Column(String, nullable=False)
    channel = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_transactions_amount_non_negative",
        ),
    )

    flags = relationship(
        "Flag",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, autoincrement=True)

    txn_id = Column(
        String,
        ForeignKey("transactions.txn_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    risk_score = Column(Integer, nullable=False)

    risk_level = Column(String, nullable=False)

    triggered_rules = Column(
        JSON,
        nullable=False,
        default=list,
    )

    explanation = Column(Text, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="Pending",
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_flags_risk_score",
        ),
        CheckConstraint(
            "risk_level IN ('Low', 'Medium', 'High')",
            name="ck_flags_risk_level",
        ),
        CheckConstraint(
            "status IN ('Pending', 'Fraud', 'Genuine', 'Escalate')",
            name="ck_flags_status",
        ),
    )

    transaction = relationship(
        "Transaction",
        back_populates="flags",
    )

    analyst_actions = relationship(
        "AnalystAction",
        back_populates="flag",
        cascade="all, delete-orphan",
        order_by="AnalystAction.timestamp",
    )


class AnalystAction(Base):
    __tablename__ = "analyst_actions"

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

    __table_args__ = (
        CheckConstraint(
            "action IN ('Fraud', 'Genuine', 'Escalate')",
            name="ck_analyst_actions_action",
        ),
    )

    flag = relationship(
        "Flag",
        back_populates="analyst_actions",
    )