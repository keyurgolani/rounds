from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, Base
from routers import questions, applications

Base.metadata.create_all(bind=engine)

# Lightweight in-place schema evolution for the SQLite dev database.
# SQLAlchemy's `create_all` does not add new columns to existing tables, so
# we add them here for new attributes on existing models. Each statement
# ignores "duplicate column" errors so reruns are safe.
def _ensure_columns():
    from sqlalchemy import text

    statements = [
        "ALTER TABLE applications ADD COLUMN job_description TEXT DEFAULT ''",
        "ALTER TABLE anecdotes ADD COLUMN description TEXT DEFAULT ''",
    ]
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception:
                pass


_ensure_columns()

app = FastAPI(title="Interview Command Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router)
app.include_router(applications.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def seed_if_empty():
    from seed_data import seed_all
    seed_all()
