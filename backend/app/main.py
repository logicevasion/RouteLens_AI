"""FastAPI application entry point for the local RouteLens API."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, Response

from app.api_usage import (
    BROWSER_MAP_PROVIDER,
    DEFAULT_DAYS,
    PROVIDERS,
    Operation,
    UsageStore,
    UsageUnavailable,
    configured_usage_path,
    observe_usage,
)
from app.routes import router

# Resolve the usage path from the process environment, as the diagnostic CLI does.
usage_path = configured_usage_path()

# Match the frontend's root .env convention while allowing deployment-provided
# environment variables to take precedence.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store: UsageStore = app.state.usage
    await asyncio.to_thread(store.initialize)
    try:
        yield
    finally:
        await store.flush()


async def track_provider_attempts(request: Request) -> AsyncIterator[None]:
    with observe_usage(request.app.state.usage):
        yield


app = FastAPI(title="RouteLens AI API", version="0.1.0", lifespan=lifespan)
app.state.usage = UsageStore(usage_path)
app.include_router(router, dependencies=[Depends(track_provider_attempts)])


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Report that the local backend is available."""
    return {"status": "ok"}


@app.get("/api/usage")
async def get_usage(request: Request, response: Response) -> dict:
    """Report observed backend attempts in the last 30 UTC calendar dates."""
    response.headers["Cache-Control"] = "no-store"
    store: UsageStore = request.app.state.usage
    await store.flush()
    start, end = store.window(DEFAULT_DAYS)
    try:
        report = await asyncio.to_thread(store.read_report, start, end)
    except UsageUnavailable:
        status = "unavailable"
        totals = dict.fromkeys(PROVIDERS)
    else:
        status = "degraded" if report.gaps else "ok"
        totals = report.provider_totals()
        totals[Operation.CAMERA_FRAME.provider] = report.operation_totals()[Operation.CAMERA_FRAME]
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "basis": "backend_observed_attempts",
        "status": status,
        "providers": [
            {
                "provider": provider,
                "status": "unavailable" if attempts is None else "tracked",
                "attempts": attempts,
            }
            for provider, attempts in totals.items()
        ] + [{"provider": BROWSER_MAP_PROVIDER, "status": "untracked", "attempts": None}],
    }
