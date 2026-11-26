"""Routing endpoint contract, validation, and safe failure behavior."""

import asyncio
import json
import logging
from pathlib import Path

import httpx
import pytest

from app.main import app
from app.models import Location
from app.routing import (
    OpenRouteServiceRouter,
    RoutingAuthenticationError,
    RoutingConfigurationError,
    RoutingNoRouteError,
    RoutingRateLimitError,
    RoutingTimeoutError,
    RoutingUpstreamError,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "openrouteservice" / "driving_richmond_to_downtown.geojson"


def api_request(payload: object) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post("/api/routes/driving", json=payload)

    return asyncio.run(request())


def request_payload() -> dict:
    return {
        "origin": Location(name="Richmond", latitude=49.163168, longitude=-123.137414).model_dump(),
        "destination": Location(name="Downtown Vancouver", latitude=49.282493, longitude=-123.118137).model_dump(),
    }


def test_returns_normalized_candidates_without_provider_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRouter:
        async def routes(self, origin: Location, destination: Location) -> list[dict]:
            assert origin.longitude == -123.137414
            assert destination.longitude == -123.118137
            provider_payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            from app.routing import normalize_response

            return normalize_response(provider_payload)

    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", lambda: FakeRouter())
    response = api_request(request_payload())

    assert response.status_code == 200
    body = response.json()
    assert len(body["routes"]) == 3
    assert body["routes"][0]["id"] == "route-1"
    assert body["routes"][0]["geometry"]["type"] == "LineString"
    assert body["routes"][0]["distance_meters"] > 0
    assert body["routes"][0]["duration_seconds"] > 0
    assert "features" not in body
    assert "summary" not in body["routes"][0]


def test_empty_candidate_list_is_a_successful_no_route_result(monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyRouter:
        async def routes(self, origin: Location, destination: Location) -> list:
            return []

    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", lambda: EmptyRouter())
    response = api_request(request_payload())
    assert response.status_code == 200
    assert response.json() == {"routes": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"origin": {}, "destination": {}},
        {"origin": {"name": "Origin", "longitude": -123}, "destination": {}},
        {"origin": {"name": "Origin", "latitude": 49, "longitude": 181}, "destination": {}},
        {"origin": {"name": "Origin", "latitude": 49, "longitude": -123, "display": "arbitrary"}, "destination": {}},
        {"origin": {"name": "Origin", "latitude": 49, "longitude": -123}},
    ],
)
def test_rejects_incomplete_or_malformed_locations(payload: dict) -> None:
    assert api_request(payload).status_code == 422


def test_rejects_destination_outside_city_boundary_without_calling_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def should_not_route():
        raise AssertionError("Provider must not be called for unsupported destinations")

    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", should_not_route)
    payload = request_payload()
    payload["destination"]["name"] = "Richmond"
    payload["destination"]["latitude"] = 49.163168
    payload["destination"]["longitude"] = -123.137414

    response = api_request(payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_destination"


@pytest.mark.parametrize(
    ("exception", "status", "code"),
    [
        (RoutingConfigurationError("safe configuration error"), 503, "routing_not_configured"),
        (RoutingAuthenticationError("safe authentication error"), 502, "routing_authentication_failed"),
        (RoutingNoRouteError("safe no-route result"), 422, "no_route_found"),
        (RoutingTimeoutError("safe timeout"), 504, "routing_timeout"),
        (RoutingRateLimitError("safe rate limit"), 503, "routing_rate_limited"),
        (RoutingUpstreamError("safe provider error"), 502, "routing_provider_unavailable"),
    ],
)
def test_provider_failure_uses_machine_readable_safe_error(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    status: int,
    code: str,
) -> None:
    class FailedRouter:
        async def routes(self, origin: Location, destination: Location) -> list:
            raise exception

    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", lambda: FailedRouter())
    response = api_request(request_payload())

    assert response.status_code == status
    assert response.json()["detail"]["code"] == code


@pytest.mark.parametrize(
    ("failure", "diagnostic"),
    [
        ("upstream", "openrouteservice.upstream_http_error status=503"),
        ("transport", "openrouteservice.transport_error exception_class=ConnectError"),
        ("usage_hook", "openrouteservice.upstream_http_error status=503"),
    ],
)
def test_routing_logs_the_failure_stage_without_exposing_request_details(
    monkeypatch, usage_store, caplog, failure, diagnostic,
):
    dispatches = []
    private_detail = "synthetic-secret https://provider.invalid/?token=private"

    def transport(request: httpx.Request) -> httpx.Response:
        dispatches.append(request)
        if failure == "transport":
            raise httpx.ConnectError(private_detail, request=request)
        return httpx.Response(503, text=private_detail)

    if failure == "usage_hook":
        def fail_before_transport(_operation):
            raise httpx.ConnectError(private_detail)

        monkeypatch.setattr(usage_store, "count_dispatch", fail_before_transport)

    router = OpenRouteServiceRouter("synthetic-secret", transport=httpx.MockTransport(transport))
    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", lambda: router)
    with caplog.at_level(logging.WARNING, logger="app.routing"):
        response = api_request(request_payload())

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "routing_provider_unavailable",
            "message": "Driving routes are temporarily unavailable.",
        },
    }
    assert len(dispatches) == 1
    records = [record for record in caplog.records if record.name == "app.routing"]
    assert [record.getMessage() for record in records] == [diagnostic]
    assert all(record.exc_info is None for record in records)
    if failure == "usage_hook":
        assert (
            "api_usage.request_hook_error operation=openrouteservice.directions exception_class=ConnectError"
            in caplog.messages
        )
        usage_store.initialize()
        assert usage_store.read_report(*usage_store.window(30)).gaps == {usage_store.today()}
    assert "synthetic-secret" not in caplog.text
    assert "provider.invalid" not in caplog.text


def test_routing_dispatches_only_to_the_heigit_directions_endpoint(monkeypatch, caplog):
    requests = []

    def transport(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        return httpx.Response(410)

    router = OpenRouteServiceRouter("synthetic-key", transport=httpx.MockTransport(transport))
    monkeypatch.setattr("app.routes.OpenRouteServiceRouter", lambda: router)
    response = api_request(request_payload())

    assert requests == [
        ("POST", "https://api.heigit.org/openrouteservice/v2/directions/driving-car/geojson"),
    ]
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "routing_provider_unavailable"
    assert "openrouteservice.upstream_http_error status=410" in caplog.messages


def test_health_endpoint_remains_available() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/health")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
