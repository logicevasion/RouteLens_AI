"""Bounded, source-specific request and response contracts for journey briefings."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

Availability = Literal["available", "empty", "partial", "unavailable", "pending", "failed", "unknown"]
RoadClass = Literal["direct_overlap", "nearby"]
RoadBasis = Literal["linestring_intersection", "linestring_proximity", "point_proximity"]
WeatherConditionCode = Literal["clear", "clouds", "rain", "drizzle", "thunderstorm", "snow", "mist", "fog", "atmosphere", "unknown"]
CameraObservationStatus = Literal["available", "partial", "insufficient_evidence", "unavailable", "error", "pending", "unknown"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def reject_embedded_camera_material(self):
        def inspect(value) -> None:
            if isinstance(value, str) and any(marker in value.casefold() for marker in ("data:image/", "http://", "https://")):
                raise ValueError("URLs and embedded image data are not accepted")
            if isinstance(value, BaseModel):
                for nested in value.__dict__.values():
                    inspect(nested)
            elif isinstance(value, (list, tuple)):
                for nested in value:
                    inspect(nested)

        for value in self.__dict__.values():
            inspect(value)
        return self


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


class Place(StrictModel):
    name: StrictStr = Field(min_length=1, max_length=120)
    latitude: StrictFloat = Field(ge=-90, le=90)
    longitude: StrictFloat = Field(ge=-180, le=180)


class RouteContext(StrictModel):
    candidate_id: StrictStr = Field(min_length=1, max_length=128)
    label: StrictStr | None = Field(max_length=120)
    distance_meters: StrictFloat = Field(gt=0, le=2_000_000)


class SourceStatus(StrictModel):
    source: StrictStr = Field(min_length=1, max_length=120)
    dataset_id: StrictStr = Field(min_length=1, max_length=120)
    success: StrictBool
    available: StrictBool
    fetched_at: datetime | None
    stale: StrictBool
    cache_stale: StrictBool | None

    @field_validator("fetched_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None


def _status_succeeded(status: SourceStatus | None) -> bool:
    return bool(status and (status.success or status.available))


class RoadFinding(StrictModel):
    source_id: StrictStr = Field(min_length=1, max_length=125, pattern=r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$")
    event_type: StrictStr | None = Field(default=None, max_length=80)
    title: StrictStr = Field(min_length=1, max_length=160)
    description: StrictStr | None = Field(max_length=320)
    classification: RoadClass
    distance_meters: StrictFloat = Field(ge=0, le=2_000_000)
    location: StrictStr | None = Field(max_length=160)
    severity: StrictStr | None = Field(max_length=80)
    status: StrictStr | None = Field(max_length=80)
    schedule_text: StrictStr | None = Field(max_length=320)
    restriction_text: StrictStr | None = Field(max_length=320)
    observed_at: datetime | None
    updated_at: datetime | None
    direction_assessment: StrictStr | None = Field(max_length=80)
    temporal_applicability: StrictStr | None = Field(max_length=80)
    current_impact: StrictStr | None = Field(max_length=80)
    geometry_basis: RoadBasis | None

    @field_validator("observed_at", "updated_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None


class RoadAheadSection(StrictModel):
    availability: Availability
    statuses: list[SourceStatus] = Field(max_length=8)
    findings: list[RoadFinding] = Field(max_length=12)
    omitted_count: StrictInt = Field(ge=0, le=100_000)

    @model_validator(mode="after")
    def availability_matches_status(self) -> RoadAheadSection:
        statuses_ok = bool(self.statuses) and all(item.success or item.available for item in self.statuses)
        if self.availability == "empty" and not statuses_ok:
            raise ValueError("empty Road Ahead results require successful source status")
        if self.availability == "available" and (not self.findings or not statuses_ok):
            raise ValueError("available Road Ahead results require findings and successful source status")
        return self


class DriveBCSection(StrictModel):
    availability: Availability
    status: SourceStatus | None
    findings: list[RoadFinding] = Field(max_length=12)
    omitted_count: StrictInt = Field(ge=0, le=100_000)

    @model_validator(mode="after")
    def availability_matches_status(self) -> DriveBCSection:
        if self.availability == "empty" and not _status_succeeded(self.status):
            raise ValueError("empty DriveBC results require successful source status")
        if self.availability == "available" and (not self.findings or not _status_succeeded(self.status)):
            raise ValueError("available DriveBC results require findings and successful source status")
        return self


class Measurement(StrictModel):
    value: StrictFloat = Field(ge=-100_000, le=100_000)
    unit: StrictStr = Field(min_length=1, max_length=24)


class Condition(StrictModel):
    code: StrictInt | None = Field(ge=0, le=10_000)
    group: WeatherConditionCode | None
    description: StrictStr | None = Field(max_length=120)


class CurrentObservation(StrictModel):
    source: Literal["OpenWeather"]
    product: Literal["onecall4_current"]
    observed_at: datetime
    fetched_at: datetime
    condition: Condition | None
    temperature_c: Measurement | None
    feels_like_c: Measurement | None
    humidity_pct: StrictFloat | None = Field(ge=0, le=100)
    wind_speed_m_s: StrictFloat | None = Field(ge=0, le=150)
    wind_direction_deg: StrictFloat | None = Field(ge=0, le=360)
    wind_gust_m_s: StrictFloat | None = Field(ge=0, le=150)
    visibility_m: StrictFloat | None = Field(ge=0, le=200_000)
    rain_1h_mm: StrictFloat | None = Field(ge=0, le=10_000)
    snow_1h_mm: StrictFloat | None = Field(ge=0, le=10_000)

    @field_validator("observed_at", "fetched_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime) -> datetime:
        return _aware(value)


class OpenWeatherCurrent(StrictModel):
    availability: Availability
    status: SourceStatus | None
    observation: CurrentObservation | None

    @model_validator(mode="after")
    def availability_matches_status(self) -> OpenWeatherCurrent:
        if self.availability == "empty" and not _status_succeeded(self.status):
            raise ValueError("empty current weather requires successful source status")
        if self.availability == "available" and (self.observation is None or not _status_succeeded(self.status)):
            raise ValueError("available current weather requires an observation and successful source status")
        return self


class ForecastInterval(StrictModel):
    source: Literal["OpenWeather"]
    product: Literal["onecall4_timeline_15min"]
    forecast_at: datetime
    fetched_at: datetime
    condition: Condition | None
    precipitation_probability_pct: StrictFloat | None = Field(ge=0, le=100)
    temperature_c: Measurement | None
    feels_like_c: Measurement | None
    humidity_pct: StrictFloat | None = Field(ge=0, le=100)
    wind_speed_m_s: StrictFloat | None = Field(ge=0, le=150)
    wind_direction_deg: StrictFloat | None = Field(ge=0, le=360)
    wind_gust_m_s: StrictFloat | None = Field(ge=0, le=150)
    visibility_m: StrictFloat | None = Field(ge=0, le=200_000)
    rain_1h_mm: StrictFloat | None = Field(ge=0, le=10_000)
    rain_3h_mm: StrictFloat | None = Field(ge=0, le=10_000)
    snow_1h_mm: StrictFloat | None = Field(ge=0, le=10_000)
    snow_3h_mm: StrictFloat | None = Field(ge=0, le=10_000)

    @field_validator("forecast_at", "fetched_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime) -> datetime:
        return _aware(value)


class ForecastCoverage(StrictModel):
    continuous: StrictBool
    expected_interval_count: StrictInt = Field(ge=0, le=100)
    returned_interval_count: StrictInt = Field(ge=0, le=100)
    first_interval_at: datetime | None
    last_interval_at: datetime | None

    @field_validator("first_interval_at", "last_interval_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None


class OpenWeatherForecast(StrictModel):
    availability: Availability
    status: SourceStatus | None
    coverage: ForecastCoverage | None
    intervals: list[ForecastInterval] = Field(max_length=4)
    omitted_count: StrictInt = Field(ge=0, le=100_000)

    @model_validator(mode="after")
    def availability_matches_status(self) -> OpenWeatherForecast:
        if self.availability == "empty" and not _status_succeeded(self.status):
            raise ValueError("empty forecast requires successful source status")
        if self.availability == "available" and (not self.intervals or not _status_succeeded(self.status)):
            raise ValueError("available forecast requires intervals and successful source status")
        return self


class StationMeasurement(StrictModel):
    name: Literal["temperature", "relative_humidity", "precipitation", "wind_speed", "wind_direction", "snow_depth"]
    value: StrictFloat = Field(ge=-100_000, le=100_000)
    unit: StrictStr = Field(min_length=1, max_length=24)
    source_field: StrictStr = Field(min_length=1, max_length=120)
    interval_seconds: StrictInt | None = Field(ge=0, le=31_536_000)
    quality_code: StrictInt | None = Field(ge=-100_000, le=100_000)


class SwobObservation(StrictModel):
    station_id: StrictStr = Field(min_length=1, max_length=88, pattern=r"^[A-Za-z0-9_.-]+$")
    station_name: StrictStr | None = Field(max_length=120)
    distance_meters: StrictFloat = Field(ge=0, le=2_000_000)
    observed_at: datetime
    retrieved_at: datetime
    observation_age_seconds: StrictInt = Field(ge=0, le=31_536_000)
    observation_stale: StrictBool
    cache_stale: StrictBool
    measurements: list[StationMeasurement] = Field(max_length=12)

    @field_validator("observed_at", "retrieved_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime) -> datetime:
        return _aware(value)


class EcccSwob(StrictModel):
    availability: Availability
    status: SourceStatus | None
    attribution: StrictStr | None = Field(max_length=180)
    observations: list[SwobObservation] = Field(max_length=3)
    omitted_count: StrictInt = Field(ge=0, le=100_000)

    @model_validator(mode="after")
    def availability_matches_status(self) -> EcccSwob:
        if self.availability == "empty" and not _status_succeeded(self.status):
            raise ValueError("empty SWOB results require successful source status")
        if self.availability == "available" and (not self.observations or not _status_succeeded(self.status)):
            raise ValueError("available SWOB results require observations and successful source status")
        return self


class CameraView(StrictModel):
    view_id: StrictStr = Field(min_length=1, max_length=128, pattern=r"^(?:view:)?[A-Za-z0-9_.-]+$")
    direction_label: StrictStr | None = Field(max_length=80)
    retrieved_at: datetime
    source_capture_at: datetime | None
    road_surface: Literal["dry_looking", "wet_looking", "snow_or_ice_looking", "unclear", "not_observable"]
    visibility: Literal["adequate", "limited", "obscured", "not_observable"]
    vehicle_activity: Literal["none_visible", "some_visible", "queue_apparent", "unclear", "not_observable"]
    conditions: list[Literal["visible_precipitation", "fog_or_haze", "glare", "obstruction", "image_quality_limited"]] = Field(max_length=5)
    uncertainty: Literal["low", "moderate", "high"]
    note: StrictStr | None = Field(max_length=160)

    @field_validator("retrieved_at", "source_capture_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None


class CameraObservation(StrictModel):
    status: CameraObservationStatus
    intersection_name: StrictStr | None = Field(max_length=120)
    street_names: list[StrictStr] = Field(max_length=2)
    distance_from_destination_meters: StrictFloat | None = Field(ge=0, le=2_000_000)
    source_name: StrictStr | None = Field(max_length=120)
    direction_view: CameraView | None
    summary: StrictStr | None = Field(max_length=240)
    summary_evidence_view_ids: list[StrictStr] = Field(max_length=1)

    @model_validator(mode="after")
    def single_direction_only(self) -> CameraObservation:
        if self.status in ("available", "partial") and self.direction_view is None:
            raise ValueError("camera observation requires one validated directional view")
        if self.status not in ("available", "partial") and (self.direction_view is not None or self.summary is not None):
            raise ValueError("unusable camera status cannot carry a visual interpretation")
        if self.direction_view is not None and self.intersection_name is None:
            raise ValueError("camera view requires intersection provenance")
        expected = [self.direction_view.view_id] if self.direction_view else []
        if self.summary_evidence_view_ids != (expected if self.summary else []):
            raise ValueError("camera summary references must identify its directional view")
        return self


class CameraVision(StrictModel):
    availability: Availability
    observation_status: CameraObservationStatus
    observation: CameraObservation | None

    @model_validator(mode="after")
    def status_consistency(self) -> CameraVision:
        if self.observation is not None and self.observation.status != self.observation_status:
            raise ValueError("camera status does not match its observation")
        if self.observation_status == "pending" and self.observation is not None:
            raise ValueError("pending camera cannot contain an observation")
        if self.observation_status in ("available", "partial") and self.observation is None:
            raise ValueError("usable camera status requires its validated observation")
        expected = {"available": "available", "partial": "partial", "empty": "insufficient_evidence",
                    "unavailable": "unavailable", "failed": "error", "pending": "pending", "unknown": "unknown"}
        if self.availability in expected and self.observation_status != expected[self.availability]:
            raise ValueError("camera availability is inconsistent with observation status")
        return self


class JourneyContext(StrictModel):
    mode: Literal["drive"]
    origin: Place
    destination: Place
    route: RouteContext


class BriefingSources(StrictModel):
    road_ahead: RoadAheadSection
    drivebc_open511: DriveBCSection
    openweather_current: OpenWeatherCurrent
    openweather_forecast: OpenWeatherForecast
    eccc_swob: EcccSwob
    camera_vision: CameraVision


class BriefingEvidenceRequestV1(StrictModel):
    request_schema_version: Literal["journey-briefing-request-v1"]
    bundle_schema_version: Literal["journey-evidence-v1"]
    attempt_id: StrictInt = Field(ge=0, le=2_147_483_647)
    assembled_at: datetime
    analyzed_at: datetime
    analysis_status: Literal["success"]
    journey: JourneyContext
    sources: BriefingSources

    @field_validator("assembled_at", "analyzed_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def semantic_consistency(self) -> BriefingEvidenceRequestV1:
        if self.assembled_at < self.analyzed_at:
            raise ValueError("evidence assembly cannot predate successful analysis")
        ids: list[str] = []
        ids.extend(f"ra-{item.source_id}" for item in self.sources.road_ahead.findings)
        ids.extend(f"bc-{item.source_id}" for item in self.sources.drivebc_open511.findings)
        if self.sources.openweather_current.observation:
            ids.append("ow-current")
        ids.extend(f"ow-fc-{item.forecast_at.isoformat()}" for item in self.sources.openweather_forecast.intervals)
        ids.extend(f"swob-{item.station_id}-{item.observed_at.isoformat()}" for item in self.sources.eccc_swob.observations)
        if self.sources.camera_vision.observation and self.sources.camera_vision.observation.direction_view:
            ids.append("camera-view-1")
        if len(ids) != len(set(ids)):
            raise ValueError("evidence identities must be unique")
        for section, count in (
            (self.sources.road_ahead, len(self.sources.road_ahead.findings)),
            (self.sources.drivebc_open511, len(self.sources.drivebc_open511.findings)),
            (self.sources.openweather_forecast, len(self.sources.openweather_forecast.intervals)),
            (self.sources.eccc_swob, len(self.sources.eccc_swob.observations)),
        ):
            if section.availability == "empty" and count:
                raise ValueError("empty source section cannot contain records")
            if section.availability == "available" and not count:
                raise ValueError("available source section must contain records")
        if self.sources.openweather_current.availability == "empty" and self.sources.openweather_current.observation:
            raise ValueError("empty source section cannot contain an observation")
        if self.sources.openweather_current.availability == "available" and not self.sources.openweather_current.observation:
            raise ValueError("available source section must contain an observation")
        return self

    def allowed_evidence_refs(self) -> set[str]:
        refs = {f"ra-{item.source_id}" for item in self.sources.road_ahead.findings}
        refs.update(f"bc-{item.source_id}" for item in self.sources.drivebc_open511.findings)
        refs.update(f"ow-fc-{item.forecast_at.isoformat()}" for item in self.sources.openweather_forecast.intervals)
        refs.update(f"swob-{item.station_id}-{item.observed_at.isoformat()}" for item in self.sources.eccc_swob.observations)
        if self.sources.openweather_current.observation:
            refs.add("ow-current")
        if self.sources.camera_vision.observation and self.sources.camera_vision.observation.direction_view:
            refs.add("camera-view-1")
        if self.sources.road_ahead.availability in ("available", "empty", "partial"):
            refs.add("ra-status")
        if self.sources.drivebc_open511.availability in ("available", "empty", "partial"):
            refs.add("bc-status")
        if self.sources.openweather_current.availability in ("available", "empty", "partial"):
            refs.add("ow-current-status")
        if self.sources.openweather_forecast.availability in ("available", "empty", "partial"):
            refs.add("ow-forecast-status")
        if self.sources.eccc_swob.availability in ("available", "empty", "partial"):
            refs.add("swob-status")
        if self.sources.camera_vision.availability in ("available", "empty", "partial"):
            refs.add("camera-status")
        return refs

    def has_usable_evidence(self) -> bool:
        for section in self.sources.model_dump().values():
            if section["availability"] in ("available", "empty", "partial"):
                return True
        return False


class ModelBriefingOutputV1(BaseModel):
    """Minimal provider output; topic identity and references are backend-owned."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    status: Literal["available", "insufficient_evidence"]
    overview: StrictStr = Field(max_length=360)
    camera_text: StrictStr = Field(max_length=300)
    weather_text: StrictStr = Field(max_length=300)
    construction_text: StrictStr = Field(max_length=300)

    @field_validator("overview", "camera_text", "weather_text", "construction_text")
    @classmethod
    def reject_external_material(cls, value: str) -> str:
        if any(marker in value.casefold() for marker in ("data:image/", "http://", "https://")):
            raise ValueError("URLs and embedded image data are not accepted")
        return value


