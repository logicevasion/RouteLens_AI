"""Multi-source journey analysis for an explicitly selected driving route."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.detail_enrichment import DetailEnrichment, RoadAheadDetailEnricher
from app.drivebc_open511 import Open511Error, Open511Result, get_drivebc_open511_data
from app.drivebc_relevance import DriveBCEventEvidence, match_drivebc_events
from app.eccc_swob import (
    RegionalSwobResult,
    SelectedStationObservation,
    SwobDiagnostics,
    SwobError,
    SwobSourceStatus,
    fetch_regional_observations,
    select_for_destination,
)
from app.geography import validate_destination
from app.models import Location
from app.openweather import (
    CurrentWeatherResult,
    ForecastWeatherResult,
    OpenWeatherClient,
    OpenWeatherError,
    OpenWeatherResult,
    WeatherSourceStatus,
)
from app.road_ahead import (
    DATASETS,
    CityEvent,
    RoadAheadError,
    RoadAheadResult,
    SourceStatus,
    get_road_ahead_data,
)
from app.route_relevance import UnmatchableEvent, match_route_events

MAX_ROUTE_COORDINATES = 20_000
ANALYSIS_SOURCE_NAME = "DriveBC Open511"
ANALYSIS_DATASET_ID = "drivebc-open511-active-unavailable"


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
    """Legacy Road Ahead finding contract, including its selective enrichment."""

    model_config = ConfigDict(extra="forbid")

    event: CityEvent
    classification: Literal["direct_overlap", "nearby"]
    distance_meters: float
    detail: DetailEnrichment


class DriveBCAnalysisEvidence(BaseModel):
    """Source evidence and uncertainty qualified by the accepted 5B matcher."""

    model_config = ConfigDict(extra="forbid")

    event_type: str
    status: str | None
    severity: str | None
    event_subtypes: list[Any]
    roads: list[dict[str, Any]]
    schedule: Any = None
    schedule_text: str | None
    direction_assessment: Literal["undetermined"]
    temporal_applicability: Literal["unknown"]
    current_impact: Literal["not_established"]

    @classmethod
    def from_matcher(cls, evidence: DriveBCEventEvidence) -> DriveBCAnalysisEvidence:
        return cls(
            event_type=evidence.event_type,
            status=evidence.status,
            severity=evidence.severity,
            event_subtypes=list(evidence.event_subtypes),
            roads=list(evidence.roads),
            schedule=evidence.schedule,
            schedule_text=evidence.schedule_text,
            direction_assessment=evidence.direction_assessment,
            temporal_applicability=evidence.temporal_applicability,
            current_impact=evidence.current_impact,
        )


class DriveBCAnalysisFinding(BaseModel):
    """Regional journey match with no inapplicable Road Ahead detail object."""

    model_config = ConfigDict(extra="forbid")

    event: CityEvent
    classification: Literal["direct_overlap", "nearby"]
    distance_meters: float
    geometry_basis: Literal[
        "linestring_intersection", "linestring_proximity", "point_proximity"
    ]
    enrichment_applicability: Literal["not_applicable"] = "not_applicable"
    source_evidence: DriveBCAnalysisEvidence


class AnalysisUnmatchableEvent(BaseModel):
    """Matcher diagnostic scoped to a source dataset and original event identity."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    reason: Literal[
        "missing_geometry", "invalid_structure", "empty_geometry", "invalid_topology", "projection_failure"
    ]
    source: str
    dataset_id: str


class DestinationWeather(BaseModel):
    """Destination-only weather evidence, kept separate from road events."""

    model_config = ConfigDict(extra="forbid")

    openweather_current: CurrentWeatherResult
    openweather_forecast: ForecastWeatherResult
    eccc_status: SwobSourceStatus
    eccc_observations: list[SelectedStationObservation] = Field(default_factory=list)
    eccc_attribution: str


class JourneyAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trip: Trip
    status: Literal["available", "partial", "unavailable"]
    findings: list[AnalysisFinding]
    drivebc_findings: list[DriveBCAnalysisFinding] = Field(default_factory=list)
    regional_events: list[CityEvent] = Field(default_factory=list)
    unmatchable_events: list[AnalysisUnmatchableEvent]
    source_statuses: list[SourceStatus]
    destination_weather: DestinationWeather
    summary: str
    analyzed_at: datetime


