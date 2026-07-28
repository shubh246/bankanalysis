import hashlib
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import CurrentUser, get_current_user
from ..database import SessionLocal, get_db
from ..parser import parse_statement

router = APIRouter(tags=["upload"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _process_statement(statement_id: int, filename: str, content: bytes, password: Optional[str]):
    db = SessionLocal()
    try:
        statement = db.get(models.Statement, statement_id)
        if not statement:
            return

        try:
            rows = parse_statement(filename, content, password=password)
        except ValueError as e:
            statement.status = "failed"
            statement.error = str(e)
            db.commit()
            return
        except Exception as e:
            statement.status = "failed"
            statement.error = f"Failed to parse file: {e}"
            db.commit()
            return

        warnings = []
        undated = sum(1 for r in rows if r["date"] is None)
        if undated:
            warnings.append(f"{undated} transaction(s) had no parseable date.")
        unnamed = sum(1 for r in rows if r["counterparty"] in (None, "Unknown"))
        if unnamed:
            warnings.append(f"{unnamed} transaction(s) had no identifiable counterparty name.")

        for r in rows:
            r["statement_id"] = statement_id
        db.bulk_insert_mappings(models.Transaction, rows)

        statement.transaction_count = len(rows)
        statement.warnings = warnings
        statement.status = "done"
        db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=schemas.UploadResult)
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB).")

    content_hash = hashlib.sha256(content).hexdigest()
    duplicate = (
        db.query(models.Statement)
        .filter(
            models.Statement.user_id == current_user.id,
            models.Statement.content_hash == content_hash,
            models.Statement.status.in_(["processing", "done"]),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This exact file was already uploaded as \"{duplicate.filename}\" "
                f"on {duplicate.uploaded_at.strftime('%Y-%m-%d %H:%M')}."
            ),
        )

    statement = models.Statement(
        user_id=current_user.id, filename=file.filename, transaction_count=0,
        status="processing", warnings=[], content_hash=content_hash,
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)

    background_tasks.add_task(_process_statement, statement.id, file.filename, content, password)

    return schemas.UploadResult(statement=schemas.StatementOut.model_validate(statement))
