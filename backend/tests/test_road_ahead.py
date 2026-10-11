"""Offline tests for Road Ahead source validation, normalization, and caching."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.road_ahead import (
    CACHE_TTL_SECONDS,
    DATASETS,
    PAGE_SIZE,
    RoadAheadClient,
    RoadAheadError,
    _normalize_record,
    _write_cache,
    validate_page,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "road_ahead"
NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def response_for(spec, *, records=None, total=None):
    items = fixture("current_road_closures.json")["results"] if records is None else records
    return {"total_count": len(items) if total is None else total, "results": items}


def client_for(tmp_path, handler, *, now=lambda: NOW):
    return RoadAheadClient(
        cache_dir=tmp_path,
        transport=httpx.MockTransport(handler),
        now=now,
    )


def test_current_closure_preserves_complete_mixed_geometry_and_provenance() -> None:
    record = fixture("current_road_closures.json")["results"][0]
    event = _normalize_record(DATASETS[0], record)

    assert event is not None
    assert event.id == "road-ahead-current-road-closures:closure-row-001"
    assert event.source_record_id == "closure-row-001"
    assert event.source_url == record["url_link"]
    assert event.geometry == record["geom"]["geometry"]
    assert event.latitude == 49.2505
    assert event.longitude == -123.1005
    assert event.source_metadata["comp_date"] == "2027-03-15"
    assert event.status is None
    assert event.schedule_text is None


def test_construction_keeps_unknown_optional_values_unknown() -> None:
    record = fixture("projects_under_construction.json")["results"][0]
    event = _normalize_record(DATASETS[1], record)

    assert event is not None
    assert event.source_dataset_id == "road-ahead-projects-under-construction"
    assert event.id == "road-ahead-projects-under-construction:construction-row-002"
    assert event.title == "Cambie Street near West 10th Avenue"
    assert event.source_url is not None
    assert event.geometry["type"] == "MultiLineString"
    assert len(event.geometry["coordinates"][0]) == 3
    assert event.status is None and event.schedule_text is None


@pytest.mark.parametrize("geometry", [None, "bad", {"type": "LineString", "coordinates": [[-123, 49]]}])
def test_null_geometry_is_safe_and_malformed_geometry_skips_record(geometry) -> None:
    record = fixture("projects_under_construction.json")["results"][0]
    record["geom"] = geometry
    event = _normalize_record(DATASETS[1], record)
    if geometry is None:
        assert event is not None and event.geometry is None
    else:
        assert event is None


def test_missing_street_and_detail_link_do_not_discard_usable_record() -> None:
    record = fixture("projects_under_construction.json")["results"][0]
    record.pop("street", None)
    record.pop("url_link", None)
    event = _normalize_record(DATASETS[1], record)
    assert event is not None
    assert event.source_record_id == "construction-row-002"
    assert event.title == record["location"]
    assert event.source_url is None


def test_official_detail_link_provides_source_identity_fallback() -> None:
    record = fixture("current_road_closures.json")["results"][0]
    record.pop("recordid")
    event = _normalize_record(DATASETS[0], record)
    assert event is not None
    assert event.source_record_id == "14a078dc-e00d-4cd5-b930-770b52c1513d"


def test_valid_empty_collection_is_accepted() -> None:
    assert validate_page({"total_count": 0, "results": []}, expected_offset=0, requested_limit=PAGE_SIZE) == (
        0,
        [],
    )


def test_valid_empty_datasets_are_available_and_cached(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": 0, "results": []})

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert len(result.source_statuses) == 2
    assert all(status.available and status.success and status.records_received == 0 for status in result.source_statuses)
    assert result.events == []


def test_linestring_and_mixed_geometry_collection_are_supported() -> None:
    record = fixture("current_road_closures.json")["results"][0]
    record["geom"] = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[-123, 49], [-123.1, 49.1]]}}
    event = _normalize_record(DATASETS[0], record)
    assert event is not None and event.geometry["type"] == "LineString"
    assert len(event.geometry["coordinates"]) == 2


def test_geometry_collection_preserves_polygon_components_and_rejects_bad_ring() -> None:
    record = fixture("current_road_closures.json")["results"][0]
    event = _normalize_record(DATASETS[0], record)
    assert event is not None
    assert event.geometry["geometries"][-1]["type"] == "Polygon"
    bad = dict(record, geom={"type": "GeometryCollection", "geometries": [
        {"type": "Polygon", "coordinates": [[[-123, 49], [-123.1, 49.1], [-123, 49]]]},
    ]})
    assert _normalize_record(DATASETS[0], bad) is None

def test_geometry_collection_rejects_null_component() -> None:
    record = fixture("current_road_closures.json")["results"][0]
    record["geom"]["geometry"]["geometries"].append(None)

    assert _normalize_record(DATASETS[0], record) is None


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"total_count": "1", "results": []}, {"total_count": 1, "results": "bad"}],
)
def test_malformed_collection_envelope_is_rejected(payload) -> None:
    with pytest.raises(RoadAheadError):
        validate_page(payload, expected_offset=0, requested_limit=PAGE_SIZE)


def test_paginated_download_retrieves_every_page_and_validates_total(tmp_path) -> None:
    records = [
        {"recordid": f"row-{index}", "geom": None, "project": f"Project {index}"}
        for index in range(PAGE_SIZE + 1)
    ]
    requests = []
    selected_fields = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        requests.append(offset)
        selected_fields.append(request.url.params["select"])
        return httpx.Response(
            200,
            json={"total_count": len(records), "results": records[offset : offset + limit]},
        )

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert requests == [0, PAGE_SIZE, 0, PAGE_SIZE]
    assert set(selected_fields) == {"*,recordid"}
    assert all(status.success for status in result.source_statuses)
    assert len(result.events) == 2 * (PAGE_SIZE + 1)


def test_truncated_page_does_not_replace_cache_and_uses_stale_data(tmp_path) -> None:
    old_records = fixture("current_road_closures.json")["results"]
    stale_at = NOW - timedelta(seconds=CACHE_TTL_SECONDS + 10)
    path = tmp_path / "closures.json"
    _write_cache(path, stale_at, old_records, 1)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": 2, "results": [old_records[0]]})

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    status = result.source_statuses[0]
    assert status.stale and status.available and not status.success
    assert status.records_normalized == 1
    assert json.loads(path.read_text())["retrieved_at"] == stale_at.isoformat()


def test_cache_miss_fetches_and_fresh_cache_avoids_network(tmp_path) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=response_for(DATASETS[0]))

    client = client_for(tmp_path, handler)
    first = asyncio.run(client.get_data())
    assert first.source_statuses[0].success and not first.source_statuses[0].cache_hit
    assert calls == 2
    second = asyncio.run(client.get_data())
    assert second.source_statuses[0].cache_hit
    assert calls == 2


def test_stale_cache_is_replaced_only_after_valid_refresh(tmp_path) -> None:
    old = fixture("current_road_closures.json")["results"]
    path = tmp_path / "closures.json"
    _write_cache(path, NOW - timedelta(seconds=CACHE_TTL_SECONDS + 60), old, 1)
    refreshed_record = dict(old[0], recordid="closure-row-refreshed", project="Updated project")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": 1, "results": [refreshed_record]})

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    status = result.source_statuses[0]
    assert status.success and status.refreshed and not status.stale
    assert result.events[0].source_record_id == "closure-row-refreshed"
    assert json.loads(path.read_text())["payload"]["records"][0]["recordid"] == "closure-row-refreshed"


def test_corrupted_cache_is_replaced_by_valid_live_data(tmp_path) -> None:
    path = tmp_path / "closures.json"
    path.write_text("{broken", encoding="utf-8")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_for(DATASETS[0]))

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert result.source_statuses[0].refreshed
    assert result.source_statuses[0].available
    assert json.loads(path.read_text())["payload"]["total_count"] == 1


def test_isolated_malformed_record_is_counted_and_good_record_retained(tmp_path) -> None:
    good = fixture("current_road_closures.json")["results"][0]
    records = [good, {"recordid": "bad", "geom": {"type": "Point", "coordinates": [-123, 49]}}]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": 2, "results": records})

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    status = result.source_statuses[0]
    assert status.available and status.records_normalized == 1 and status.records_skipped == 1
    assert len([event for event in result.events if event.source_dataset_id == DATASETS[0].dataset_id]) == 1


def test_refresh_failure_with_no_cache_is_unavailable_and_sources_are_independent(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "current-road-closures" in request.url.path:
            return httpx.Response(503)
        return httpx.Response(200, json=response_for(DATASETS[1], records=fixture("projects_under_construction.json")["results"]))

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert not result.source_statuses[0].available
    assert result.source_statuses[1].available
    assert len(result.events) == 1


def test_timeout_is_reported_without_leaking_transport_details(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("https://private.invalid/path?token=secret")

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert all(not status.available for status in result.source_statuses)
    assert all("secret" not in (status.error or "") for status in result.source_statuses)


def test_corrupted_cache_is_not_treated_as_empty_success(tmp_path) -> None:
    (tmp_path / "closures.json").write_text("{broken", encoding="utf-8")

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert not result.source_statuses[0].available
    assert result.events == []


def test_significant_record_loss_rejects_dataset(tmp_path) -> None:
    records = [{"recordid": str(index), "geom": {"type": "Point", "coordinates": [-123, 49]}} for index in range(20)]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": len(records), "results": records})

    result = asyncio.run(client_for(tmp_path, handler).get_data())
    assert not result.source_statuses[0].available


def test_concurrent_calls_share_refresh_per_dataset(tmp_path) -> None:
    calls = 0

    async def run() -> None:
        nonlocal calls

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json=response_for(DATASETS[0]))

        client = RoadAheadClient(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW)
        first, second = await asyncio.gather(client.get_data(), client.get_data())
        assert first.source_statuses[0].success and second.source_statuses[0].cache_hit

    asyncio.run(run())
    assert calls == 2


def test_cache_replacement_is_atomic_and_cleans_temporary_file(tmp_path, monkeypatch) -> None:
    path = tmp_path / "closures.json"
    path.write_text('{"old":true}', encoding="utf-8")
    original_replace = __import__("os").replace
    observed = []

    def checked_replace(source, destination):
        assert json.loads(Path(source).read_text(encoding="utf-8"))["payload"]["total_count"] == 0
        assert json.loads(path.read_text(encoding="utf-8")) == {"old": True}
        observed.append(True)
        original_replace(source, destination)

    monkeypatch.setattr("app.road_ahead.os.replace", checked_replace)
    _write_cache(path, NOW, [], 0)
    assert observed == [True]
    assert json.loads(path.read_text(encoding="utf-8"))["payload"]["records"] == []
    assert list(tmp_path.glob("*.tmp")) == []
