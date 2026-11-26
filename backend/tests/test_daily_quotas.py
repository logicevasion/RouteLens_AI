"""Exercise strict daily admission through the API, HTTPX, and a shared SQLite file."""

import asyncio
import multiprocessing
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from threading import Event

import httpx
import pytest

from app import api_usage, routes
from app.api_usage import DailyQuotaExhausted, DailyQuotaUnavailable, Operation, UsageStore
from app.geocoding import MapTilerGeocoder
from app.main import app
from app.routing import OpenRouteServiceRouter

MAPTILER = Operation.MAPTILER_GEOCODING
ORS = Operation.ORS_DIRECTIONS
NOW = datetime(2026, 11, 26, 23, 59, 59, 500_000, tzinfo=timezone.utc)
ROUTE_REQUEST = {
    "origin": {"name": "Richmond", "latitude": 49.16, "longitude": -123.14},
    "destination": {"name": "Vancouver", "latitude": 49.28, "longitude": -123.12},
}


def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def search(api, operation):
    if operation is MAPTILER:
        return await api.get("/api/geocoding/search", params={"q": "Vancouver"})
    return await api.post("/api/routes/driving", json=ROUTE_REQUEST)


@pytest.fixture
def mock_providers(monkeypatch):
    def install(handler):
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(routes, "MapTilerGeocoder", lambda: MapTilerGeocoder("test", transport=transport))
        monkeypatch.setattr(routes, "OpenRouteServiceRouter", lambda: OpenRouteServiceRouter("test", transport=transport))

    return install


@pytest.fixture
def settings(monkeypatch, usage_store):
    def configure(mapt, ors, *, now=lambda: NOW):
        monkeypatch.setenv("MAPTILER_GEOCODING_DAILY_LIMIT", str(mapt))
        monkeypatch.setenv("OPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT", str(ors))
        store = UsageStore(usage_store.path, daily_limits=api_usage.configured_daily_limits(), now=now)
        monkeypatch.setattr(app.state, "usage", store)
        return store

    return configure


