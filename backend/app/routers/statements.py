from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["statements"])


@router.get("/statements", response_model=list[schemas.StatementOut])
def list_statements(db: Session = Depends(get_db)):
    return db.query(models.Statement).order_by(models.Statement.uploaded_at.desc()).all()


@router.get("/statements/{statement_id}", response_model=schemas.StatementOut)
def get_statement(statement_id: int, db: Session = Depends(get_db)):
    stmt = db.get(models.Statement, statement_id)
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found.")
    return stmt


@router.delete("/statements/{statement_id}")
def delete_statement(statement_id: int, db: Session = Depends(get_db)):
    stmt = db.get(models.Statement, statement_id)
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found.")
    db.delete(stmt)
    db.commit()
    return {"ok": True}
