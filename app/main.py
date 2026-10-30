"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import get_connection, init_db, seed_db, DB_PATH
from app.routes.matches import router as matches_router


# ---------------------------------------------------------------------------
# Lifespan: create / seed the database once on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Ensure the database exists and is seeded before serving requests."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        # Check whether the candidates table already exists
        table = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='candidates'"
        ).fetchone()
        if table is None:
            init_db(conn)
            seed_db(conn)
        else:
            count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM candidates"
            ).fetchone()
            if count["cnt"] == 0:
                seed_db(conn)
    finally:
        conn.close()
    yield  # application runs here


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RecruiterFlow Bot",
    description=(
        "A backend service that ingests candidate profiles and job openings, "
        "then ranks the best matches for each using a transparent, "
        "rule-based scoring algorithm."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(matches_router)


@app.get("/", summary="Health check")
def root():
    """Simple health-check endpoint."""
    return {
        "status": "ok",
        "message": (
            "RecruiterFlow Bot API is running. "
            "Visit /docs for interactive API documentation."
        ),
    }
