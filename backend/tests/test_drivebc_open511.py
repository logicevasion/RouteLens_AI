"""Offline contract, pagination, normalization, and cache tests for DriveBC Open511."""

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

import app.drivebc_open511 as open511
from app.drivebc_open511 import DriveBCOpen511Client, normalize_event

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "open511"
NOW = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)


def observed_events() -> list[dict]:
    payload = json.loads((FIXTURES / "regional_active_observed.json").read_text(encoding="utf-8"))
    return payload["events"]


def event_record(index: int, **changes) -> dict:
    record = deepcopy(observed_events()[index % 2])
    record["id"] = f"drivebc.ca/test-{index}"
    record["url"] = f"/events/drivebc.ca/test-{index}"
    record.update(changes)
    return record


def page_payload(events, offset: int, *, next_url: str | None = None) -> dict:
    pagination = {"offset": str(offset)}
    if next_url is not None:
        pagination["next_url"] = next_url
    return {"meta": {"version": "v1", "url": "/events"}, "events": events, "pagination": pagination}


def make_client(tmp_path, handler, *, now=lambda: NOW, bbox=open511.DEFAULT_BBOX, page_size=100):
    return DriveBCOpen511Client(
        bbox=bbox,
        page_size=page_size,
        cache_dir=tmp_path,
        transport=httpx.MockTransport(handler),
        now=now,
    )


def test_observed_fixture_normalizes_point_and_line_without_losing_source_metadata():
    point, line = observed_events()
    point_event = normalize_event(point, dataset_id="dataset")
    line_event = normalize_event(line, dataset_id="dataset")

    assert point_event is not None and line_event is not None
    assert point_event.source_record_id == "drivebc.ca/OBSERVED-POINT-001"
    assert point_event.id == "dataset:drivebc.ca/OBSERVED-POINT-001"
    assert point_event.source == "DriveBC Open511"
    assert point_event.geometry == point["geography"]
    assert point_event.longitude == -122.3815195
    assert point_event.latitude == 49.05770406
    assert line_event.geometry == line["geography"]
    assert line_event.latitude is None and line_event.longitude is None
    assert line_event.severity == "MINOR"
    assert line_event.source_metadata["roads"] == line["roads"]
    assert line_event.source_metadata["schedule"] == line["schedule"]
    assert line_event.source_metadata["event_subtypes"] == ["PLANNED_EVENT"]
    assert (
        line_event.source_url == "https://api.open511.gov.bc.ca/events/drivebc.ca/OBSERVED-LINE-002"
    )
    assert point_event.observed_at == datetime(2026, 6, 25, 2, 18, 54, tzinfo=timezone.utc)


def test_unknown_or_missing_severity_and_future_schedule_are_retained():
    future = event_record(
        0,
        severity="UNRECOGNIZED_PROVIDER_VALUE",
        schedule={"intervals": ["2027-02-01T08:00/2027-02-01T16:00"]},
    )
    absent = event_record(1)
    absent.pop("severity")
    first = normalize_event(future, dataset_id="dataset")
    second = normalize_event(absent, dataset_id="dataset")

    assert first is not None and first.status == "ACTIVE"
    assert first.severity == "UNRECOGNIZED_PROVIDER_VALUE"
    assert first.source_metadata["schedule"]["intervals"][0].startswith("2027-")
    assert second is not None and second.severity is None


def test_unfamiliar_event_types_are_not_filtered_and_non_active_records_are_excluded():
    records = [
        event_record(0, event_type="SPECIAL_EVENT"),
        event_record(1, event_type="WEATHER_CONDITION"),
        event_record(2, status="ARCHIVED"),
    ]
    normalized = [normalize_event(record, dataset_id="dataset") for record in records]
    assert [event.event_type for event in normalized if event is not None] == [
        "SPECIAL_EVENT",
        "WEATHER_CONDITION",
    ]


def test_unzoned_timestamps_are_not_assumed_utc():
    record = event_record(0, created="2026-06-24T19:18:54", updated="not-a-date")
    event = normalize_event(record, dataset_id="dataset")

    assert event is not None
    assert event.observed_at is None
    assert event.updated_at is None
    assert event.source_metadata["created"] == "2026-06-24T19:18:54"


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [-123.1, 49.2]},
        {"type": "LineString", "coordinates": [[-123.1, 49.2], [-123.0, 49.3]]},
        None,
    ],
)
def test_supported_and_missing_geometries_are_preserved(geometry):
    event = normalize_event(event_record(0, geography=geometry), dataset_id="dataset")
    assert event is not None and event.geometry == geometry


