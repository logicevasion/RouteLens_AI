"""Offline contract, grouping, selection, paging, and cache tests for ECCC SWOB."""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

import app.eccc_swob as swob
from app.eccc_swob import (
    EcccSwobClient,
    parse_feature_collection,
    select_destination_observations,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "eccc_swob" / "swob_realtime_vancouver_observed.json"
OBSERVED_PAYLOAD = json.loads(FIXTURE.read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 11, 13, 30, tzinfo=timezone.utc)


def feature(
    station: str = "station-1",
    *,
    observed_at: str = "2026-10-11T13:20:00Z",
    source_id: str = "record-1",
    lon: float | None = -123.12,
    lat: float | None = 49.28,
    properties: dict | None = None,
) -> dict:
    values = {
        "date_tm-value": observed_at,
        "msc_id-value": station,
        "stn_nam-value": f"Station {station}",
        "air_temp": 8.0,
        "air_temp-uom": "°C",
        "air_temp-qa": 100,
        "rel_hum": 80,
        "rel_hum-uom": "%",
        "rel_hum-qa": 100,
        "pcpn_amt_pst10mts": 0,
        "pcpn_amt_pst10mts-uom": "mm",
        "pcpn_amt_pst10mts-qa": 100,
        "pcpn_amt_pst1hr": 0.4,
        "pcpn_amt_pst1hr-uom": "mm",
        "pcpn_amt_pst1hr-qa": 100,
        "avg_wnd_spd_10m_pst10mts": 4.0,
        "avg_wnd_spd_10m_pst10mts-uom": "km/h",
        "avg_wnd_spd_10m_pst10mts-qa": 100,
        "avg_wnd_dir_10m_pst10mts": 180,
        "avg_wnd_dir_10m_pst10mts-uom": "°",
        "avg_wnd_dir_10m_pst10mts-qa": 100,
        "snw_dpth": 0,
        "snw_dpth-uom": "cm",
        "snw_dpth-qa": 100,
    }
    values.update(properties or {})
    geometry = None if lon is None or lat is None else {"type": "Point", "coordinates": [lon, lat]}
    return {"type": "Feature", "id": source_id, "geometry": geometry, "properties": values}


def collection(features: list[dict], *, matched: int | None = None) -> dict:
    return {
        "type": "FeatureCollection",
        "numberMatched": len(features) if matched is None else matched,
        "numberReturned": len(features),
        "features": features,
    }


def client(tmp_path, handler, *, now=lambda: NOW, ttl=600):
    return EcccSwobClient(
        cache_dir=tmp_path,
        ttl_seconds=ttl,
        transport=httpx.MockTransport(handler),
        now=now,
    )


def test_observed_live_fixture_parses_actual_geojson_fields_and_multiple_station_records():
    observations, diagnostics, matched = parse_feature_collection(OBSERVED_PAYLOAD, NOW)
    assert matched == 20
    assert diagnostics.records_received == 20
    assert diagnostics.station_count == 2
    assert {item.station_id for item in observations} == {"1106200", "1108824"}
    point_atkinson = next(item for item in observations if item.station_id == "1106200")
    assert point_atkinson.station_name == "POINT ATKINSON"
    assert point_atkinson.latitude == pytest.approx(49.330352)
    assert point_atkinson.longitude == pytest.approx(-123.264704)
    assert point_atkinson.temperature.value == 10.2
    assert point_atkinson.temperature.source_field == "air_temp"
    assert point_atkinson.temperature.unit == "°C"
    assert point_atkinson.precipitation[0].value == 0
    assert point_atkinson.precipitation[0].interval_seconds == 600
    assert point_atkinson.precipitation[1].value == 0
    assert point_atkinson.precipitation[1].unit == "mm"
    assert point_atkinson.precipitation[1].interval_seconds == 3600
    assert point_atkinson.wind_speed.unit == "km/h"
    assert point_atkinson.wind_direction.unit == "°"
    assert all(item.attribution == swob.ATTRIBUTION for item in observations)


def test_nonzero_precipitation_preserves_measured_amount_unit_and_interval():
    observations, _, _ = parse_feature_collection(
        collection([feature(properties={"pcpn_amt_pst1hr": 2.5})]), NOW
    )
    amount = observations[0].precipitation[1]
    assert amount.value == 2.5
    assert amount.unit == "mm"
    assert amount.interval_seconds == 3600
    assert amount.source_field == "pcpn_amt_pst1hr"


def test_latest_per_station_and_duplicate_timestamp_tie_are_deterministic():
    features = [
        feature("s-1", observed_at="2026-10-11T13:00:00Z", source_id="older"),
        feature("s-1", observed_at="2026-10-11T13:10:00Z", source_id="tie-a"),
        feature("s-1", observed_at="2026-10-11T13:10:00Z", source_id="tie-z", properties={"air_temp": 9.0}),
        feature("s-2", source_id="other"),
    ]
    first, diagnostics, _ = parse_feature_collection(collection(features), NOW)
    second, _, _ = parse_feature_collection(collection(list(reversed(features))), NOW)
    selected = next(item for item in first if item.station_id == "s-1")
    reversed_selected = next(item for item in second if item.station_id == "s-1")
    assert selected.source_record_id == "tie-z"
    assert selected.temperature.value == 9.0
    assert reversed_selected.source_record_id == selected.source_record_id
    assert diagnostics.duplicate_timestamps == 1


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"date_tm-value": "not-a-time"}, "invalid_timestamp"),
        ({"msc_id-value": None, "clim_id-value": None, "wmo_synop_id-value": None, "tc_id-value": None}, "missing_station_identity"),
    ],
)
def test_invalid_timestamp_and_missing_station_identity_are_skipped(changes, reason):
    observations, diagnostics, _ = parse_feature_collection(
        collection([feature(properties=changes), feature("valid", source_id="valid")]), NOW
    )
    assert len(observations) == 1
    assert diagnostics.skipped_reasons[reason] == 1