class BriefingTopicV1(StrictModel):
    category: Literal["camera", "weather", "road"]
    text: StrictStr = Field(min_length=1, max_length=300)
    evidence_refs: list[StrictStr] = Field(max_length=3)


class BriefingUsage(StrictModel):
    input_tokens: StrictInt | None = Field(ge=0, le=10_000_000)
    output_tokens: StrictInt | None = Field(ge=0, le=1024)
    total_tokens: StrictInt | None = Field(ge=0, le=10_000_000)
    cost_usd: float | None = Field(ge=0, le=100)
    latency_ms: StrictInt = Field(ge=0, le=30_000)


class BriefingResultV1(StrictModel):
    contract_version: Literal["journey-briefing-v1"] = "journey-briefing-v1"
    prompt_version: Literal["journey-briefing-prompt-v1"] = "journey-briefing-prompt-v1"
    status: Literal["available", "insufficient_evidence", "unavailable", "error"]
    failure_code: Literal["configuration_missing", "budget_exhausted", "timeout", "provider_unavailable", "invalid_model_output", "duplicate_attempt", "error"] | None
    generated_at: datetime
    attempt_id: StrictInt = Field(ge=0)
    origin_name: StrictStr = Field(max_length=120)
    destination_name: StrictStr = Field(max_length=120)
    requested_model: Literal["google/gemma-4-31b-it"] = "google/gemma-4-31b-it"
    returned_model: StrictStr | None = Field(max_length=120)
    provider: StrictStr | None = Field(max_length=80)
    overview: StrictStr = Field(max_length=360)
    overview_evidence_refs: list[StrictStr] = Field(max_length=4)
    highlights: list[BriefingTopicV1] = Field(max_length=3)
    limitations: list[StrictStr] = Field(max_length=12)
    usage: BriefingUsage

    @field_validator("generated_at")
    @classmethod
    def timestamp_timezone(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def fixed_topic_contract(self) -> BriefingResultV1:
        if self.status == "available":
            expected_categories = ["camera", "weather", "road"]
            if [item.category for item in self.highlights] != expected_categories:
                raise ValueError("available briefing requires the fixed topic order")
            placeholders = {
                "camera": {
                    "Camera interpretation was pending and was not included.",
                    "Camera interpretation is stale and was not used for this briefing.",
                    "Camera interpretation unavailable for this journey.",
                },
                "weather": {"Destination weather data unavailable."},
                "road": {
                    "Road Ahead construction evidence is unavailable for this journey.",
                    "No qualifying construction report is available in the current Road Ahead evidence.",
                },
            }
            for item in self.highlights:
                if len(item.evidence_refs) != len(set(item.evidence_refs)):
                    raise ValueError("topic evidence references must be unique")
                if not item.evidence_refs and item.text not in placeholders[item.category]:
                    raise ValueError("empty topic references are reserved for fixed availability messages")
                if item.evidence_refs and item.text in placeholders[item.category]:
                    raise ValueError("availability messages cannot contain evidence references")
        elif self.highlights or self.overview or self.overview_evidence_refs:
            raise ValueError("non-available briefing must not contain generated prose")
        return self