@pytest.mark.parametrize(
    "geometry",
    [
        "bad",
        {"type": "Point", "coordinates": [-123.1, float("nan")]},
        {"type": "Point", "coordinates": [-123.1, 91]},
        {"type": "LineString", "coordinates": [[-123.1, 49.2]]},
        {"type": "Polygon", "coordinates": []},
    ],
)
def test_invalid_or_unobserved_geometry_isolated_from_record(geometry):
    assert normalize_event(event_record(0, geography=geometry), dataset_id="dataset") is None


def test_source_url_is_restricted_to_official_https_event_links():
    for candidate in [
        "http://api.open511.gov.bc.ca/events/a",
        "https://evil.invalid/events/a",
        "https://api.open511.gov.bc.ca/jurisdiction",
    ]:
        event = normalize_event(event_record(0, url=candidate), dataset_id="dataset")
        assert event is not None and event.source_url is None


def test_single_page_retrieval_uses_active_bbox_all_types_and_all_severities(tmp_path):
    requests = []

    def handler(request):
        requests.append(dict(request.url.params))
        return httpx.Response(200, json=page_payload(observed_events(), 0))

    result = asyncio.run(make_client(tmp_path, handler).get_data())
    assert len(result.events) == 2
    assert result.source_status.success and result.source_status.refreshed
    assert result.source_status.records_received == 2
    assert requests == [
        {
            "format": "json",
            "status": "ACTIVE",
            "bbox": open511.DEFAULT_BBOX,
            "limit": "100",
            "offset": "0",
        }
    ]


def test_redirect_is_not_followed_or_cached(tmp_path):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(
            302,
            headers={"Location": "https://redirect.example/forwarded"},
        )

    client = make_client(tmp_path, handler)
    result = asyncio.run(client.get_data())

    assert len(requests) == 1
    assert requests[0].startswith(open511.EVENTS_URL)
    assert result.events == []
    assert not result.source_status.success
    assert not result.source_status.available
    assert not result.source_status.refreshed
    assert not client.cache_path.exists()


def test_documented_next_url_pagination_retrieves_every_page(tmp_path):
    records = [event_record(index) for index in range(5)]
    requests = []

    def handler(request):
        params = dict(request.url.params)
        requests.append(int(params["offset"]))
        offset = int(params["offset"])
        page = records[offset : offset + 2]
        link = None
        if offset + len(page) < len(records):
            link = f"/events?format=json&status=ACTIVE&bbox={open511.DEFAULT_BBOX}&limit=2&offset={offset + len(page)}"
        return httpx.Response(200, json=page_payload(page, offset, next_url=link))

    result = asyncio.run(make_client(tmp_path, handler, page_size=2).get_data())
    assert requests == [0, 2, 4]
    assert result.source_status.records_received == 5
    assert len(result.events) == 5


def test_exact_full_final_page_is_confirmed_by_empty_offset_probe(tmp_path):
    records = [event_record(0), event_record(1)]
    offsets = []

    def handler(request):
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        return httpx.Response(200, json=page_payload(records[offset : offset + 2], offset))

    result = asyncio.run(make_client(tmp_path, handler, page_size=2).get_data())
    assert offsets == [0, 2]
    assert len(result.events) == 2


@pytest.mark.parametrize(
    "pointer",
    [
        "https://evil.invalid/events?status=ACTIVE&bbox=-123.45,48.99,-122.45,49.49&limit=1&offset=1",
        "/events?status=ACTIVE&bbox=-123.45,48.99,-122.45,49.49&limit=1&offset=9",
        "/events?status=ACTIVE&bbox=-123.45,48.99,-122.45,49.49&limit=1",
        "not a URL",
    ],
)
def test_malformed_or_inconsistent_next_pointer_is_rejected(tmp_path, pointer):
    def handler(request):
        return httpx.Response(200, json=page_payload([event_record(0)], 0, next_url=pointer))

    result = asyncio.run(make_client(tmp_path, handler, page_size=1).get_data())
    assert not result.source_status.available
    assert result.source_status.records_received == 0