def test_malformed_coordinates_keep_station_but_exclude_it_from_distance_selection():
    bad_latitude = feature("bad", lon=-123.1, lat=91)
    no_location = feature("no-location", lon=None, lat=None)
    observations, diagnostics, _ = parse_feature_collection(collection([bad_latitude, no_location]), NOW)
    assert diagnostics.station_count == 2
    assert all(item.latitude is None and item.longitude is None for item in observations)
    assert select_destination_observations(observations, latitude=49.28, longitude=-123.12, now=NOW) == []


def test_missing_fields_unknown_units_bad_quality_and_sentinels_remain_unknown():
    record = feature(
        properties={
            "air_temp": None,
            "rel_hum": None,
            "pcpn_amt_pst10mts": None,
            "pcpn_amt_pst1hr": None,
            "avg_wnd_spd_10m_pst10mts": None,
            "avg_wnd_dir_10m_pst10mts": None,
            "snw_dpth": -1,
            "snw_dpth-qa": -10,
            "visibility": 2,
            "visib": 2,
        }
    )
    observations, _, _ = parse_feature_collection(collection([record]), NOW)
    reading = observations[0]
    assert reading.temperature is None
    assert reading.relative_humidity is None
    assert reading.precipitation == []
    assert reading.wind_speed is None and reading.wind_direction is None
    assert reading.snow_depth is None
    assert not hasattr(reading, "visibility")

    unknown_unit = feature(properties={"air_temp-uom": "F"})
    normalized, _, _ = parse_feature_collection(collection([unknown_unit]), NOW)
    assert normalized[0].temperature is None


def test_invalid_station_id_and_timestamp_schema_never_becomes_an_empty_success():
    with pytest.raises(swob._ExpectedFailure, match="widespread_record_loss"):
        parse_feature_collection(collection([feature(properties={"msc_id-value": None})]), NOW)
    with pytest.raises(swob._ExpectedFailure, match="incomplete_page"):
        parse_feature_collection(collection([feature()], matched=2), NOW)


def test_future_skew_stale_readings_and_invalid_destination_are_handled():
    observations, _, _ = parse_feature_collection(
        collection(
            [
                feature("future", observed_at="2026-10-11T13:36:00Z"),
                feature("stale", observed_at="2026-10-11T10:00:00Z"),
                feature("fresh", observed_at="2026-10-11T13:20:00Z"),
            ]
        ),
        NOW,
    )
    selected = select_destination_observations(observations, latitude=49.28, longitude=-123.12, now=NOW)
    assert [item.observation.station_id for item in selected] == ["fresh", "stale"]
    assert selected[0].observation_stale is False
    assert selected[1].observation_stale is True
    with pytest.raises(ValueError, match="destination"):
        select_destination_observations(observations, latitude=91, longitude=-123.12, now=NOW)


