"""openrouteservice driving-directions adapter and route normalization."""

from __future__ import annotations

import math
import os
from typing import Any

import httpx

from app.models import Location, RouteCandidate

ORS_ENDPOINT = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
REQUEST_TIMEOUT_SECONDS = 12.0
ALTERNATIVE_ROUTES = {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4}


class RoutingError(Exception):
    """Sanitized routing error safe to map to an application response."""


class RoutingConfigurationError(RoutingError):
    """Raised when the server has no ORS credential configured."""


class RoutingAuthenticationError(RoutingError):
    """Raised when ORS rejects the configured credential."""


class RoutingRateLimitError(RoutingError):
    """Raised when ORS reports that its request limit was reached."""


class RoutingNoRouteError(RoutingError):
    """Raised when ORS confirms that the supplied coordinates are unroutable."""


class RoutingTimeoutError(RoutingError):
    """Raised when ORS does not respond before the request timeout."""


class RoutingUpstreamError(RoutingError):
    """Raised for unavailable or unexpected ORS responses."""


def _valid_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _normalize_route(feature: Any, index: int) -> RouteCandidate | None:
    """Normalize one provider feature, ignoring unusable alternatives."""
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        return None

    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    for position in coordinates:
        if not isinstance(position, list) or len(position) < 2:
            return None
        longitude, latitude = position[:2]
        if (
            not _valid_number(longitude)
            or not _valid_number(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            return None

    properties = feature.get("properties")
    summary = properties.get("summary") if isinstance(properties, dict) else None
    if not isinstance(summary, dict):
        return None
    distance = summary.get("distance")
    duration = summary.get("duration")
    if not _valid_number(distance) or distance <= 0 or not _valid_number(duration) or duration <= 0:
        return None

    try:
        return RouteCandidate(
            id=f"route-{index}",
            geometry={"type": "LineString", "coordinates": coordinates},
            distance_meters=float(distance),
            duration_seconds=round(duration),
            label=f"Route {index}",
        )
    except (TypeError, ValueError):
        return None


def normalize_response(payload: Any) -> list[RouteCandidate]:
    """Normalize valid routes from an ORS GeoJSON FeatureCollection."""
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise RoutingUpstreamError("The routing provider returned an invalid response.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise RoutingUpstreamError("The routing provider returned an invalid response.")

    candidates: list[RouteCandidate] = []
    for index, feature in enumerate(features, start=1):
        candidate = _normalize_route(feature, index)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


class OpenRouteServiceRouter:
    """Small async adapter for ORS driving-car GeoJSON directions."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.getenv("OPENROUTESERVICE_API_KEY", "")).strip()
        self._transport = transport

    async def routes(self, origin: Location, destination: Location) -> list[RouteCandidate]:
        if not self._api_key:
            raise RoutingConfigurationError("Driving routes are not configured on this server.")

        body = {
            "coordinates": [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude],
            ],
            "units": "m",
            "instructions": False,
            "alternative_routes": ALTERNATIVE_ROUTES,
        }
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    ORS_ENDPOINT,
                    json=body,
                    headers={"Authorization": self._api_key},
                )
        except httpx.TimeoutException:
            raise RoutingTimeoutError("The routing provider timed out. Please try again.") from None
        except httpx.RequestError:
            raise RoutingUpstreamError("Driving routes are temporarily unavailable.") from None

        if response.status_code in (401, 403):
            raise RoutingAuthenticationError("The routing provider rejected its configured credential.")
        if response.status_code == 429:
            raise RoutingRateLimitError("The routing provider rate limit was reached. Please try again later.")
        if response.status_code == 404:
            try:
                error = response.json().get("error", {})
            except (ValueError, TypeError, AttributeError):
                error = {}
            if isinstance(error, dict) and error.get("code") == 2010:
                raise RoutingNoRouteError("The routing provider could not find a usable route for these locations.")
        if response.status_code >= 400:
            raise RoutingUpstreamError("Driving routes are temporarily unavailable.")
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise RoutingUpstreamError("The routing provider returned an invalid response.") from None
        return normalize_response(payload)
