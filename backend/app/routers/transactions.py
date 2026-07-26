from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=list[schemas.TransactionOut])
def search_transactions(
    amount: Optional[float] = Query(None, description="Exact amount to match"),
    amount_tolerance: float = Query(0.0, description="+/- tolerance around `amount`"),
    amount_min: Optional[float] = Query(None),
    amount_max: Optional[float] = Query(None),
    counterparty: Optional[str] = Query(None, description="Substring match on name"),
    direction: Optional[str] = Query(None, pattern="^(debit|credit)$"),
    statement_ids: Optional[str] = Query(None, description="Comma-separated statement ids to include"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(500, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(models.Transaction)

    if amount is not None:
        lo, hi = amount - amount_tolerance, amount + amount_tolerance
        q = q.filter(models.Transaction.amount >= lo, models.Transaction.amount <= hi)
    if amount_min is not None:
        q = q.filter(models.Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.filter(models.Transaction.amount <= amount_max)
    if counterparty:
        q = q.filter(models.Transaction.counterparty.ilike(f"%{counterparty}%"))
    if direction:
        q = q.filter(models.Transaction.direction == direction)
    if statement_ids:
        ids = [int(x) for x in statement_ids.split(",") if x.strip()]
        if ids:
            q = q.filter(models.Transaction.statement_id.in_(ids))
    if date_from is not None:
        q = q.filter(models.Transaction.date >= date_from)
    if date_to is not None:
        q = q.filter(models.Transaction.date <= date_to)

    q = q.order_by(models.Transaction.date.desc().nullslast(), models.Transaction.id.desc())
    return q.limit(limit).all()
