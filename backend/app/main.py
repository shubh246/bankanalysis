from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import Base, engine, run_migrations
from .routers import auth, fundflow, statements, transactions, upload

Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(title="Bank Statement Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(statements.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(fundflow.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
