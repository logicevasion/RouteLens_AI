"""SQLite, application dispatch, reporting, and CLI regressions without live services."""

import asyncio
import runpy
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import httpx
import pytest

from app import geocoding, routes
from app.api_usage import (
    BROWSER_MAP_PROVIDER,
    PROVIDERS,
    Operation,
    UsageStore,
    observe_usage,
    usage_hooks,
)
from app.main import app

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "api_usage_report.py"


@asynccontextmanager
async def running_api():
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def rows_by_provider(payload):
    return {row["provider"]: (row["status"], row["attempts"]) for row in payload["providers"]}


def test_creation_atomic_increments_and_persistence(usage_store):
    path, day = usage_store.path, usage_store.today()
    assert not path.exists()
    usage_store.record(Operation.ORS_DIRECTIONS, day)
    # Use independent connections and store instances, as separate workers would.
    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(lambda _: UsageStore(path).record(Operation.ORS_DIRECTIONS, day), range(80)))

    report = UsageStore(path).read_report(day, day)
    assert report.counts == {(day, Operation.ORS_DIRECTIONS): 81}
    assert not report.gaps


def test_api_uses_utc_window_and_groups_all_providers(monkeypatch, usage_store):
    clock = [datetime(2026, 11, 25, 15, 59, tzinfo=timezone(timedelta(hours=-8)))]
    store = UsageStore(usage_store.path, now=lambda: clock[0])
    monkeypatch.setattr(app.state, "usage", store)
    assert store.today() == date(2026, 11, 25)
    clock[0] += timedelta(minutes=1)
    assert store.today() == date(2026, 11, 26)

    async def run():
        async with running_api() as client:
            empty = (await client.get("/api/usage")).json()
            assert empty["status"] == "ok"
            assert rows_by_provider(empty) == {
                **dict.fromkeys(PROVIDERS, ("tracked", 0)),
                BROWSER_MAP_PROVIDER: ("untracked", None),
            }
            for day, operation in [
                (date(2026, 10, 27), Operation.OPENROUTER_VISION),
                (date(2026, 10, 28), Operation.OPENROUTER_VISION),
                (date(2026, 11, 26), Operation.OPENROUTER_BRIEFING),
                (date(2026, 11, 27), Operation.OPENROUTER_BRIEFING),
            ]:
                store.record(operation, day)
            return empty, await client.get("/api/usage")

    empty, response = asyncio.run(run())
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert (payload["start_date"], payload["end_date"]) == ("2026-10-28", "2026-11-26")
    assert payload["basis"] == "backend_observed_attempts"
    assert rows_by_provider(payload) == {
        **rows_by_provider(empty),
        "openrouter": ("tracked", 2),
    }
    assert sum(store.read_report(date(2026, 10, 27), date(2026, 11, 27)).counts.values()) == 4


def test_public_camera_count_includes_only_frames_and_cli_keeps_all_attempts(
    usage_store, monkeypatch, capsys,
):
    today = usage_store.today()
    yesterday = today - timedelta(days=1)
    for operation, day, count in [
        (Operation.CAMERA_CATALOGUE, yesterday, 3),
        (Operation.CAMERA_PAGE, yesterday, 220),
        (Operation.CAMERA_FRAME, today, 3),
    ]:
        for _ in range(count):
            usage_store.record(operation, day)

    async def read():
        async with running_api() as client:
            return (await client.get("/api/usage")).json()

    assert rows_by_provider(asyncio.run(read()))["vancouver_traffic_cameras"] == ("tracked", 3)

    monkeypatch.setenv("ROUTELENS_DATA_DIR", str(usage_store.path.parent))
    monkeypatch.setattr(UsageStore, "today", lambda self: today)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--daily", "--operations"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exit_info.value.code == 0
    rows = {tuple(line.split()) for line in capsys.readouterr().out.splitlines()}
    assert {
        ("vancouver_traffic_cameras", "226"),
        ("vancouver_traffic_cameras.catalogue", "3"),
        ("vancouver_traffic_cameras.page", "220"),
        ("vancouver_traffic_cameras.frame", "3"),
        (yesterday.isoformat(), "223"),
        (today.isoformat(), "3"),
    } <= rows


@pytest.mark.parametrize("failure", ["missing", "corrupt"])
def test_unreadable_usage_is_not_reported_as_zero(usage_store, failure):
    if failure == "corrupt":
        usage_store.path.parent.mkdir()
        usage_store.path.write_bytes(b"corrupt")
    # ASGI transport skips lifespan so missing state remains missing during this read.
    async def read():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as client:
            return await client.get("/api/usage")

    response = asyncio.run(read())
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert rows_by_provider(response.json()) == {
        **dict.fromkeys(PROVIDERS, ("unavailable", None)),
        BROWSER_MAP_PROVIDER: ("untracked", None),
    }
    assert str(usage_store.path) not in response.text
    assert usage_store.path.exists() == (failure == "corrupt")