def _unavailable_openweather() -> OpenWeatherResult:
    return OpenWeatherResult(
        current=CurrentWeatherResult(status=WeatherSourceStatus(
            dataset_id="onecall4_current", success=False, available=False,
            error="OpenWeather is temporarily unavailable.",
        )),
        forecast=ForecastWeatherResult(status=WeatherSourceStatus(
            dataset_id="onecall4_timeline_15min", success=False, available=False,
            error="OpenWeather is temporarily unavailable.",
        )),
    )


def _unavailable_swob() -> RegionalSwobResult:
    from app.eccc_swob import ATTRIBUTION

    return RegionalSwobResult(
        observations=[], diagnostics=SwobDiagnostics(),
        status=SwobSourceStatus(
            success=False, available=False, error="ECCC GeoMet/SWOB is temporarily unavailable."
        ),
        attribution=ATTRIBUTION,
    )


async def _destination_openweather(trip: Trip, evaluation_time: datetime) -> OpenWeatherResult:
    try:
        return await OpenWeatherClient().get_weather(
            trip.destination.latitude, trip.destination.longitude, evaluation_time=evaluation_time
        )
    except (OpenWeatherError, OSError, ValueError, TypeError, TimeoutError):
        # Provider/cache configuration failures stay inside the weather source boundary.
        return _unavailable_openweather()


async def _destination_swob(
    trip: Trip, evaluation_time: datetime
) -> tuple[RegionalSwobResult, list[SelectedStationObservation]]:
    try:
        regional = await fetch_regional_observations()
        selected = select_for_destination(
            regional,
            latitude=trip.destination.latitude,
            longitude=trip.destination.longitude,
            now=evaluation_time,
            limit=3,
            preferred_measurements=["precipitation"],
        )
        return regional, selected
    except (SwobError, OSError, ValueError, TypeError, TimeoutError):
        return _unavailable_swob(), []


