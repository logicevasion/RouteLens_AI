"""FastAPI application entry point for the local RouteLens API."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from app.routes import router

# Match the frontend's root .env convention while allowing deployment-provided
# environment variables to take precedence.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="RouteLens AI API", version="0.1.0")
app.include_router(router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Report that the local backend is available."""
    return {"status": "ok"}
