from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    statement_id: int
    date: Optional[date]
    description: str
    counterparty: Optional[str]
    channel: Optional[str]
    debit: Optional[float]
    credit: Optional[float]
    amount: float
    direction: str
    balance: Optional[float]


class StatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    account_name: Optional[str]
    uploaded_at: datetime
    transaction_count: int
    status: str
    error: Optional[str] = None
    warnings: list[str] = []


class UploadResult(BaseModel):
    statement: StatementOut


class FundFlowNode(BaseModel):
    id: str
    label: str
    kind: str  # "account" | "counterparty"
    total_in: float = 0.0
    total_out: float = 0.0


class FundFlowEdge(BaseModel):
    source: str
    target: str
    amount: float
    count: int
    direction: str  # "in" | "out" relative to the account
    dates: list[str] = []


class FundFlowResponse(BaseModel):
    nodes: list[FundFlowNode]
    edges: list[FundFlowEdge]
