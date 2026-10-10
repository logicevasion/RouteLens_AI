"""Deterministic tests for MapTiler response normalization and HTTP handling."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.geocoding import (
    MAX_CANDIDATES,
    GeocodingConfigurationError,
    GeocodingUpstreamError,
    MapTilerGeocoder,
    normalize_feature,
    normalize_response,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "maptiler"
DOWNTOWN_FIXTURE = FIXTURES / "geocoding_selected_downtown_vancouver.json"


def fixture_payload() -> dict:
    return json.loads(DOWNTOWN_FIXTURE.read_text(encoding="utf-8"))


def test_normalizes_observed_point_features_and_preserves_geojson_axis_order() -> None:
    result = normalize_response(fixture_payload())

    assert len(result) == 5
    assert result[0].name == "Downtown"
    assert result[0].provider_id == "municipal_district.151618"
    assert result[0].longitude == pytest.approx(-123.11813659965992)
    assert result[0].latitude == pytest.approx(49.28249294135585)
    assert result[0].address == "Downtown, Vancouver, Metro Vancouver Regional District, British Columbia, Canada"


def test_missing_optional_address_is_preserved_as_none() -> None:
    feature = {
        "type": "Feature",
        "id": "place.1",
        "text": "Example",
        "geometry": {"type": "Point", "coordinates": [-123.1, 49.2]},
    }

    result = normalize_feature(feature)

    assert result is not None
    assert result.address is None


@pytest.mark.parametrize(
    "feature",
    [
        {"type": "Feature", "text": "No ID", "geometry": {"type": "Point", "coordinates": [1, 2]}},
        {"type": "Feature", "id": "no-point", "text": "No geometry", "geometry": None},
        {"type": "Feature", "id": "short", "text": "Short", "geometry": {"type": "Point", "coordinates": [-123.1]}},
        {"type": "Feature", "id": "bad-lon", "text": "Bad", "geometry": {"type": "Point", "coordinates": [181, 49]}},
        {"type": "Feature", "id": "bad-lat", "text": "Bad", "geometry": {"type": "Point", "coordinates": [-123, -91]}},
        {"type": "Feature", "id": "nan", "text": "Bad", "geometry": {"type": "Point", "coordinates": [float("nan"), 49]}},
        {"type": "Feature", "id": "boolean", "text": "Bad", "geometry": {"type": "Point", "coordinates": [True, 49]}},
        {"type": "Feature", "id": "no-name", "geometry": {"type": "Point", "coordinates": [-123, 49]}},
    ],
)
def test_skips_candidates_without_valid_required_fields(feature: dict) -> None:
    assert normalize_feature(feature) is None


def test_empty_feature_collection_returns_no_candidates() -> None:
    assert normalize_response({"type": "FeatureCollection", "features": []}) == []


def test_skips_malformed_candidates_and_caps_result_count() -> None:
    valid = {
        "type": "Feature",
        "id": "place.1",
        "text": "Place",
        "geometry": {"type": "Point", "coordinates": [-123.1, 49.2]},
    }
    result = normalize_response({"type": "FeatureCollection", "features": [None, *[valid] * 8]})

    assert len(result) == MAX_CANDIDATES


@pytest.mark.parametrize("payload", [None, {}, {"type": "FeatureCollection"}, {"features": []}])
def test_rejects_malformed_response_structure(payload: object) -> None:
    with pytest.raises(GeocodingUpstreamError):
        normalize_response(payload)


def test_missing_credentials_fails_before_http_request() -> None:
    geocoder = MapTilerGeocoder(api_key=" ")

    with pytest.raises(GeocodingConfigurationError):
        asyncio.run(geocoder.search("Vancouver"))


def test_successful_request_uses_safe_bounded_regional_parameters() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=fixture_payload())

    geocoder = MapTilerGeocoder("test-secret", transport=httpx.MockTransport(handler))
    result = asyncio.run(geocoder.search("Downtown Vancouver"))

    assert len(result) == 5
    assert captured["path"].endswith("/Downtown Vancouver.json")
    params = captured["params"]
    assert params["key"] == "test-secret"
    assert params["limit"] == str(MAX_CANDIDATES)
    assert params["autocomplete"] == "true"
    assert params["country"] == "ca"
    assert params["proximity"] == "-123.1207,49.2827"


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_upstream_http_failures_are_sanitized(status_code: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="upstream details")

    geocoder = MapTilerGeocoder("never-return-this-key", transport=httpx.MockTransport(handler))

    with pytest.raises(GeocodingUpstreamError) as caught:
        asyncio.run(geocoder.search("Vancouver"))
    assert "never-return-this-key" not in str(caught.value)
    assert "upstream details" not in str(caught.value)


def test_timeout_error_is_safe() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret-bearing upstream URL")

    geocoder = MapTilerGeocoder("secret-key", transport=httpx.MockTransport(handler))

    with pytest.raises(GeocodingUpstreamError) as caught:
        asyncio.run(geocoder.search("Vancouver"))
    assert "secret-key" not in str(caught.value)
    assert "secret-bearing" not in str(caught.value)


def test_invalid_json_body_is_safe() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    geocoder = MapTilerGeocoder("secret-key", transport=httpx.MockTransport(handler))

    with pytest.raises(GeocodingUpstreamError, match="invalid geocoding response"):
        asyncio.run(geocoder.search("Vancouver"))