def test_destination_selection_prefers_freshness_then_proximity_and_complements_evidence():
    observations, _, _ = parse_feature_collection(
        collection(
            [
                feature("close-old", observed_at="2026-10-11T12:00:00Z", lon=-123.1201, lat=49.28),
                feature("far-fresh", observed_at="2026-10-11T13:25:00Z", lon=-123.2, lat=49.28),
                feature(
                    "precip-only",
                    observed_at="2026-10-11T13:24:00Z",
                    lon=-123.13,
                    lat=49.28,
                    properties={"air_temp": None, "rel_hum": None, "avg_wnd_spd_10m_pst10mts": None, "avg_wnd_dir_10m_pst10mts": None, "snw_dpth": None},
                ),
                feature("closest-no-temp", observed_at="2026-10-11T13:23:00Z", lon=-123.12001, lat=49.28, properties={"air_temp": None}),
            ]
        ),
        NOW,
    )
    selected = select_destination_observations(observations, latitude=49.28, longitude=-123.12, now=NOW)
    assert selected[0].observation.station_id == "far-fresh"
    assert selected[1].observation.station_id == "precip-only"
    assert selected[1].useful_measurements == ["precipitation_accumulation"]
    assert all(item.distance_meters >= 0 for item in selected)
    assert all(item.distance_meters < 20_000 for item in selected)
    assert all("temperature" in item.selection_reason for item in selected[:1])


def test_destination_selection_can_prioritize_a_requested_measurement():
    observations, _, _ = parse_feature_collection(
        collection(
            [
                feature("nearest-no-temperature", observed_at="2026-10-11T13:29:00Z", lon=-123.12, properties={"air_temp": None}),
                feature(
                    "farther-temperature",
                    observed_at="2026-10-11T13:25:00Z",
                    lon=-123.2,
                    properties={
                        "rel_hum": None,
                        "pcpn_amt_pst10mts": None,
                        "pcpn_amt_pst1hr": None,
                        "avg_wnd_spd_10m_pst10mts": None,
                        "avg_wnd_dir_10m_pst10mts": None,
                        "snw_dpth": None,
                    },
                ),
            ]
        ),
        NOW,
    )
    selected = select_destination_observations(
        observations,
        latitude=49.28,
        longitude=-123.12,
        now=NOW,
        preferred_measurements=["temperature"],
        limit=1,
    )
    assert selected[0].observation.station_id == "farther-temperature"
    assert selected[0].useful_measurements == ["temperature"]


def test_destination_selection_is_station_id_tie_broken_and_bounded():
    observations, _, _ = parse_feature_collection(
        collection([feature("z"), feature("b"), feature("a"), feature("c")]), NOW
    )
    selected = select_destination_observations(
        observations, latitude=49.28, longitude=-123.12, now=NOW, limit=2
    )
    assert [item.observation.station_id for item in selected] == ["a", "b"]
    assert all(item.distance_meters == 0 for item in selected)
    with pytest.raises(ValueError, match="limit"):
        select_destination_observations(observations, latitude=49.28, longitude=-123.12, limit=4)


def test_destination_distance_is_reported_in_metres():
    observations, _, _ = parse_feature_collection(
        collection([feature("offset", lon=-123.119, lat=49.28)]), NOW
    )
    selected = select_destination_observations(
        observations, latitude=49.28, longitude=-123.12, now=NOW
    )
    assert selected[0].distance_meters == pytest.approx(73, abs=2)


def page_response(features: list[dict], matched: int, offset: int) -> httpx.Response:
    selected = features[offset : offset + swob.PAGE_SIZE]
    return httpx.Response(200, json=collection(selected, matched=matched))