def test_offset_mismatch_duplicate_ids_and_invalid_envelope_fail_closed(tmp_path):
    def wrong_offset(request):
        return httpx.Response(200, json=page_payload([event_record(0)], 1))

    result = asyncio.run(make_client(tmp_path, wrong_offset, page_size=1).get_data())
    assert not result.source_status.available

    records = [event_record(0), event_record(1)]

    def duplicate(request):
        offset = int(request.url.params["offset"])
        if offset == 0:
            pointer = f"/events?status=ACTIVE&bbox={open511.DEFAULT_BBOX}&limit=1&offset=1"
            return httpx.Response(200, json=page_payload([records[0]], 0, next_url=pointer))
        return httpx.Response(200, json=page_payload([records[0]], 1))

    result = asyncio.run(make_client(tmp_path, duplicate, page_size=1).get_data())
    assert not result.source_status.available


def test_repeated_next_page_link_is_rejected(tmp_path):
    pointer = f"/events?format=json&status=ACTIVE&bbox={open511.DEFAULT_BBOX}&limit=1&offset=1"

    def handler(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(
            200,
            json=page_payload([event_record(offset)], offset, next_url=pointer),
        )

    result = asyncio.run(make_client(tmp_path, handler, page_size=1).get_data())
    assert not result.source_status.available


def test_declared_content_length_mismatch_is_treated_as_truncation(tmp_path):
    body = json.dumps(page_payload([event_record(0)], 0)).encode()

    def handler(_):
        return httpx.Response(200, content=body, headers={"content-length": str(len(body) + 1)})

    result = asyncio.run(make_client(tmp_path, handler).get_data())
    assert not result.source_status.available


def test_page_count_limit_rejects_a_never_ending_feed(tmp_path, monkeypatch):
    monkeypatch.setattr(open511, "MAX_PAGES", 1)

    def handler(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json=page_payload([event_record(offset)], offset))

    result = asyncio.run(make_client(tmp_path, handler, page_size=1).get_data())
    assert not result.source_status.available
    assert "safety limit" in (result.source_status.error or "")


def test_refresh_runtime_limit_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(open511, "MAX_REFRESH_SECONDS", 0.001)

    async def slow_handler(_):
        await asyncio.sleep(0.02)
        return httpx.Response(200, json=page_payload([event_record(0)], 0))

    transport = httpx.MockTransport(slow_handler)
    client = DriveBCOpen511Client(cache_dir=tmp_path, transport=transport, now=lambda: NOW)
    result = asyncio.run(client.get_data())
    assert not result.source_status.available
    assert "time limit" in (result.source_status.error or "")


def test_valid_empty_dataset_is_available_and_cached(tmp_path):
    calls = 0

    def handler(_):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=page_payload([], 0))

    client = make_client(tmp_path, handler)
    first = asyncio.run(client.get_data())
    second = asyncio.run(client.get_data())
    assert first.source_status.available and first.events == []
    assert second.source_status.cache_hit and second.source_status.available
    assert calls == 1


def test_large_or_systemic_record_loss_rejected_but_one_bad_record_isolated(tmp_path):
    records = [event_record(0), {"id": "bad", "status": "ACTIVE"}]

    def handler(_):
        return httpx.Response(200, json=page_payload(records, 0))

    result = asyncio.run(make_client(tmp_path, handler).get_data())
    assert result.source_status.available
    assert result.source_status.records_normalized == 1
    assert result.source_status.records_skipped == 1

    bad_records = [{"id": f"bad-{index}"} for index in range(10)]

    def systemic(_):
        return httpx.Response(200, json=page_payload(bad_records, 0))

    result = asyncio.run(make_client(tmp_path / "systemic", systemic).get_data())
    assert not result.source_status.available


def test_fresh_cache_reuse_and_query_identity_isolation(tmp_path):
    calls = 0

    def handler(_):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=page_payload([event_record(0)], 0))

    client = make_client(tmp_path, handler)
    first = asyncio.run(client.get_data())
    second = asyncio.run(client.get_data())
    changed_scope = make_client(tmp_path, handler, bbox="-123.5,48.9,-122.4,49.5")
    third = asyncio.run(changed_scope.get_data())
    assert first.source_status.refreshed
    assert second.source_status.cache_hit
    assert third.source_status.refreshed
    assert first.source_status.dataset_id != third.source_status.dataset_id
    assert calls == 2


