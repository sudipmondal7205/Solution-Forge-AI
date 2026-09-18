"""
FastAPI application entry point.

Run with:  uvicorn backend.main:app --reload

Wires all route modules together and exposes a /health endpoint
so we can verify DB connectivity easily.
"""

from fastapi import FastAPI
from backend.db.database import db
from backend.routers import auth, consultations

app = FastAPI(
    title="SolutionForgeAI API",
    description="Multi-agent AI solution consulting backend.",
    version="0.2.0",
)

app.include_router(auth.router)
app.include_router(consultations.router)


@app.get("/health")
def health_check():
    """Quick check that the API + MongoDB are reachable."""
    db.command("ping")  # raises if MongoDB is not reachable
    return {"status": "ok", "database": "connected"}