def test_pagination_completes_snapshot_and_uses_bounded_fixed_query(tmp_path, monkeypatch):
    all_features = [feature(f"s-{index}", source_id=f"id-{index}") for index in range(swob.PAGE_SIZE + 2)]
    requests = []

    def handler(request):
        requests.append(request)
        return page_response(all_features, len(all_features), int(request.url.params["offset"]))

    monkeypatch.setattr(swob, "MAX_RECORDS", 2000)
    result = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    assert result.status.success and result.status.available and result.status.refreshed
    assert result.status.records_received == swob.PAGE_SIZE + 2
    assert result.diagnostics.station_count == swob.PAGE_SIZE + 2
    assert [request.url.params["offset"] for request in requests] == ["0", "500"]
    assert requests[0].url.scheme == "https" and requests[0].url.host == "api.weather.gc.ca"
    assert requests[0].url.params["bbox"] == swob.DEFAULT_BBOX
    assert requests[0].url.params["datetime"].endswith("Z/2026-10-11T13:30:00Z")
    assert requests[0].url.params["sortby"] == "date_tm-value"
    assert requests[0].url.params["limit"] == "500"


def test_valid_empty_feed_is_available_and_cached(tmp_path):
    calls = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(200, json=collection([]))

    first = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    second = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    assert first.status.available and first.observations == []
    assert second.status.cache_hit and second.status.available
    assert len(calls) == 1


def test_fresh_cache_reuse_stale_refresh_and_stale_fallback(tmp_path):
    state = {"now": NOW, "fail": False, "calls": 0}

    def handler(_request):
        state["calls"] += 1
        if state["fail"]:
            raise httpx.ReadTimeout("private host details")
        return httpx.Response(200, json=collection([feature()]))

    def current_time():
        return state["now"]

    async def scenario():
        live = client(tmp_path, handler, now=current_time)
        first = await live.fetch_regional_observations()
        second = await live.fetch_regional_observations()
        state["now"] += timedelta(seconds=601)
        state["fail"] = True
        third = await live.fetch_regional_observations()
        return first, second, third

    first, second, third = asyncio.run(scenario())
    assert first.status.refreshed and first.status.success
    assert second.status.cache_hit and second.status.cache_age_seconds == 0
    assert third.status.available and third.status.stale and not third.status.success
    assert third.status.error == "timeout"
    assert third.status.cache_age_seconds == 601
    assert third.observations == first.observations
    assert "private host details" not in (third.status.error or "")


def test_stale_cache_is_replaced_after_valid_refresh(tmp_path):
    state = {"now": NOW, "temperature": 7.0}

    def handler(_request):
        return httpx.Response(200, json=collection([feature(properties={"air_temp": state["temperature"]})]))

    def current_time():
        return state["now"]

    async def scenario():
        source = client(tmp_path, handler, now=current_time)
        first = await source.fetch_regional_observations()
        original_cache = source.cache_path.read_text(encoding="utf-8")
        state["now"] += timedelta(seconds=601)
        state["temperature"] = 9.0
        second = await source.fetch_regional_observations()
        return source, first, second, original_cache

    source, first, second, original_cache = asyncio.run(scenario())
    assert first.observations[0].temperature.value == 7.0
    assert second.status.refreshed and second.status.success and not second.status.stale
    assert second.observations[0].temperature.value == 9.0
    assert source.cache_path.read_text(encoding="utf-8") != original_cache


def test_corrupt_cache_is_ignored_and_replaced_with_validated_snapshot(tmp_path):
    calls = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(200, json=collection([feature()]))

    source = client(tmp_path, handler)
    source.cache_dir.mkdir(parents=True, exist_ok=True)
    source.cache_path.write_text("{broken", encoding="utf-8")
    result = asyncio.run(source.fetch_regional_observations())
    assert result.status.refreshed and result.status.success
    assert source._read_cache() is not None
    assert len(calls) == 1


def test_structurally_invalid_cache_observation_is_not_stale_fallback(tmp_path):
    source = client(tmp_path, lambda _request: httpx.Response(503))
    observations, diagnostics, _ = parse_feature_collection(collection([feature()]), NOW)
    source._write_cache(NOW, observations, diagnostics)
    cache_payload = json.loads(source.cache_path.read_text(encoding="utf-8"))
    cache_payload["observations"][0]["latitude"] = 91
    source.cache_path.write_text(json.dumps(cache_payload), encoding="utf-8")

    result = asyncio.run(source.fetch_regional_observations())
    assert not result.status.available
    assert result.status.error == "http_503"


