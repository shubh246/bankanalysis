from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db

router = APIRouter(tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/auth/register", response_model=TokenResponse)
def register(body: Credentials, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="That username is already taken.")

    is_first_user = db.query(models.User).count() == 0

    user = models.User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()

    if is_first_user:
        # statements uploaded before accounts existed belong to whoever registers first
        db.query(models.Statement).filter(models.Statement.user_id.is_(None)).update(
            {"user_id": user.id}
        )

    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id, user.username), username=user.username)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: Credentials, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user.id, user.username), username=user.username)
