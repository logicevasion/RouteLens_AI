"""MapTiler geocoding adapter and provider response normalization."""

from __future__ import annotations

import math
import os
from typing import Any
from urllib.parse import quote

import httpx

from app.geography import CITY_OF_VANCOUVER, validate_destination
from app.models import Location

MAPTILER_ENDPOINT = "https://api.maptiler.com/geocoding"
MAPTILER_PROXIMITY = "-123.1207,49.2827"
MAX_CANDIDATES = 5
DESTINATION_PROVIDER_LIMIT = 10
REQUEST_TIMEOUT_SECONDS = 8.0


def _city_bbox() -> str:
    """Return MapTiler's west,south,east,north bbox for the municipal polygon."""
    west, south, east, north = CITY_OF_VANCOUVER.bounds
    return f"{west},{south},{east},{north}"


class GeocodingError(Exception):
    """Sanitized geocoding error safe to map to an application response."""


class GeocodingConfigurationError(GeocodingError):
    """Raised when the server has no MapTiler credential configured."""


class GeocodingUpstreamError(GeocodingError):
    """Raised when MapTiler cannot provide a usable response."""


def normalize_feature(feature: Any) -> Location | None:
    """Normalize one GeoJSON point feature; skip malformed candidates."""
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        return None

    identifier = feature.get("id")
    geometry = feature.get("geometry")
    if not isinstance(identifier, str) or not identifier.strip():
        return None
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    longitude, latitude = coordinates[:2]
    if (
        isinstance(longitude, bool)
        or isinstance(latitude, bool)
        or not isinstance(longitude, (int, float))
        or not isinstance(latitude, (int, float))
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
    ):
        return None
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        return None

    properties = feature.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    name = _first_text(
        feature.get("text_en"),
        feature.get("text"),
        properties.get("name_en"),
        properties.get("name"),
        feature.get("place_name_en"),
        feature.get("place_name"),
    )
    address = _first_text(feature.get("place_name_en"), feature.get("place_name"))
    if name is None:
        return None

    try:
        return Location(
            name=name,
            latitude=float(latitude),
            longitude=float(longitude),
            address=address,
            provider_id=identifier.strip(),
        )
    except (TypeError, ValueError):
        return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_response(payload: Any, *, limit: int = MAX_CANDIDATES) -> list[Location]:
    """Normalize valid point candidates from a MapTiler FeatureCollection."""
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise GeocodingUpstreamError("MapTiler returned an invalid geocoding response.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise GeocodingUpstreamError("MapTiler returned an invalid geocoding response.")

    candidates: list[Location] = []
    for feature in features:
        location = normalize_feature(feature)
        if location is not None:
            candidates.append(location)
        if len(candidates) == limit:
            break
    return candidates


class MapTilerGeocoder:
    """Small async adapter for MapTiler's GeoJSON geocoding endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (api_key if api_key is not None else os.getenv("MAPTILER_API_KEY", "")).strip()
        self._transport = transport

    async def search(self, query: str, *, destination: bool = False) -> list[Location]:
        if not self._api_key:
            raise GeocodingConfigurationError("Location search is not configured on this server.")

        encoded_query = quote(query, safe="")
        candidate_limit = DESTINATION_PROVIDER_LIMIT if destination else MAX_CANDIDATES
        params = {
            "key": self._api_key,
            "autocomplete": "true",
            "country": "ca",
            "language": "en",
            "limit": str(candidate_limit),
            "proximity": MAPTILER_PROXIMITY,
        }
        if destination:
            params["bbox"] = _city_bbox()
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = await client.get(f"{MAPTILER_ENDPOINT}/{encoded_query}.json", params=params)
        except httpx.TimeoutException:
            raise GeocodingUpstreamError("Location search timed out. Please try again.") from None
        except httpx.RequestError:
            raise GeocodingUpstreamError("Location search is temporarily unavailable.") from None

        if response.status_code in (401, 403):
            raise GeocodingUpstreamError("Location search could not authenticate with its provider.")
        if response.status_code >= 400:
            raise GeocodingUpstreamError("Location search is temporarily unavailable.")
        try:
            candidates = normalize_response(response.json(), limit=candidate_limit)
        except (ValueError, TypeError):
            raise GeocodingUpstreamError("MapTiler returned an invalid geocoding response.") from None
        if not destination:
            return candidates
        return [candidate for candidate in candidates if validate_destination(candidate).valid][:MAX_CANDIDATES]