def test_failed_atomic_replacement_keeps_previous_valid_cache(tmp_path, monkeypatch):
    def good(_request):
        return httpx.Response(200, json=collection([feature()]))

    initial = client(tmp_path, good)
    asyncio.run(initial.fetch_regional_observations())
    before = initial.cache_path.read_text(encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("private filesystem details")

    monkeypatch.setattr(swob.os, "replace", fail_replace)
    refreshed = asyncio.run(
        client(
            tmp_path,
            good,
            now=lambda: NOW + timedelta(seconds=601),
        ).fetch_regional_observations()
    )
    assert refreshed.status.available and refreshed.status.stale
    assert refreshed.status.error == "cache_write_failure"
    assert initial.cache_path.read_text(encoding="utf-8") == before
    assert list(tmp_path.iterdir()) == [initial.cache_path]


def test_failed_refresh_without_cache_reports_independent_unavailable_status(tmp_path):
    def handler(_request):
        return httpx.Response(503)

    result = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    assert result.status.source == "ECCC GeoMet/SWOB"
    assert not result.status.available and not result.status.success
    assert result.status.error == "http_503"


def test_oversized_provider_page_is_rejected_before_json_parsing(tmp_path, monkeypatch):
    monkeypatch.setattr(swob, "MAX_PAGE_BYTES", 16)

    def handler(_request):
        return httpx.Response(200, json=collection([feature()]))

    result = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    assert not result.status.available
    assert result.status.error == "response_size_limit"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://example.invalid/"}),
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"type": "FeatureCollection", "features": []}),
        httpx.Response(200, json=collection([feature(properties={"msc_id-value": None})] * 3)),
    ],
)
def test_redirect_invalid_schema_and_widespread_record_loss_are_rejected(tmp_path, response):
    def handler(_request):
        return response

    result = asyncio.run(client(tmp_path, handler).fetch_regional_observations())
    assert not result.status.available
    assert not result.status.success
    assert not result.status.refreshed
    assert list(tmp_path.glob("*.json")) == []


def test_unstable_pagination_falls_back_without_replacing_valid_cache(tmp_path, monkeypatch):
    def good(_request):
        return httpx.Response(200, json=collection([feature()]))

    source = client(tmp_path, good)
    asyncio.run(source.fetch_regional_observations())
    cached_text = source.cache_path.read_text(encoding="utf-8")

    pages = 0

    def unstable(request):
        nonlocal pages
        pages += 1
        count = 502 if pages == 1 else 503
        return page_response([feature(f"s-{i}", source_id=f"id-{i}") for i in range(count)], count, int(request.url.params["offset"]))

    monkeypatch.setattr(swob, "MAX_RECORDS", 1000)
    stale_client = client(tmp_path, unstable, now=lambda: NOW + timedelta(seconds=601))
    result = asyncio.run(stale_client.fetch_regional_observations())
    assert result.status.stale and result.status.available
    assert result.status.error == "unstable_page_count"
    assert stale_client.cache_path.read_text(encoding="utf-8") == cached_text


def test_concurrent_refreshes_share_one_request_and_cache_write(tmp_path):
    calls = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(200, json=collection([feature()]))

    source = client(tmp_path, handler)

    async def run():
        return await asyncio.gather(
            source.fetch_regional_observations(),
            source.fetch_regional_observations(),
            source.fetch_regional_observations(),
        )

    results = asyncio.run(run())
    assert len(calls) == 1
    assert sum(result.status.refreshed for result in results) == 1
    assert sum(result.status.cache_hit for result in results) == 2


def test_bbox_and_ttl_configuration_are_validated(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="bbox"):
        EcccSwobClient(bbox="-123,49,-124,50", cache_dir=tmp_path)
    with pytest.raises(ValueError, match="TTL"):
        EcccSwobClient(ttl_seconds=10, cache_dir=tmp_path)
    west = EcccSwobClient(cache_dir=tmp_path, bbox="-123.4,49.1,-122.8,49.4")
    east = EcccSwobClient(cache_dir=tmp_path, bbox="-123.3,49.15,-122.85,49.35")
    assert west.cache_identity != east.cache_identity
    monkeypatch.setenv("SWOB_BBOX", "-123.4,49.1,-122.8,49.4")
    monkeypatch.setenv("SWOB_CACHE_TTL_SECONDS", "900")
    configured = EcccSwobClient(cache_dir=tmp_path)
    assert configured.bbox == "-123.4,49.1,-122.8,49.4"
    assert configured.ttl_seconds == 900
