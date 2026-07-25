from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..parser import parse_statement

router = APIRouter(tags=["upload"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=schemas.UploadResult)
async def upload_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB).")

    try:
        rows = parse_statement(file.filename, content, password=password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {e}")

    warnings = []
    undated = sum(1 for r in rows if r["date"] is None)
    if undated:
        warnings.append(f"{undated} transaction(s) had no parseable date.")
    unnamed = sum(1 for r in rows if r["counterparty"] in (None, "Unknown"))
    if unnamed:
        warnings.append(f"{unnamed} transaction(s) had no identifiable counterparty name.")

    statement = models.Statement(filename=file.filename, transaction_count=len(rows))
    db.add(statement)
    db.flush()

    for r in rows:
        db.add(models.Transaction(statement_id=statement.id, **r))

    db.commit()
    db.refresh(statement)

    return schemas.UploadResult(
        statement=schemas.StatementOut.model_validate(statement),
        transactions=[schemas.TransactionOut.model_validate(t) for t in statement.transactions],
        warnings=warnings,
    )