def _unavailable_road_ahead() -> RoadAheadResult:
    return RoadAheadResult(
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


def _unavailable_open511() -> Open511Result:
    return Open511Result(
        events=[],
        source_status=SourceStatus(
            source=ANALYSIS_SOURCE_NAME,
            dataset_id=ANALYSIS_DATASET_ID,
            success=False,
            available=False,
            error="DriveBC Open511 is temporarily unavailable.",
        ),
    )


def _source_result(result: Any, fallback: Any, expected_errors: tuple[type[Exception], ...]) -> Any:
    if isinstance(result, BaseException):
        if isinstance(result, expected_errors):
            return fallback
        raise result
    return result


def summarize(
    statuses: list[SourceStatus],
    road_ahead_findings: list[AnalysisFinding],
    drivebc_findings: list[DriveBCAnalysisFinding],
) -> tuple[str, Literal["available", "partial", "unavailable"]]:
    available_count = sum(status.available for status in statuses)
    if available_count == 0:
        return "Road event analysis is unavailable because no source datasets could be retrieved.", "unavailable"

    overall: Literal["available", "partial", "unavailable"] = (
        "available" if available_count == len(statuses) else "partial"
    )
    coverage = ""
    if overall == "partial":
        coverage = f"Coverage is partial; {len(statuses) - available_count} of {len(statuses)} datasets are unavailable. "

    if not road_ahead_findings and not drivebc_findings:
        return coverage + "No route-relevant road events were identified from the available datasets.", overall

    parts: list[str] = []
    ra_direct = sum(item.classification == "direct_overlap" for item in road_ahead_findings)
    ra_nearby = len(road_ahead_findings) - ra_direct
    bc_direct = sum(item.classification == "direct_overlap" for item in drivebc_findings)
    bc_nearby = len(drivebc_findings) - bc_direct
    if ra_direct:
        parts.append(f"Road Ahead reports {ra_direct} event{'s' if ra_direct != 1 else ''} intersecting the selected route")
    if ra_nearby:
        parts.append(f"Road Ahead identifies {ra_nearby} additional event{'s' if ra_nearby != 1 else ''} nearby")
    if bc_direct:
        parts.append(f"DriveBC reports {bc_direct} regional LineString event{'s' if bc_direct != 1 else ''} intersecting the selected route")
    if bc_nearby:
        parts.append(f"DriveBC identifies {bc_nearby} regional event{'s' if bc_nearby != 1 else ''} nearby")
    return coverage + ". ".join(parts) + ".", overall


def _diagnostic(event: UnmatchableEvent, *, source: str, dataset_id: str) -> AnalysisUnmatchableEvent:
    return AnalysisUnmatchableEvent(
        event_id=event.event_id,
        reason=event.reason,
        source=source,
        dataset_id=dataset_id,
    )


async def analyze_journey(trip: Trip, *, enricher: RoadAheadDetailEnricher | None = None) -> JourneyAnalysis:
    """Acquire road and destination-weather evidence independently for the selected route."""
    destination_result = validate_destination(trip.destination)
    if not destination_result.valid:
        raise ValueError(destination_result.reason or "Destination is outside the supported area.")

    analysis_time = datetime.now(timezone.utc)
    road_result, open511_result, openweather_result, swob_result = await asyncio.gather(
        get_road_ahead_data(),
        get_drivebc_open511_data(),
        _destination_openweather(trip, analysis_time),
        _destination_swob(trip, analysis_time),
        return_exceptions=True,
    )
    road_data: RoadAheadResult = _source_result(
        road_result,
        _unavailable_road_ahead(),
        (RoadAheadError, OSError, TimeoutError),
    )
    open511_data: Open511Result = _source_result(
        open511_result,
        _unavailable_open511(),
        (Open511Error, OSError, TimeoutError),
    )
    weather_data: OpenWeatherResult = (
        _unavailable_openweather() if isinstance(openweather_result, BaseException) else openweather_result
    )
    if isinstance(swob_result, BaseException):
        regional_swob, selected_swob = _unavailable_swob(), []
    else:
        regional_swob, selected_swob = swob_result

    road_matches = match_route_events(trip.selected_route.geometry, road_data.events)
    drivebc_matches = match_drivebc_events(trip.selected_route.geometry, open511_data.events)

    detail_enricher = enricher or RoadAheadDetailEnricher()
    details = await detail_enricher.enrich_many([match.event for match in road_matches.matches])
    findings = [
        AnalysisFinding(
            event=match.event,
            classification=match.classification,
            distance_meters=match.distance_meters,
            detail=detail,
        )
        for match, detail in zip(road_matches.matches, details, strict=True)
    ]
    drivebc_findings = [
        DriveBCAnalysisFinding(
            event=match.event,
            classification=match.classification,
            distance_meters=match.distance_meters,
            geometry_basis=match.geometry_basis,
            source_evidence=DriveBCAnalysisEvidence.from_matcher(match.evidence),
        )
        for match in drivebc_matches.matches
    ]
    statuses = [*road_data.source_statuses, open511_data.source_status]
    unmatchable = [
        *(
            _diagnostic(event, source="City of Vancouver Road Ahead", dataset_id=event.event_id.partition(":")[0])
            for event in road_matches.unmatchable_events
        ),
        *(
            _diagnostic(event, source=ANALYSIS_SOURCE_NAME, dataset_id=open511_data.source_status.dataset_id)
            for event in drivebc_matches.unmatchable_events
        ),
    ]
    unmatchable.sort(key=lambda item: (item.source, item.dataset_id, item.event_id))
    summary, overall_status = summarize(statuses, findings, drivebc_findings)
    return JourneyAnalysis(
        trip=trip,
        status=overall_status,
        findings=findings,
        drivebc_findings=drivebc_findings,
        regional_events=open511_data.events,
        unmatchable_events=unmatchable,
        source_statuses=statuses,
        destination_weather=DestinationWeather(
            openweather_current=weather_data.current,
            openweather_forecast=weather_data.forecast,
            eccc_status=regional_swob.status,
            eccc_observations=selected_swob,
            eccc_attribution=regional_swob.attribution,
        ),
        summary=summary,
        analyzed_at=analysis_time,
    )
