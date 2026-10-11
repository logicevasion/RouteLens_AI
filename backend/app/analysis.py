"""Synchronous Road Ahead journey-analysis orchestration."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.detail_enrichment import DetailEnrichment, RoadAheadDetailEnricher
from app.geography import validate_destination
from app.models import Location
from app.road_ahead import (
    CityEvent,
    RoadAheadError,
    RoadAheadResult,
    SourceStatus,
    get_road_ahead_data,
)
from app.route_relevance import UnmatchableEvent, match_route_events

MAX_ROUTE_COORDINATES = 20_000


class SelectedRoute(BaseModel):
    """Explicit route candidate context supplied by the user-facing client."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=100)
    geometry: dict
    distance_meters: float = Field(gt=0, le=2_000_000)
    duration_seconds: int = Field(gt=0, le=7 * 24 * 60 * 60)
    label: str | None = Field(default=None, max_length=100)

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, geometry: dict) -> dict:
        if set(geometry) != {"type", "coordinates"}:
            raise ValueError("Selected route geometry may contain only type and coordinates.")
        if geometry.get("type") != "LineString" or not isinstance(geometry.get("coordinates"), list):
            raise ValueError("Selected route geometry must be a GeoJSON LineString.")
        coordinates = geometry["coordinates"]
        if not 2 <= len(coordinates) <= MAX_ROUTE_COORDINATES:
            raise ValueError(f"Selected route must contain 2 to {MAX_ROUTE_COORDINATES} coordinates.")
        positions: list[tuple[float, float]] = []
        for position in coordinates:
            if not isinstance(position, list) or len(position) not in {2, 3}:
                raise ValueError("Selected route contains an invalid coordinate.")
            lon, lat = position[0], position[1]
            if (
                isinstance(lon, bool)
                or isinstance(lat, bool)
                or not isinstance(lon, (int, float))
                or not isinstance(lat, (int, float))
                or not math.isfinite(lon)
                or not math.isfinite(lat)
                or not -180 <= lon <= 180
                or not -90 <= lat <= 90
                or (len(position) == 3 and (
                    isinstance(position[2], bool)
                    or not isinstance(position[2], (int, float))
                    or not math.isfinite(position[2])
                ))
            ):
                raise ValueError("Selected route contains an out-of-range coordinate.")
            positions.append((float(lon), float(lat)))
        if len(set(positions)) < 2:
            raise ValueError("Selected route geometry must have nonzero length.")
        if len(json.dumps(geometry, separators=(",", ":"))) > 1_000_000:
            raise ValueError("Selected route geometry exceeds the supported request size.")
        return geometry

    @field_validator("label")
    @classmethod
    def strip_label(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class Trip(BaseModel):
    """Canonical driving journey and its explicitly selected route."""

    model_config = ConfigDict(extra="forbid")

    origin: Location
    destination: Location
    mode: Literal["drive"]
    selected_route: SelectedRoute


class AnalysisFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: CityEvent
    classification: Literal["direct_overlap", "nearby"]
    distance_meters: float
    detail: DetailEnrichment


class JourneyAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip: Trip
    status: Literal["available", "partial", "unavailable"]
    findings: list[AnalysisFinding]
    unmatchable_events: list[UnmatchableEvent]
    source_statuses: list[SourceStatus]
    summary: str
    analyzed_at: datetime


def summarize(statuses: list[SourceStatus], direct_count: int, nearby_count: int) -> tuple[str, Literal["available", "partial", "unavailable"]]:
    available_count = sum(status.available for status in statuses)
    if available_count == 0:
        return "Road Ahead data is unavailable for this analysis.", "unavailable"

    overall: Literal["available", "partial", "unavailable"] = (
        "available" if available_count == len(statuses) else "partial"
    )
    prefix = ""
    if overall == "partial":
        prefix = "Road Ahead results are partially available; one dataset could not be retrieved. "
    if direct_count == 0 and nearby_count == 0:
        return prefix + "No Road Ahead events were identified near the selected route in the available datasets.", overall
    parts: list[str] = []
    if direct_count:
        parts.append(f"{direct_count} Road Ahead event{'s' if direct_count != 1 else ''} intersect the selected route")
    if nearby_count:
        parts.append(f"{nearby_count} additional event{'s' if nearby_count != 1 else ''} {'are' if nearby_count != 1 else 'is'} nearby")
    return prefix + ". ".join(parts) + ".", overall


async def analyze_journey(trip: Trip, *, enricher: RoadAheadDetailEnricher | None = None) -> JourneyAnalysis:
    """Load accepted Road Ahead data, match the selected geometry, then enrich matches."""
    destination_result = validate_destination(trip.destination)
    if not destination_result.valid:
        raise ValueError(destination_result.reason or "Destination is outside the supported area.")
    try:
        road_data: RoadAheadResult = await get_road_ahead_data()
    except (RoadAheadError, OSError):
        # The source adapter normally isolates per-dataset failures. This fallback
        # covers unexpected adapter-level outages without leaking exception text.
        from app.road_ahead import DATASETS

        road_data = RoadAheadResult(
            events=[],
            source_statuses=[
                SourceStatus(
                    source="City of Vancouver Road Ahead",
                    dataset_id=dataset.dataset_id,
                    success=False,
                    available=False,
                    error="Road Ahead is temporarily unavailable.",
                )
                for dataset in DATASETS
            ],
        )

    matches = match_route_events(trip.selected_route.geometry, road_data.events)

    detail_enricher = enricher or RoadAheadDetailEnricher()
    details = await detail_enricher.enrich_many([match.event for match in matches.matches])
    findings = [
        AnalysisFinding(
            event=match.event,
            classification=match.classification,
            distance_meters=match.distance_meters,
            detail=detail,
        )
        for match, detail in zip(matches.matches, details, strict=True)
    ]
    direct_count = sum(finding.classification == "direct_overlap" for finding in findings)
    nearby_count = len(findings) - direct_count
    summary, overall_status = summarize(road_data.source_statuses, direct_count, nearby_count)
    return JourneyAnalysis(
        trip=trip,
        status=overall_status,
        findings=findings,
        unmatchable_events=list(matches.unmatchable_events),
        source_statuses=road_data.source_statuses,
        summary=summary,
        analyzed_at=datetime.now(timezone.utc),
    )
