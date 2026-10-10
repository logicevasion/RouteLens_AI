"""FastAPI application entry point for the local RouteLens API."""

from fastapi import FastAPI

app = FastAPI(title="RouteLens AI API", version="0.1.0")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Report that the local backend is available."""
    return {"status": "ok"}
