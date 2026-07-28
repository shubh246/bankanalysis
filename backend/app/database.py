import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bankstatements.db"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Add columns introduced after the initial deploy that create_all() won't retrofit."""
    inspector = inspect(engine)
    if "statements" not in inspector.get_table_names():
        return  # fresh DB; create_all() already covers this

    existing_cols = {c["name"] for c in inspector.get_columns("statements")}
    is_postgres = engine.dialect.name == "postgresql"

    with engine.begin() as conn:
        added_status = False
        if "status" not in existing_cols:
            conn.execute(text("ALTER TABLE statements ADD COLUMN status VARCHAR DEFAULT 'processing'"))
            added_status = True
        if "error" not in existing_cols:
            conn.execute(text("ALTER TABLE statements ADD COLUMN error VARCHAR"))
        if "warnings" not in existing_cols:
            json_type = "JSONB" if is_postgres else "JSON"
            conn.execute(text(f"ALTER TABLE statements ADD COLUMN warnings {json_type}"))
            conn.execute(text("UPDATE statements SET warnings = '[]'"))
        if added_status:
            # rows that existed before this migration were already fully processed synchronously
            conn.execute(text("UPDATE statements SET status = 'done'"))
        if "user_id" not in existing_cols:
            conn.execute(text("ALTER TABLE statements ADD COLUMN user_id INTEGER"))
        if "content_hash" not in existing_cols:
            conn.execute(text("ALTER TABLE statements ADD COLUMN content_hash VARCHAR"))