@pytest.mark.parametrize(("operation", "other", "limit", "message"), [
    (MAPTILER, ORS, 200, "Location search has reached today's usage limit. Please try again tomorrow."),
    (ORS, MAPTILER, 100, "Route searches have reached today's usage limit. Please try again tomorrow."),
])
def test_default_limit_counts_once_and_is_independent(
    usage_store, mock_providers, monkeypatch, operation, other, limit, message,
):
    monkeypatch.delenv("MAPTILER_GEOCODING_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("OPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT", raising=False)
    assert api_usage.configured_daily_limits()[operation] == limit
    dispatches = []

    def dispatch(request):
        dispatches.append(request.url.host)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    mock_providers(dispatch)

    async def run():
        async with client() as api:
            assert (await search(api, operation)).status_code == 200
            assert usage_store.read_report(*usage_store.window(30)).operation_totals()[operation] == 1
            for _ in range(limit - 1):
                assert (await search(api, operation)).status_code == 200
            exceeded = await search(api, operation)
            assert exceeded.status_code == 429
            assert exceeded.json() == {"detail": {"code": "daily_quota_exhausted", "message": message}}
            assert exceeded.headers["Retry-After"] == "43200"
            assert len(dispatches) == limit
            assert (await search(api, other)).status_code == 200
            report = (await api.get("/api/usage")).json()
            assert report["status"] == "ok"
            totals = {row["provider"]: row["attempts"] for row in report["providers"]}
            assert (totals[operation.provider], totals[other.provider]) == (limit, 1)

    asyncio.run(run())
    assert len(dispatches) == limit + 1


@pytest.mark.parametrize(("operation", "failure", "status", "code"), [
    (MAPTILER, "timeout", 502, None),
    (MAPTILER, "provider_429", 502, None),
    (ORS, "timeout", 504, "routing_timeout"),
    (ORS, "provider_429", 503, "routing_rate_limited"),
])
def test_upstream_errors_consume_quota(settings, mock_providers, operation, failure, status, code):
    with closing(settings(1, 1)) as store:
        def dispatch(request):
            if failure == "timeout":
                raise httpx.ReadTimeout("synthetic private URL", request=request)
            return httpx.Response(429, text="synthetic private body")

        mock_providers(dispatch)

        async def run():
            async with client() as api:
                failed = await search(api, operation)
                assert failed.status_code == status
                assert "synthetic private" not in failed.text
                if code:
                    assert failed.json()["detail"]["code"] == code
                blocked = await search(api, operation)
                assert blocked.status_code == 429
                assert blocked.json()["detail"]["code"] == "daily_quota_exhausted"
                assert blocked.headers["Retry-After"] == "1"

        asyncio.run(run())
        assert store.read_report(*store.window(30)).counts == {(store.today(), operation): 1}


def test_cancelled_provider_request_retains_reservation(settings, mock_providers):
    async def run():
        entered = asyncio.Event()

        async def dispatch(_request):
            entered.set()
            await asyncio.Future()

        mock_providers(dispatch)
        async with client() as api:
            pending = asyncio.create_task(search(api, MAPTILER))
            await asyncio.wait_for(entered.wait(), 2)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert (await search(api, MAPTILER)).status_code == 429

    with closing(settings(1, 2)) as store:
        asyncio.run(run())
        assert store.read_report(*store.window(30)).counts == {(store.today(), MAPTILER): 1}


def test_lifespan_restart_retains_counts_and_utc_midnight_resets(settings, mock_providers):
    clock = [NOW.astimezone(timezone(timedelta(hours=-8)))]
    mock_providers(lambda _: httpx.Response(200, json={"type": "FeatureCollection", "features": []}))

    async def run():
        first = settings(1, 2, now=lambda: clock[0])
        async with app.router.lifespan_context(app), client() as api:
            assert (await search(api, MAPTILER)).status_code == 200
        restarted = settings(1, 2, now=lambda: clock[0])
        assert restarted.path == first.path
        async with app.router.lifespan_context(app), client() as api:
            assert (await search(api, MAPTILER)).status_code == 429
            clock[0] += timedelta(milliseconds=500)
            assert (await search(api, MAPTILER)).status_code == 200
            blocked = await search(api, MAPTILER)
            assert blocked.status_code == 429
            assert blocked.headers["Retry-After"] == "86400"
        assert restarted.read_report(*restarted.window(30)).counts == {
            (NOW.date(), MAPTILER): 1,
            (NOW.date() + timedelta(days=1), MAPTILER): 1,
        }

    asyncio.run(run())


def test_simultaneous_requests_grant_the_final_slot_once(settings, mock_providers):
    dispatches = []

    async def dispatch(request):
        dispatches.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    mock_providers(dispatch)

    async def run():
        async with client() as api:
            assert (await search(api, ORS)).status_code == 200
            contenders = await asyncio.gather(*(search(api, ORS) for _ in range(16)))
            assert sorted(response.status_code for response in contenders) == [200] + [429] * 15

    with closing(settings(1, 2)) as store:
        asyncio.run(run())
        assert len(dispatches) == 2
        assert store.read_report(*store.window(30)).counts == {(NOW.date(), ORS): 2}


def reserve_in_process(path, barrier, results):
    with closing(UsageStore(path, now=lambda: NOW, daily_limits={MAPTILER: 2})) as store:
        barrier.wait(timeout=10)
        try:
            asyncio.run(store.reserve(MAPTILER))
        except DailyQuotaExhausted:
            results.put("exhausted")
        else:
            results.put("admitted")


def test_independent_processes_share_the_final_slot(usage_store):
    usage_store.record(MAPTILER, NOW.date())
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(target=reserve_in_process, args=(usage_store.path, barrier, results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    try:
        assert sorted(results.get(timeout=10) for _ in processes) == ["admitted", "exhausted"]
    finally:
        for process in processes:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        results.close()
        results.join_thread()
    assert [process.exitcode for process in processes] == [0, 0]
    assert usage_store.read_report(*usage_store.window(30)).counts == {(NOW.date(), MAPTILER): 2}


@pytest.mark.parametrize("failure", ["locked", "corrupt", "read_only", "unavailable"])
def test_storage_failures_block_both_providers(usage_store, mock_providers, monkeypatch, caplog, failure):
    def unexpected_dispatch(_request):
        pytest.fail("dispatched without a committed quota reservation")

    mock_providers(unexpected_dispatch)

    async def run():
        async with client() as api:
            for operation, message in [
                (MAPTILER, "Location search is temporarily unavailable. Please try again."),
                (ORS, "Driving routes are temporarily unavailable. Please try again."),
            ]:
                response = await search(api, operation)
                assert response.status_code == 503
                assert response.json() == {"detail": {"code": "daily_quota_unavailable", "message": message}}
                assert "Retry-After" not in response.headers

    path = usage_store.path
    if failure == "locked":
        usage_store.initialize()
        with closing(sqlite3.connect(path)) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            asyncio.run(run())
    else:
        if failure == "read_only":
            usage_store.initialize()
            monkeypatch.setattr(usage_store, "_open_writer", lambda: sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True))
        elif failure == "corrupt":
            path.parent.mkdir()
            path.write_bytes(b"corrupt quota database")
        else:
            path.parent.touch()
        asyncio.run(run())
    assert str(path.parent) not in caplog.text
    assert "api_usage.admission_error" in caplog.text
    if failure in ("locked", "read_only"):
        report = usage_store.read_report(*usage_store.window(30))
        assert not report.counts and not report.gaps


def test_admission_wait_is_bounded_and_leaves_default_executor_free(settings, monkeypatch):
    monkeypatch.setattr(api_usage, "MAX_PENDING_ADMISSIONS", 2)
    monkeypatch.setattr(api_usage, "ADMISSION_TIMEOUT_SECONDS", 0.1)
    started, release = Event(), Event()

    def hold_writer(*_args):
        started.set()
        assert release.wait(5)

    async def run(store):
        asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1))
        store.count_dispatch(Operation.CAMERA_FRAME)
        assert await asyncio.to_thread(started.wait, 2)
        pending = [asyncio.create_task(store.reserve(MAPTILER)) for _ in range(2)]
        await asyncio.sleep(0)
        assert await asyncio.wait_for(asyncio.to_thread(lambda: "available"), 2) == "available"
        assert all(not request.done() for request in pending)
        with pytest.raises(DailyQuotaUnavailable):
            await store.reserve(MAPTILER)
        for request in pending:
            with pytest.raises(DailyQuotaUnavailable):
                await asyncio.wait_for(request, 1)
        # Timed-out jobs still hold their queue slots until the worker retires them.
        with pytest.raises(DailyQuotaUnavailable):
            await store.reserve(ORS)
        release.set()
        await store.flush()
        assert not store.read_report(*store.window(30)).counts
        await store.reserve(MAPTILER)

    with closing(settings(1, 1)) as store:
        store.initialize()
        monkeypatch.setattr(store, "record", hold_writer)
        try:
            asyncio.run(run(store))
        finally:
            release.set()
        assert store.read_report(*store.window(30)).counts == {(NOW.date(), MAPTILER): 1}


