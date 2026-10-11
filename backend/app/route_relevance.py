"""Deterministic Road Ahead matching against an explicitly selected route."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from pyproj import Transformer
from pyproj.exceptions import ProjError
from shapely.errors import GEOSException
from shapely.geometry import LineString, shape
from shapely.ops import transform

from app.road_ahead import CityEvent

GEOGRAPHIC_CRS = "EPSG:4326"
PROJECTED_CRS = "EPSG:26910"  # NAD83 / UTM zone 10N, appropriate for Metro Vancouver.
DEFAULT_NEARBY_DISTANCE_METERS = 500.0
DEFAULT_NEARBY_LIMIT = 10

_PROJECTOR = Transformer.from_crs(GEOGRAPHIC_CRS, PROJECTED_CRS, always_xy=True)


@dataclass(frozen=True)
class RouteEventMatch:
    """A source event with its deterministic geographic relevance to one route."""

    event: CityEvent
    classification: Literal["direct_overlap", "nearby"]
    distance_meters: float


@dataclass(frozen=True)
class UnmatchableEvent:
    """An event that could not be evaluated, with a bounded reason code."""

    event_id: str
    reason: Literal[
        "missing_geometry",
        "invalid_structure",
        "empty_geometry",
        "invalid_topology",
        "projection_failure",
    ]


@dataclass(frozen=True)
class RouteEventMatchResult:
    """Relevant matches plus identities of events without usable geometry."""

    matches: tuple[RouteEventMatch, ...]
    unmatchable_events: tuple[UnmatchableEvent, ...]

    @property
    def unmatchable_event_ids(self) -> tuple[str, ...]:
        return tuple(item.event_id for item in self.unmatchable_events)

    @property
    def direct_overlaps(self) -> tuple[RouteEventMatch, ...]:
        return tuple(match for match in self.matches if match.classification == "direct_overlap")

    @property
    def nearby_events(self) -> tuple[RouteEventMatch, ...]:
        return tuple(match for match in self.matches if match.classification == "nearby")


class RouteGeometryError(ValueError):
    """The selected route is not a usable GeoJSON LineString."""


def _valid_position(position: object) -> bool:
    return (
        isinstance(position, (list, tuple))
        and len(position) >= 2
        and all(
            not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
            for value in position
        )
        and -180 <= position[0] <= 180
        and -90 <= position[1] <= 90
    )


def _valid_event_coordinates(geometry: object) -> bool:
    """Validate supported GeoJSON shapes without repairing source coordinates."""
    if not isinstance(geometry, dict):
        return False
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "LineString":
        return isinstance(coordinates, list) and len(coordinates) >= 2 and all(
            _valid_position(position) for position in coordinates
        )
    if kind == "MultiLineString":
        return isinstance(coordinates, list) and bool(coordinates) and all(
            isinstance(line, list)
            and len(line) >= 2
            and all(_valid_position(position) for position in line)
            for line in coordinates
        )
    if kind == "Polygon":
        if not isinstance(coordinates, list) or not coordinates:
            return False
        for ring in coordinates:
            if (
                not isinstance(ring, list)
                or len(ring) < 4
                or not all(_valid_position(position) for position in ring)
                or ring[0][:2] != ring[-1][:2]
            ):
                return False
        return True
    if kind == "GeometryCollection":
        geometries = geometry.get("geometries")
        return (
            isinstance(geometries, list)
            and bool(geometries)
            and all(_valid_event_coordinates(component) for component in geometries)
        )
    return False


def _is_explicit_empty_geometry(geometry: dict) -> bool:
    kind = geometry.get("type")
    if kind == "GeometryCollection":
        return geometry.get("geometries") == []
    if kind in {"LineString", "MultiLineString", "Polygon"}:
        return geometry.get("coordinates") == []
    return False


def _prepare_route(route_geometry: object) -> LineString:
    if (
        not isinstance(route_geometry, dict)
        or route_geometry.get("type") != "LineString"
        or not _valid_event_coordinates(route_geometry)
    ):
        raise RouteGeometryError("Selected route must be a valid GeoJSON LineString.")
    try:
        route = shape(route_geometry)
        projected = transform(_PROJECTOR.transform, route)
    except (GEOSException, ProjError, TypeError, ValueError, OverflowError) as exc:
        raise RouteGeometryError("Selected route could not be projected safely.") from exc
    if projected.is_empty or not projected.is_valid or projected.length <= 0:
        raise RouteGeometryError("Selected route must contain a usable non-empty LineString.")
    return projected


def _prepare_event(event_geometry: object):
    if event_geometry is None:
        return None, "missing_geometry"
    if not isinstance(event_geometry, dict) or event_geometry.get("type") not in {
        "LineString",
        "MultiLineString",
        "Polygon",
        "GeometryCollection",
    }:
        return None, "invalid_structure"
    if _is_explicit_empty_geometry(event_geometry):
        return None, "empty_geometry"
    if not _valid_event_coordinates(event_geometry):
        return None, "invalid_structure"
    try:
        geometry = shape(event_geometry)
    except (GEOSException, TypeError, ValueError, OverflowError):
        return None, "invalid_structure"
    if geometry.is_empty:
        return None, "empty_geometry"
    if not geometry.is_valid:
        return None, "invalid_topology"
    try:
        projected = transform(_PROJECTOR.transform, geometry)
    except (GEOSException, ProjError, TypeError, ValueError, OverflowError):
        return None, "projection_failure"
    if projected.is_empty:
        return None, "empty_geometry"
    if not projected.is_valid:
        return None, "invalid_topology"
    return projected, None


def _identity_key(event: CityEvent) -> tuple[str, str, str]:
    return event.source_dataset_id, event.source_record_id, event.id


def match_route_events(
    route_geometry: dict,
    events: list[CityEvent],
    *,
    nearby_distance_meters: float = DEFAULT_NEARBY_DISTANCE_METERS,
    nearby_limit: int = DEFAULT_NEARBY_LIMIT,
) -> RouteEventMatchResult:
    """Match event geometries to a selected route using projected metre distances.

    Exact Shapely intersections are `direct_overlap`; non-intersecting event
    geometries within the configured threshold are `nearby`. The limit applies
    only to nearby events. Geographic closeness is not a traffic-impact claim.
    """
    if (
        isinstance(nearby_distance_meters, bool)
        or not isinstance(nearby_distance_meters, (int, float))
        or not math.isfinite(nearby_distance_meters)
        or nearby_distance_meters < 0
    ):
        raise ValueError("nearby_distance_meters must be a finite non-negative number.")
    if isinstance(nearby_limit, bool) or not isinstance(nearby_limit, int) or nearby_limit < 0:
        raise ValueError("nearby_limit must be a non-negative integer.")

    route = _prepare_route(route_geometry)
    direct: list[RouteEventMatch] = []
    nearby: list[RouteEventMatch] = []
    unmatchable: dict[str, UnmatchableEvent] = {}
    seen: set[tuple[str, str, str]] = set()

    for event in events:
        identity = _identity_key(event)
        if identity in seen:
            continue
        seen.add(identity)
        projected_event, reason = _prepare_event(event.geometry)
        if projected_event is None:
            unmatchable[event.id] = UnmatchableEvent(event_id=event.id, reason=reason)
            continue
        if route.intersects(projected_event):
            direct.append(RouteEventMatch(event, "direct_overlap", 0.0))
            continue
        distance = float(route.distance(projected_event))
        if distance <= nearby_distance_meters:
            nearby.append(RouteEventMatch(event, "nearby", distance))

    direct.sort(key=lambda match: _identity_key(match.event))
    nearby.sort(key=lambda match: (match.distance_meters, _identity_key(match.event)))
    return RouteEventMatchResult(
        matches=tuple(direct + nearby[:nearby_limit]),
        unmatchable_events=tuple(unmatchable[event_id] for event_id in sorted(unmatchable)),
    )
