from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    statements = relationship("Statement", back_populates="owner")


class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    transaction_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing | done | failed
    error = Column(String, nullable=True)
    warnings = Column(JSON, default=list)

    transactions = relationship(
        "Transaction", back_populates="statement", cascade="all, delete-orphan"
    )
    owner = relationship("User", back_populates="statements")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=False)

    date = Column(Date, nullable=True)
    description = Column(String, nullable=False, default="")
    counterparty = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=True)  # NEFT, IMPS, UPI, RTGS, ATM, CHQ, OTHER
    debit = Column(Float, nullable=True)
    credit = Column(Float, nullable=True)
    amount = Column(Float, nullable=False, index=True)  # abs(debit or credit)
    direction = Column(String, nullable=False)  # "debit" | "credit"
    balance = Column(Float, nullable=True)

    statement = relationship("Statement", back_populates="transactions")
