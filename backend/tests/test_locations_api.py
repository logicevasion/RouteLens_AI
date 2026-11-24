"""API and municipal-boundary tests for canonical journey locations."""

import asyncio

import httpx
import pytest
from shapely.geometry import Point

from app.geocoding import GeocodingConfigurationError, GeocodingUpstreamError, MapTilerGeocoder
from app.geography import CITY_OF_VANCOUVER
from app.main import app
from app.models import Location


def api_request(method: str, path: str, **kwargs: object) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def location(latitude: float, longitude: float, name: str = "Test place") -> Location:
    return Location(name=name, latitude=latitude, longitude=longitude)


@pytest.mark.parametrize(
    ("name", "latitude", "longitude"),
    [
        ("Downtown Vancouver", 49.2827, -123.1207),
        ("Residential Vancouver", 49.255, -123.135),
    ],
)
def test_vancouver_destinations_are_valid(name: str, latitude: float, longitude: float) -> None:
    response = api_request(
        "POST",
        "/api/locations/validate-destination",
        json=location(latitude, longitude, name).model_dump(),
    )

    assert response.status_code == 200
    assert response.json() == {"valid": True, "reason": None}


@pytest.mark.parametrize(
    ("name", "latitude", "longitude"),
    [
        ("Richmond", 49.16316819009346, -123.1374143064022),
        ("Burnaby", 49.248, -123.003),
        ("North Vancouver", 49.320, -123.072),
    ],
)
def test_nearby_municipalities_are_rejected_geographically(
    name: str, latitude: float, longitude: float
) -> None:
    response = api_request(
        "POST",
        "/api/locations/validate-destination",
        json=location(latitude, longitude, name).model_dump(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "reason": "Destination must be inside the City of Vancouver municipal boundary.",
    }


def test_point_on_city_boundary_is_included() -> None:
    boundary_point = CITY_OF_VANCOUVER.boundary.interpolate(0.5, normalized=True)
    response = api_request(
        "POST",
        "/api/locations/validate-destination",
        json=location(boundary_point.y, boundary_point.x).model_dump(),
    )

    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_point_just_outside_city_boundary_is_rejected() -> None:
    boundary_point = CITY_OF_VANCOUVER.boundary.interpolate(0.5, normalized=True)
    center = CITY_OF_VANCOUVER.centroid
    outside = Point(
        boundary_point.x + (boundary_point.x - center.x) * 1e-6,
        boundary_point.y + (boundary_point.y - center.y) * 1e-6,
    )
    response = api_request(
        "POST",
        "/api/locations/validate-destination",
        json=location(outside.y, outside.x).model_dump(),
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_invalid_coordinates_are_rejected_by_api_model() -> None:
    response = api_request(
        "POST",
        "/api/locations/validate-destination",
        json={"name": "Outside world", "latitude": 95, "longitude": -123},
    )

    assert response.status_code == 422


def test_search_returns_normalized_candidates_and_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    roles: list[bool] = []

    class FakeGeocoder:
        async def search(self, query: str, *, destination: bool = False) -> list[Location]:
            roles.append(destination)
            if query == "missing place":
                return []
            return [Location(name="Downtown", latitude=49.28249, longitude=-123.11814, provider_id="id.1")]

    monkeypatch.setattr("app.routes.MapTilerGeocoder", lambda: FakeGeocoder())
    response = api_request("GET", "/api/geocoding/search", params={"q": "Downtown"})
    empty_response = api_request("GET", "/api/geocoding/search", params={"q": "missing place"})
    destination_response = api_request(
        "GET", "/api/geocoding/search", params={"q": "Downtown", "role": "destination"}
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Downtown",
            "latitude": 49.28249,
            "longitude": -123.11814,
            "address": None,
            "provider_id": "id.1",
        }
    ]
    assert empty_response.status_code == 200
    assert empty_response.json() == []
    assert destination_response.status_code == 200
    assert roles == [False, False, True]


def test_search_filters_destinations_through_maptiler_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    # Lonsdale Quay falls within Vancouver's bounding rectangle but outside the municipal polygon.
    quay_lon, quay_lat = -123.0826, 49.3099
    places = [
        ("lonsdale-quay", "Lonsdale Quay", [quay_lon, quay_lat]),
        ("city-hall", "Vancouver City Hall", [-123.1146, 49.2606]),
    ]
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": place_id,
                "text": name,
                "geometry": {"type": "Point", "coordinates": coordinates},
            }
            for place_id, name, coordinates in places
        ],
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr("app.routes.MapTilerGeocoder", lambda: MapTilerGeocoder("test-key", transport=transport))
    destination = api_request("GET", "/api/geocoding/search", params={"q": "Vancouver", "role": "destination"})
    origin = api_request("GET", "/api/geocoding/search", params={"q": "Vancouver", "role": "origin"})

    assert destination.status_code == origin.status_code == 200
    assert [item["provider_id"] for item in destination.json()] == ["city-hall"]
    assert [item["provider_id"] for item in origin.json()] == ["lonsdale-quay", "city-hall"]
    destination_request, origin_request = requests
    west, south, east, north = map(float, destination_request.url.params["bbox"].split(","))
    assert west < quay_lon < east and south < quay_lat < north
    assert "bbox" not in origin_request.url.params


def test_search_rejects_unknown_role() -> None:
    response = api_request("GET", "/api/geocoding/search", params={"q": "Vancouver", "role": "other"})
    assert response.status_code == 422


def test_search_rejects_short_or_blank_queries() -> None:
    assert api_request("GET", "/api/geocoding/search", params={"q": "x"}).status_code == 422
    assert api_request("GET", "/api/geocoding/search", params={"q": "  "}).status_code == 422
    assert api_request("GET", "/api/geocoding/search", params={"q": "a" * 201}).status_code == 422


def test_search_provider_failure_returns_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedGeocoder:
        async def search(self, query: str, *, destination: bool = False) -> list[Location]:
            raise GeocodingUpstreamError("Location search timed out. Please try again.")

    monkeypatch.setattr("app.routes.MapTilerGeocoder", lambda: FailedGeocoder())
    response = api_request("GET", "/api/geocoding/search", params={"q": "Vancouver"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Location search timed out. Please try again."}


def test_search_missing_server_credential_returns_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnconfiguredGeocoder:
        async def search(self, query: str, *, destination: bool = False) -> list[Location]:
            raise GeocodingConfigurationError("Location search is not configured on this server.")

    monkeypatch.setattr("app.routes.MapTilerGeocoder", lambda: UnconfiguredGeocoder())
    response = api_request("GET", "/api/geocoding/search", params={"q": "Vancouver"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Location search is not configured on this server."}


def test_health_endpoint_remains_operational() -> None:
    response = api_request("GET", "/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
