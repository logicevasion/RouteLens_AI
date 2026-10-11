"""Deterministic route relevance for normalized regional DriveBC Open511 events."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Literal

from pyproj.exceptions import ProjError
from shapely.errors import GEOSException
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

from app.road_ahead import CityEvent
from app.route_relevance import (
    _PROJECTOR,
    UnmatchableEvent,
    _prepare_route,
    _valid_position,
)

DEFAULT_LINE_NEARBY_DISTANCE_METERS = 500.0
DEFAULT_POINT_NEARBY_DISTANCE_METERS = 250.0
DEFAULT_NEARBY_LIMIT = 10

GeometryBasis = Literal["linestring_intersection", "linestring_proximity", "point_proximity"]


@dataclass(frozen=True)
class DriveBCEventEvidence:
    """Provider metadata retained with explicit uncertainty qualifications."""

    event_type: str
    status: str | None
    severity: str | None
    event_subtypes: tuple[Any, ...]
    roads: tuple[dict[str, Any], ...]
    schedule: Any
    schedule_text: str | None
    direction_assessment: Literal["undetermined"] = "undetermined"
    temporal_applicability: Literal["unknown"] = "unknown"
    current_impact: Literal["not_established"] = "not_established"


@dataclass(frozen=True)
class DriveBCEventMatch:
    """An original source event and measured, qualified route relationship."""

    event: CityEvent
    classification: Literal["direct_overlap", "nearby"]
    distance_meters: float
    geometry_basis: GeometryBasis
    evidence: DriveBCEventEvidence


@dataclass(frozen=True)
class DriveBCExcludedEvent:
    """A usable geometry outside its configured relevance threshold."""

    event_id: str
    distance_meters: float
    geometry_basis: Literal["linestring_proximity", "point_proximity"]


@dataclass(frozen=True)
class DriveBCRelevanceResult:
    """Route-specific subset and diagnostics; source regional events stay untouched."""

    matches: tuple[DriveBCEventMatch, ...]
    unmatchable_events: tuple[UnmatchableEvent, ...]
    excluded_events: tuple[DriveBCExcludedEvent, ...]

    @property
    def direct_overlaps(self) -> tuple[DriveBCEventMatch, ...]:
        return tuple(match for match in self.matches if match.classification == "direct_overlap")

    @property
    def nearby_events(self) -> tuple[DriveBCEventMatch, ...]:
        return tuple(match for match in self.matches if match.classification == "nearby")

    @property
    def nearby_point_events(self) -> tuple[DriveBCEventMatch, ...]:
        return tuple(match for match in self.nearby_events if match.geometry_basis == "point_proximity")


def _identity_key(event: CityEvent) -> tuple[str, str, str]:
    return event.source_dataset_id, event.source_record_id, event.id


def _stable_event_key(event: CityEvent) -> str:
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _prepare_open511_geometry(geometry: object):
    if geometry is None:
        return None, "missing_geometry"
    if not isinstance(geometry, dict):
        return None, "invalid_structure"
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Point":
        if not _valid_position(coordinates):
            return None, "invalid_structure"
    elif kind == "LineString":
        if not isinstance(coordinates, list) or len(coordinates) < 2 or not all(
            _valid_position(position) for position in coordinates
        ):
            return None, "invalid_structure"
    else:
        return None, "invalid_structure"
    try:
        source = shape(geometry)
        if source.is_empty:
            return None, "empty_geometry"
        projected = transform(_PROJECTOR.transform, source)
    except (GEOSException, ProjError, TypeError, ValueError, OverflowError):
        return None, "projection_failure"
    if projected.is_empty:
        return None, "empty_geometry"
    if not projected.is_valid:
        return None, "invalid_topology"
    return projected, None


def _evidence(event: CityEvent) -> DriveBCEventEvidence:
    metadata = event.source_metadata
    raw_subtypes = metadata.get("event_subtypes")
    subtypes = tuple(raw_subtypes) if isinstance(raw_subtypes, list) else ()
    raw_roads = metadata.get("roads")
    roads = tuple(road for road in raw_roads if isinstance(road, dict)) if isinstance(raw_roads, list) else ()
    return DriveBCEventEvidence(
        event_type=event.event_type,
        status=event.status,
        severity=event.severity,
        event_subtypes=subtypes,
        roads=roads,
        schedule=metadata.get("schedule"),
        schedule_text=event.schedule_text,
    )


def match_drivebc_events(
    route_geometry: dict,
    events: list[CityEvent],
    *,
    linestring_nearby_distance_meters: float = DEFAULT_LINE_NEARBY_DISTANCE_METERS,
    point_nearby_distance_meters: float = DEFAULT_POINT_NEARBY_DISTANCE_METERS,
    nearby_limit: int = DEFAULT_NEARBY_LIMIT,
) -> DriveBCRelevanceResult:
    """Match Open511 Points and LineStrings to an explicitly selected route.

    LineString intersections are direct geographic overlaps. Points are always
    proximity evidence, even when their projected distance is zero. Only nearby
    findings are limited; distance calculations use the Phase 4 EPSG:26910
    projection. Source status, severity, schedule, and direction do not imply
    current route impact and never exclude a geographic match.
    """
    for name, value in (
        ("linestring_nearby_distance_meters", linestring_nearby_distance_meters),
        ("point_nearby_distance_meters", point_nearby_distance_meters),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number.")
    if isinstance(nearby_limit, bool) or not isinstance(nearby_limit, int) or nearby_limit < 0:
        raise ValueError("nearby_limit must be a non-negative integer.")

    route = _prepare_route(route_geometry)
    # Pick a canonical representative if a malformed collection repeats an
    # identity with differing payloads, so the output is input-order independent.
    unique: dict[tuple[str, str, str], CityEvent] = {}
    for event in events:
        identity = _identity_key(event)
        previous = unique.get(identity)
        if previous is None or _stable_event_key(event) < _stable_event_key(previous):
            unique[identity] = event

    direct: list[DriveBCEventMatch] = []
    nearby: list[DriveBCEventMatch] = []
    excluded: list[DriveBCExcludedEvent] = []
    unmatchable: list[UnmatchableEvent] = []
    for identity in sorted(unique):
        event = unique[identity]
        projected, reason = _prepare_open511_geometry(event.geometry)
        if projected is None:
            unmatchable.append(UnmatchableEvent(event_id=event.id, reason=reason))
            continue

        if isinstance(projected, LineString) and route.intersects(projected):
            direct.append(DriveBCEventMatch(event, "direct_overlap", 0.0, "linestring_intersection", _evidence(event)))
            continue
        distance = float(route.distance(projected))
        is_point = isinstance(projected, Point)
        threshold = point_nearby_distance_meters if is_point else linestring_nearby_distance_meters
        basis: Literal["linestring_proximity", "point_proximity"] = "point_proximity" if is_point else "linestring_proximity"
        if distance <= threshold:
            nearby.append(DriveBCEventMatch(event, "nearby", distance, basis, _evidence(event)))
        else:
            excluded.append(DriveBCExcludedEvent(event.id, distance, basis))

    direct.sort(key=lambda match: _identity_key(match.event))
    nearby.sort(key=lambda match: (match.distance_meters, _identity_key(match.event)))
    excluded.sort(key=lambda item: (item.distance_meters, item.event_id))
    unmatchable.sort(key=lambda item: item.event_id)
    return DriveBCRelevanceResult(tuple(direct + nearby[:nearby_limit]), tuple(unmatchable), tuple(excluded))
