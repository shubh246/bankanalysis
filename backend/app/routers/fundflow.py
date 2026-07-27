from collections import defaultdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import CurrentUser, get_current_user
from ..database import get_db

router = APIRouter(tags=["fundflow"])

ACCOUNT_NODE_ID = "account"


@router.get("/fundflow", response_model=schemas.FundFlowResponse)
def fund_flow(
    amount: Optional[float] = Query(None, description="Exact amount to trace"),
    amount_tolerance: float = Query(0.0),
    amount_min: Optional[float] = Query(None),
    amount_max: Optional[float] = Query(None),
    counterparty: Optional[str] = Query(None),
    statement_ids: Optional[str] = Query(None, description="Comma-separated statement ids to include"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    q = (
        db.query(models.Transaction)
        .join(models.Statement, models.Transaction.statement_id == models.Statement.id)
        .filter(models.Statement.user_id == current_user.id)
    )

    if amount is not None:
        lo, hi = amount - amount_tolerance, amount + amount_tolerance
        q = q.filter(models.Transaction.amount >= lo, models.Transaction.amount <= hi)
    if amount_min is not None:
        q = q.filter(models.Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.filter(models.Transaction.amount <= amount_max)
    if counterparty:
        q = q.filter(models.Transaction.counterparty.ilike(f"%{counterparty}%"))
    if statement_ids:
        ids = [int(x) for x in statement_ids.split(",") if x.strip()]
        if ids:
            q = q.filter(models.Transaction.statement_id.in_(ids))
    if date_from is not None:
        q = q.filter(models.Transaction.date >= date_from)
    if date_to is not None:
        q = q.filter(models.Transaction.date <= date_to)

    txns = q.all()

    edge_agg: dict[str, dict] = defaultdict(
        lambda: {"amount": 0.0, "count": 0, "dates": [], "direction": None, "label": None}
    )
    account_in = 0.0
    account_out = 0.0
    cp_totals: dict[str, dict] = defaultdict(lambda: {"in": 0.0, "out": 0.0})

    for t in txns:
        name = (t.counterparty or "Unknown").strip() or "Unknown"
        key = name.lower()
        edge_key = f"{key}|{t.direction}"
        agg = edge_agg[edge_key]
        agg["amount"] += t.amount
        agg["count"] += 1
        agg["direction"] = "in" if t.direction == "credit" else "out"
        agg["label"] = name
        if t.date and len(agg["dates"]) < 25:
            agg["dates"].append(t.date.isoformat())

        if t.direction == "credit":
            account_in += t.amount
            cp_totals[key]["out"] += t.amount  # money flows out of counterparty into account
        else:
            account_out += t.amount
            cp_totals[key]["in"] += t.amount  # money flows into counterparty from account
        cp_totals[key]["label"] = name

    nodes = [
        schemas.FundFlowNode(
            id=ACCOUNT_NODE_ID,
            label="My Account",
            kind="account",
            total_in=round(account_in, 2),
            total_out=round(account_out, 2),
        )
    ]
    for key, totals in cp_totals.items():
        nodes.append(
            schemas.FundFlowNode(
                id=f"cp:{key}",
                label=totals["label"],
                kind="counterparty",
                total_in=round(totals["in"], 2),
                total_out=round(totals["out"], 2),
            )
        )

    edges = []
    for edge_key, agg in edge_agg.items():
        key = edge_key.rsplit("|", 1)[0]
        cp_id = f"cp:{key}"
        if agg["direction"] == "in":
            source, target = cp_id, ACCOUNT_NODE_ID
        else:
            source, target = ACCOUNT_NODE_ID, cp_id
        edges.append(
            schemas.FundFlowEdge(
                source=source,
                target=target,
                amount=round(agg["amount"], 2),
                count=agg["count"],
                direction=agg["direction"],
                dates=sorted(agg["dates"]),
            )
        )

    return schemas.FundFlowResponse(nodes=nodes, edges=edges)