def test_stale_cache_fallback_on_timeout_and_malformed_refresh(tmp_path):
    client = make_client(
        tmp_path, lambda _: httpx.Response(200, json=page_payload([event_record(0)], 0))
    )
    client._write_cache(NOW - timedelta(seconds=700), [event_record(0)], 1)
    previous_cache = client.cache_path.read_text(encoding="utf-8")

    def timeout(_):
        raise httpx.ReadTimeout("https://private.invalid/?token=secret")

    stale = asyncio.run(make_client(tmp_path, timeout).get_data())
    assert stale.source_status.stale and stale.source_status.available
    assert not stale.source_status.success
    assert stale.source_status.records_received == 1
    assert "secret" not in (stale.source_status.error or "")

    def malformed(_):
        return httpx.Response(
            200, json={"events": [], "meta": {"version": "v1"}, "pagination": {"offset": "2"}}
        )

    stale_again = asyncio.run(make_client(tmp_path, malformed).get_data())
    assert stale_again.source_status.stale and len(stale_again.events) == 1
    assert client.cache_path.read_text(encoding="utf-8") == previous_cache


def test_corrupt_cache_is_not_success_or_stale_fallback(tmp_path):
    client = make_client(tmp_path, lambda _: httpx.Response(503))
    client.cache_path.parent.mkdir(parents=True, exist_ok=True)
    client.cache_path.write_text("{broken", encoding="utf-8")
    result = asyncio.run(client.get_data())
    assert not result.source_status.available
    assert not result.events


@pytest.mark.parametrize(
    "cache_changes",
    [
        {"complete": False},
        {"records_received": 2},
        {"cache_schema_version": True},
        {"page_count": open511.MAX_PAGES + 1},
    ],
)
def test_incomplete_or_malformed_cache_envelope_is_rejected(tmp_path, cache_changes):
    client = make_client(tmp_path, lambda _: httpx.Response(503))
    client._write_cache(NOW, [event_record(0)], 1)
    payload = json.loads(client.cache_path.read_text(encoding="utf-8"))
    payload.update(cache_changes)
    client.cache_path.write_text(json.dumps(payload), encoding="utf-8")
    result = asyncio.run(client.get_data())
    assert not result.source_status.available
    assert not result.events


def test_atomic_cache_write_failure_preserves_previous_valid_snapshot(tmp_path, monkeypatch):
    old = event_record(0)
    client = make_client(
        tmp_path, lambda _: httpx.Response(200, json=page_payload([event_record(1)], 0))
    )
    client._write_cache(NOW - timedelta(seconds=700), [old], 1)
    before = client.cache_path.read_text(encoding="utf-8")

    def fail_replace(*_):
        raise OSError("private cache filesystem path")

    monkeypatch.setattr(open511.os, "replace", fail_replace)
    result = asyncio.run(client.get_data())
    assert result.source_status.stale and result.events[0].source_record_id == old["id"]
    assert client.cache_path.read_text(encoding="utf-8") == before
    assert not [path for path in client.cache_dir.iterdir() if path.name.endswith(".tmp")]


def test_concurrent_calls_share_one_refresh(tmp_path):
    calls = 0

    def handler(_):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=page_payload([event_record(0)], 0))

    async def run():
        client = make_client(tmp_path, handler)
        return await asyncio.gather(client.get_data(), client.get_data())

    first, second = asyncio.run(run())
    assert calls == 1
    assert first.source_status.refreshed
    assert second.source_status.cache_hit


def test_bbox_and_page_size_configuration_is_validated_and_canonicalized(tmp_path):
    left = DriveBCOpen511Client(cache_dir=tmp_path, bbox="-123.450, 48.990, -122.450, 49.490")
    right = DriveBCOpen511Client(cache_dir=tmp_path, bbox=open511.DEFAULT_BBOX)
    assert left.query_identity == right.query_identity
    with pytest.raises(ValueError):
        DriveBCOpen511Client(cache_dir=tmp_path, bbox="-123,49,-124,50")
    with pytest.raises(ValueError):
        DriveBCOpen511Client(cache_dir=tmp_path, page_size=501)


def test_response_count_and_offset_are_not_inferred_from_event_records():
    client = DriveBCOpen511Client()
    with pytest.raises(open511._InvalidPayload):
        client._validate_page(
            {"events": [], "meta": {"version": "v1"}, "pagination": {"offset": "many"}},
            expected_offset=0,
        )