def test_app_records_failures_and_transport_errors_but_not_validation_or_probes(
    monkeypatch, usage_store
):
    sent = []

    def handler(request):
        sent.append(request)
        if len(sent) == 2:
            raise httpx.ConnectError("synthetic error", request=request)
        return httpx.Response(429)

    geocoder = geocoding.MapTilerGeocoder(api_key="synthetic", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(routes, "MapTilerGeocoder", lambda: geocoder)
    async def run():
        async with running_api() as client:
            assert (await client.get("/api/geocoding/search", params={"q": "a"})).status_code == 422
            for _ in range(2):
                response = await client.get("/api/geocoding/search", params={"q": "test"})
                assert response.status_code == 502
            response = await client.get("/api/usage")
            assert rows_by_provider(response.json())["maptiler"] == ("tracked", 2)

    asyncio.run(run())
    with pytest.raises(geocoding.GeocodingUpstreamError):
        asyncio.run(geocoder.search("developer probe"))
    assert len(sent) == 3
    report = usage_store.read_report(*usage_store.window(30))
    assert report.counts == {(usage_store.today(), Operation.MAPTILER_GEOCODING): 2}
    assert b"synthetic" not in usage_store.path.read_bytes()


def test_contended_write_does_not_gate_provider_and_gap_survives_recovery(
    monkeypatch, usage_store, caplog
):
    geocoder = geocoding.MapTilerGeocoder(
        api_key="synthetic",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"type": "FeatureCollection", "features": []})
        ),
    )
    monkeypatch.setattr(routes, "MapTilerGeocoder", lambda: geocoder)
    async def run():
        async with running_api() as client:
            with closing(sqlite3.connect(usage_store.path)) as blocker:
                blocker.execute("BEGIN IMMEDIATE")
                response = await client.get("/api/geocoding/search", params={"q": "test"})
                assert response.json() == []
                payload = (await client.get("/api/usage")).json()
                assert payload["status"] == "degraded"
                assert rows_by_provider(payload)["maptiler"] == ("tracked", 0)
            response = await client.get("/api/geocoding/search", params={"q": "test"})
            assert response.json() == []
            payload = (await client.get("/api/usage")).json()
            assert rows_by_provider(payload)["maptiler"] == ("tracked", 1)

    asyncio.run(run())

    assert "could not be recorded for maptiler.geocoding" in caplog.text
    assert str(usage_store.path) not in caplog.text
    assert "synthetic" not in caplog.text
    reopened = UsageStore(usage_store.path)
    assert reopened.read_report(*usage_store.window(30)).gaps == {usage_store.today()}


def test_pending_write_cannot_delay_dispatch_and_uses_date_at_dispatch(monkeypatch, usage_store):
    clock = [datetime(2026, 11, 25, 23, 59, tzinfo=timezone.utc)]
    store = UsageStore(usage_store.path, now=lambda: clock[0])
    transport_entered = Event()
    write = store.record

    def delayed_write(operation, day):
        assert transport_entered.wait(2), "provider dispatch waited for accounting"
        write(operation, day)

    def handler(_):
        clock[0] += timedelta(minutes=1)
        transport_entered.set()
        return httpx.Response(200)

    monkeypatch.setattr(store, "record", delayed_write)

    async def run():
        with observe_usage(store):
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler), event_hooks=usage_hooks(Operation.ECCC_PAGE)
            ) as client:
                assert (await client.get("https://example.invalid")).status_code == 200
        await store.flush()

    asyncio.run(run())
    assert store.read_report(*store.window(30)).counts == {
        (date(2026, 11, 25), Operation.ECCC_PAGE): 1,
    }


def test_cli_uses_configured_database_and_is_read_only(tmp_path, monkeypatch, capsys):
    directory = tmp_path / "app data #1"
    monkeypatch.setenv("ROUTELENS_DATA_DIR", str(directory))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--days", "2", "--daily", "--operations"])

    def run():
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_path(str(SCRIPT), run_name="__main__")
        return exit_info.value.code

    assert run() == 1
    assert "missing or unreadable" in capsys.readouterr().err
    assert not directory.exists()

    # Freeze the same default clock used by the executable, including its implicit window.
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz):
            return datetime(2026, 11, 26, 12, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr("app.api_usage.datetime", FrozenDateTime)
    path = directory / "api-usage.sqlite3"
    store = UsageStore(path)
    store.record(Operation.OPENROUTER_BRIEFING, date(2026, 11, 25))
    store.record(Operation.OPENROUTER_VISION, date(2026, 11, 26))
    store.record(Operation.ORS_DIRECTIONS, date(2026, 11, 24))
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    assert run() == 0
    output = capsys.readouterr().out
    assert "2026-11-25 through 2026-11-26 inclusive (UTC)" in output
    rows = {tuple(line.split()) for line in output.splitlines()}
    assert {("openrouter", "2"), ("2026-11-25", "1"), ("2026-11-26", "1"),
            ("openrouter.vision", "1"), ("openrouter.briefing", "1"),
            ("openrouteservice", "0")} <= rows
    assert ("2026-11-24", "1") not in rows
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    assert run() == 0
    assert "2026-10-28 through 2026-11-26 inclusive (UTC)" in capsys.readouterr().out
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert list(directory.iterdir()) == [path]
