from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import CurrentUser, get_current_user
from ..database import get_db

router = APIRouter(tags=["statements"])


@router.get("/statements", response_model=list[schemas.StatementOut])
def list_statements(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return (
        db.query(models.Statement)
        .filter(models.Statement.user_id == current_user.id)
        .order_by(models.Statement.uploaded_at.desc())
        .all()
    )


@router.get("/statements/{statement_id}", response_model=schemas.StatementOut)
def get_statement(
    statement_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
):
    stmt = (
        db.query(models.Statement)
        .filter(models.Statement.id == statement_id, models.Statement.user_id == current_user.id)
        .first()
    )
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found.")
    return stmt


@router.delete("/statements/{statement_id}")
def delete_statement(
    statement_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)
):
    stmt = (
        db.query(models.Statement)
        .filter(models.Statement.id == statement_id, models.Statement.user_id == current_user.id)
        .first()
    )
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found.")
    db.delete(stmt)
    db.commit()
    return {"ok": True}