@pytest.mark.parametrize("value", ["", "0", "-1", "1.5", "1_000", "never", "9223372036854775808"])
def test_invalid_limits_are_rejected(monkeypatch, value):
    monkeypatch.setenv("MAPTILER_GEOCODING_DAILY_LIMIT", value)
    with pytest.raises(ValueError, match="MAPTILER_GEOCODING_DAILY_LIMIT"):
        api_usage.configured_daily_limits()


def test_startup_loads_dotenv_before_validating_limits_and_honors_process_env(tmp_path, monkeypatch):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("MAPTILER_GEOCODING_DAILY_LIMIT=0\nOPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT=4\n")
    monkeypatch.delenv("MAPTILER_GEOCODING_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("OPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT", raising=False)
    script = """
import sys
import dotenv
load = dotenv.load_dotenv
dotenv.load_dotenv = lambda _: load(sys.argv[1])
from app.main import app
print(list(app.state.usage._daily_limits.values()))
"""
    command = [sys.executable, "-c", script, str(dotenv_file)]
    failed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    assert failed.returncode != 0
    assert "MAPTILER_GEOCODING_DAILY_LIMIT must be an integer" in failed.stderr
    monkeypatch.setenv("MAPTILER_GEOCODING_DAILY_LIMIT", "100")
    started = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
    assert started.stdout.strip() == "[100, 4]"
