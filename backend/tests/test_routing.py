"""Deterministic ORS normalization and request tests using accepted responses."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.models import Location
from app.routing import (
    ALTERNATIVE_ROUTES,
    ORS_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    OpenRouteServiceRouter,
    RoutingAuthenticationError,
    RoutingConfigurationError,
    RoutingNoRouteError,
    RoutingRateLimitError,
    RoutingTimeoutError,
    RoutingUpstreamError,
    normalize_response,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "openrouteservice"
RICHMOND_FIXTURE = FIXTURES / "driving_richmond_to_downtown.geojson"


def payload() -> dict:
    return json.loads(RICHMOND_FIXTURE.read_text(encoding="utf-8"))


def locations() -> tuple[Location, Location]:
    return (
        Location(name="Richmond", latitude=49.163168, longitude=-123.137414),
        Location(name="Downtown Vancouver", latitude=49.282493, longitude=-123.118137),
    )


@pytest.mark.parametrize("count", [3, 2, 1])
def test_normalizes_available_route_count_and_preserves_contract(count: int) -> None:
    data = payload()
    data["features"] = data["features"][:count]

    routes = normalize_response(data)

    assert len(routes) == count
    assert [route.id for route in routes] == [f"route-{index}" for index in range(1, count + 1)]
    assert routes[0].geometry["type"] == "LineString"
    assert routes[0].geometry["coordinates"][0] == data["features"][0]["geometry"]["coordinates"][0]
    assert routes[0].distance_meters == data["features"][0]["properties"]["summary"]["distance"]
    assert routes[0].duration_seconds == round(data["features"][0]["properties"]["summary"]["duration"])


def test_empty_collection_returns_no_routes() -> None:
    assert normalize_response({"type": "FeatureCollection", "features": []}) == []


def test_observed_alternatives_preserve_distinct_provider_geometries() -> None:
    routes = normalize_response(payload())

    assert len(routes) == 3
    geometries = {json.dumps(route.geometry["coordinates"]) for route in routes}
    assert len(geometries) == 3


@pytest.mark.parametrize(
    "mutate",
    [
        lambda feature: feature.update(geometry={"type": "Point", "coordinates": [-123, 49]}),
        lambda feature: feature.update(geometry={"type": "LineString", "coordinates": [[-123, 49]]}),
        lambda feature: feature.update(geometry={"type": "LineString", "coordinates": [[181, 49], [-123, 49]]}),
        lambda feature: feature.update(geometry={"type": "LineString", "coordinates": [[-123, 49], [float("nan"), 49]]}),
        lambda feature: feature["properties"]["summary"].pop("distance"),
        lambda feature: feature["properties"]["summary"].pop("duration"),
        lambda feature: feature["properties"]["summary"].update(distance=-1),
    ],
)
def test_skips_individual_routes_with_invalid_geometry_or_metadata(mutate) -> None:
    data = payload()
    mutate(data["features"][0])

    routes = normalize_response(data)

    assert len(routes) == 2
    assert [route.id for route in routes] == ["route-2", "route-3"]


@pytest.mark.parametrize("data", [None, {}, {"type": "FeatureCollection"}, {"type": "FeatureCollection", "features": {}}])
def test_rejects_malformed_collection(data: object) -> None:
    with pytest.raises(RoutingUpstreamError):
        normalize_response(data)


def test_missing_credentials_fails_before_http_request() -> None:
    with pytest.raises(RoutingConfigurationError):
        asyncio.run(OpenRouteServiceRouter(api_key=" ").routes(*locations()))


def test_request_uses_geojson_axis_order_profile_and_approved_alternative_parameters() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=payload())

    origin, destination = locations()
    router = OpenRouteServiceRouter("test-secret", transport=httpx.MockTransport(handler))
    routes = asyncio.run(router.routes(origin, destination))

    assert len(routes) == 3
    assert captured["url"] == ORS_ENDPOINT
    assert captured["headers"]["authorization"] == "test-secret"
    body = captured["body"]
    assert body["coordinates"] == [
        [origin.longitude, origin.latitude],
        [destination.longitude, destination.latitude],
    ]
    assert body["units"] == "m"
    assert body["instructions"] is False
    assert body["alternative_routes"] == ALTERNATIVE_ROUTES
    assert REQUEST_TIMEOUT_SECONDS > 0


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, RoutingAuthenticationError),
        (403, RoutingAuthenticationError),
        (429, RoutingRateLimitError),
        (400, RoutingUpstreamError),
        (500, RoutingUpstreamError),
    ],
)
def test_provider_http_failures_are_categorized_and_sanitized(status: int, exception: type[Exception]) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="secret-key https://provider.invalid/?token=x")

    router = OpenRouteServiceRouter("secret-key", transport=httpx.MockTransport(handler))
    with pytest.raises(exception) as caught:
        asyncio.run(router.routes(*locations()))
    assert "secret-key" not in str(caught.value)
    assert "provider.invalid" not in str(caught.value)


def test_timeout_is_sanitized() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("https://provider.invalid/?token=secret")

    router = OpenRouteServiceRouter("secret", transport=httpx.MockTransport(handler))
    with pytest.raises(RoutingTimeoutError) as caught:
        asyncio.run(router.routes(*locations()))
    assert "secret" not in str(caught.value)
    assert "provider.invalid" not in str(caught.value)


def test_ors_unroutable_point_error_is_distinguished_from_provider_failure() -> None:
    router = OpenRouteServiceRouter(
        "secret",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(404, json={"error": {"code": 2010, "message": "provider detail"}})
        ),
    )
    with pytest.raises(RoutingNoRouteError) as caught:
        asyncio.run(router.routes(*locations()))
    assert "provider detail" not in str(caught.value)


def test_malformed_json_and_unexpected_payload_are_sanitized() -> None:
    for response in (httpx.Response(200, content=b"not-json"), httpx.Response(200, json={"routes": []})):
        def handler(_: httpx.Request, response: httpx.Response = response) -> httpx.Response:
            return response

        router = OpenRouteServiceRouter(
            "secret",
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(RoutingUpstreamError):
            asyncio.run(router.routes(*locations()))
