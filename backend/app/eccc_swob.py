"""ECCC GeoMet SWOB measured station observations and regional caching."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SOURCE = "ECCC GeoMet/SWOB"
COLLECTION = "swob-realtime"
ITEMS_URL = f"https://api.weather.gc.ca/collections/{COLLECTION}/items"
ATTRIBUTION = (
    "Contains information licensed under the Open Government Licence – Canada. "
    "Source: Environment and Climate Change Canada GeoMet/SWOB."
)
DEFAULT_BBOX = "-123.30,49.15,-122.85,49.35"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "eccc_swob"
CACHE_TTL_SECONDS = 600
CACHE_SCHEMA_VERSION = 1
LOOKBACK = timedelta(hours=6)
PAGE_SIZE = 500
MAX_PAGES = 12
MAX_RECORDS = PAGE_SIZE * MAX_PAGES
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_REFRESH_SECONDS = 75.0
REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=4.0, read=10.0, write=3.0, pool=3.0)
FUTURE_SKEW = timedelta(minutes=5)
OBSERVATION_STALE_AFTER_SECONDS = 90 * 60
MAX_SELECTED_STATIONS = 3


class SwobError(Exception):
    """Sanitized source configuration or response validation failure."""


class _ExpectedFailure(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class MeasuredValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float
    unit: str
    source_field: str
    interval_seconds: int | None = None
    quality_code: int | None = None

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("measurement must be finite")
        return value

    @field_validator("unit", "source_field")
    @classmethod
    def nonempty_measurement_provenance(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("measurement unit and source field are required")
        return value


class PrecipitationAccumulation(MeasuredValue):
    interval_seconds: int


class StationObservation(BaseModel):
    """One real station reading; measurement semantics and source fields survive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = SOURCE
    station_id: str
    station_name: str | None = None
    station_identifiers: dict[str, str] = Field(default_factory=dict)
    source_record_id: str
    latitude: float | None = None
    longitude: float | None = None
    observed_at: datetime
    retrieved_at: datetime
    temperature: MeasuredValue | None = None
    relative_humidity: MeasuredValue | None = None
    precipitation: list[PrecipitationAccumulation] = Field(default_factory=list)
    wind_speed: MeasuredValue | None = None
    wind_direction: MeasuredValue | None = None
    snow_depth: MeasuredValue | None = None
    attribution: str = ATTRIBUTION

    @field_validator("observed_at", "retrieved_at")
    @classmethod
    def utc_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("latitude")
    @classmethod
    def valid_latitude(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or not -90 <= value <= 90):
            raise ValueError("latitude is outside valid bounds")
        return value

    @field_validator("longitude")
    @classmethod
    def valid_longitude(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or not -180 <= value <= 180):
            raise ValueError("longitude is outside valid bounds")
        return value

    @model_validator(mode="after")
    def valid_identity_and_position(self) -> StationObservation:
        if not self.station_id.strip() or not self.source_record_id.strip():
            raise ValueError("station and observation identities are required")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("station coordinates must both be present or absent")
        expected = (
            (self.temperature, "air_temp", "°C", None),
            (self.relative_humidity, "rel_hum", "%", None),
            (self.wind_speed, "avg_wnd_spd_10m_pst10mts", "km/h", 600),
            (self.wind_direction, "avg_wnd_dir_10m_pst10mts", "°", 600),
            (self.snow_depth, "snw_dpth", "cm", None),
        )
        for measured, source_field, unit, interval in expected:
            if measured is not None and (
                measured.source_field != source_field
                or measured.unit != unit
                or measured.interval_seconds != interval
            ):
                raise ValueError("measurement provenance does not match the SWOB field contract")
        for amount in self.precipitation:
            interval_by_field = {"pcpn_amt_pst10mts": 600, "pcpn_amt_pst1hr": 3600}
            if (
                amount.unit != "mm"
                or amount.source_field not in interval_by_field
                or amount.interval_seconds != interval_by_field[amount.source_field]
            ):
                raise ValueError("precipitation provenance does not match the SWOB field contract")
        return self


class SwobDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    records_received: int = Field(default=0, ge=0)
    records_normalized: int = Field(default=0, ge=0)
    records_skipped: int = Field(default=0, ge=0)
    duplicate_timestamps: int = Field(default=0, ge=0)
    station_count: int = Field(default=0, ge=0)
    skipped_reasons: dict[str, int] = Field(default_factory=dict)


class SwobSourceStatus(BaseModel):
    """SWOB availability and regional-cache state, independent of other sources."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = SOURCE
    dataset_id: str = COLLECTION
    success: bool
    available: bool
    fetched_at: datetime | None = None
    cache_hit: bool = False
    refreshed: bool = False
    stale: bool = False
    cache_age_seconds: int | None = None
    error: str | None = None
    records_received: int = 0
    records_normalized: int = 0
    records_skipped: int = 0

    @field_validator("fetched_at")
    @classmethod
    def fetched_time_is_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class RegionalSwobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observations: list[StationObservation] = Field(default_factory=list)
    diagnostics: SwobDiagnostics
    status: SwobSourceStatus
    bbox: str = DEFAULT_BBOX
    attribution: str = ATTRIBUTION


class SelectedStationObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation: StationObservation
    distance_meters: float
    observation_age_seconds: int
    observation_stale: bool
    cache_stale: bool
    useful_measurements: list[str]
    selection_reason: str


class _CacheEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    cache_identity: str
    fetched_at: datetime
    bbox: str
    observations: list[StationObservation]
    diagnostics: SwobDiagnostics

    @field_validator("fetched_at")
    @classmethod
    def fetched_time_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("cache timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


def _utc(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    return now.astimezone(timezone.utc)


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _bbox_parts(bbox: str) -> tuple[float, float, float, float]:
    try:
        values = tuple(float(part.strip()) for part in bbox.split(","))
    except (TypeError, ValueError):
        raise ValueError("bbox must contain four numeric coordinates") from None
    if len(values) != 4 or not all(math.isfinite(value) for value in values):
        raise ValueError("bbox must contain four finite coordinates")
    west, south, east, north = values
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox coordinates are outside valid bounds")
    return west, south, east, north


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _source_text(properties: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = properties.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            return str(value).strip()
    return None


def _coordinates(feature: dict[str, Any]) -> tuple[float | None, float | None]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None, None
    position = geometry.get("coordinates")
    if not isinstance(position, list) or len(position) < 2:
        return None, None
    lon, lat = position[0], position[1]
    if not _valid_number(lon) or not _valid_number(lat):
        return None, None
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None, None
    return float(lat), float(lon)


def _measurement(
    properties: dict[str, Any],
    field: str,
    expected_unit: str,
    *,
    interval_seconds: int | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> MeasuredValue | None:
    value = properties.get(field)
    unit = properties.get(f"{field}-uom")
    if value is None:
        return None
    if not _valid_number(value) or unit != expected_unit:
        return None
    number = float(value)
    if minimum is not None and number < minimum or maximum is not None and number > maximum:
        return None
    quality = properties.get(f"{field}-qa")
    quality_code = int(quality) if isinstance(quality, int) and not isinstance(quality, bool) else None
    if quality_code is not None and quality_code < 0:
        return None
    return MeasuredValue(
        value=number,
        unit=expected_unit,
        source_field=field,
        interval_seconds=interval_seconds,
        quality_code=quality_code,
    )


def normalize_feature(feature: Any, retrieved_at: datetime) -> tuple[StationObservation | None, str | None]:
    """Normalize one GeoJSON feature; return a reason code for isolated bad rows."""
    if not isinstance(feature, dict):
        return None, "invalid_feature"
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None, "missing_properties"
    observed_at = _parse_datetime(properties.get("date_tm-value"))
    if observed_at is None:
        return None, "invalid_timestamp"

    identifiers = {
        key.removesuffix("-value"): value
        for key in ("msc_id-value", "clim_id-value", "wmo_synop_id-value", "tc_id-value")
        if (value := _source_text(properties, key)) is not None
    }
    station_id = next(
        (identifiers[key] for key in ("msc_id", "clim_id", "wmo_synop_id", "tc_id") if key in identifiers),
        None,
    )
    if station_id is None:
        return None, "missing_station_identity"
    raw_id = feature.get("id") or properties.get("id") or properties.get("url")
    if not isinstance(raw_id, str) or not raw_id.strip():
        return None, "missing_observation_identity"

    latitude, longitude = _coordinates(feature)
    precipitation: list[PrecipitationAccumulation] = []
    for field, seconds in (("pcpn_amt_pst10mts", 600), ("pcpn_amt_pst1hr", 3600)):
        measurement = _measurement(properties, field, "mm", interval_seconds=seconds, minimum=0)
        if measurement is not None:
            precipitation.append(PrecipitationAccumulation(**measurement.model_dump()))

    return (
        StationObservation(
            station_id=station_id,
            station_name=_source_text(properties, "stn_nam-value"),
            station_identifiers=identifiers,
            source_record_id=raw_id.strip(),
            latitude=latitude,
            longitude=longitude,
            observed_at=observed_at,
            retrieved_at=_utc(retrieved_at),
            temperature=_measurement(properties, "air_temp", "°C"),
            relative_humidity=_measurement(properties, "rel_hum", "%", minimum=0, maximum=100),
            precipitation=precipitation,
            wind_speed=_measurement(properties, "avg_wnd_spd_10m_pst10mts", "km/h", interval_seconds=600, minimum=0),
            wind_direction=_measurement(properties, "avg_wnd_dir_10m_pst10mts", "°", interval_seconds=600, minimum=0, maximum=360),
            snow_depth=_measurement(properties, "snw_dpth", "cm", minimum=0),
        ),
        None,
    )


def parse_feature_collection(payload: Any, retrieved_at: datetime) -> tuple[list[StationObservation], SwobDiagnostics, int]:
    """Validate collection completeness and group latest valid reading per station."""
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise _ExpectedFailure("invalid_feature_collection")
    features = payload.get("features")
    matched, returned = payload.get("numberMatched"), payload.get("numberReturned")
    if (
        not isinstance(features, list)
        or not _nonnegative_int(matched)
        or not _nonnegative_int(returned)
        or returned != len(features)
        or returned > matched
    ):
        raise _ExpectedFailure("invalid_collection_metadata")
    if matched != returned:
        # A single response page is not a complete regional snapshot.
        raise _ExpectedFailure("incomplete_page")

    latest: dict[str, StationObservation] = {}
    reasons: dict[str, int] = {}
    duplicates = 0
    normalized_count = 0
    for feature in features:
        observation, reason = normalize_feature(feature, retrieved_at)
        if reason is not None:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue
        assert observation is not None
        normalized_count += 1
        current = latest.get(observation.station_id)
        if current is None or observation.observed_at > current.observed_at:
            latest[observation.station_id] = observation
        elif observation.observed_at == current.observed_at:
            duplicates += 1
            # Duplicate times are one reading, never field-merged. The source
            # record id provides stable tie handling across page order.
            if observation.source_record_id > current.source_record_id:
                latest[observation.station_id] = observation

    skipped = len(features) - normalized_count
    if features and (not latest or skipped / len(features) > 0.5):
        raise _ExpectedFailure("widespread_record_loss")
    diagnostics = SwobDiagnostics(
        records_received=len(features),
        records_normalized=normalized_count,
        records_skipped=skipped,
        duplicate_timestamps=duplicates,
        station_count=len(latest),
        skipped_reasons=reasons,
    )
    return sorted(latest.values(), key=lambda item: item.station_id), diagnostics, matched


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def _useful_measurements(observation: StationObservation) -> list[str]:
    available = []
    if observation.temperature is not None:
        available.append("temperature")
    if observation.relative_humidity is not None:
        available.append("relative_humidity")
    if observation.precipitation:
        available.append("precipitation_accumulation")
    if observation.wind_speed is not None or observation.wind_direction is not None:
        available.append("wind")
    if observation.snow_depth is not None:
        available.append("snow_depth")
    return available


def select_destination_observations(
    observations: list[StationObservation],
    *,
    latitude: float,
    longitude: float,
    now: datetime | None = None,
    cache_stale: bool = False,
    limit: int = MAX_SELECTED_STATIONS,
    preferred_measurements: list[str] | None = None,
) -> list[SelectedStationObservation]:
    """Return useful, recent destination-area stations with geodesic distances."""
    if (
        not _valid_number(latitude)
        or not _valid_number(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError("destination coordinates are invalid")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_SELECTED_STATIONS:
        raise ValueError(f"limit must be from 1 to {MAX_SELECTED_STATIONS}")
    at = _utc(now or datetime.now(timezone.utc))
    preferred = set(preferred_measurements or [])
    candidates: list[tuple[tuple[Any, ...], StationObservation, int, float, bool, list[str]]] = []
    for observation in observations:
        if observation.latitude is None or observation.longitude is None:
            continue
        age = int((at - observation.observed_at).total_seconds())
        if age < -int(FUTURE_SKEW.total_seconds()):
            continue
        age = max(0, age)
        useful = _useful_measurements(observation)
        if not useful:
            continue
        stale = age > OBSERVATION_STALE_AFTER_SECONDS
        distance = _haversine_meters(latitude, longitude, observation.latitude, observation.longitude)
        # Explicitly requested measurement types rank first. Without hints,
        # freshness ranks first; proximity then resolves equally fresh records.
        preference_coverage = len(preferred.intersection(useful))
        key = (
            -preference_coverage if preferred else 0,
            stale,
            age,
            distance,
            -len(useful),
            observation.station_id,
        )
        candidates.append((key, observation, age, distance, stale, useful))

    candidates.sort(key=lambda candidate: candidate[0])
    selected: list[SelectedStationObservation] = []
    represented: set[str] = set()
    remaining = candidates[:]
    while remaining and len(selected) < limit:
        # After the best overall station, prefer complementary measurements
        # before adding a redundant station with the same evidence.
        if selected:
            remaining.sort(
                key=lambda candidate: (
                    -len((set(candidate[5]) & preferred) - represented) if preferred else 0,
                    candidate[4],
                    candidate[1].observed_at > at,
                    -len(set(candidate[5]) - represented),
                    candidate[2],
                    candidate[3],
                    candidate[1].station_id,
                )
            )
        chosen = remaining.pop(0)
        _, observation, age, distance, stale, useful = chosen
        new_measurements = sorted(set(useful) - represented)
        represented.update(useful)
        reason = "recent nearby station with " + ", ".join(new_measurements or useful)
        if stale:
            reason += "; station observation is stale"
        if cache_stale:
            reason += "; regional source cache is stale"
        selected.append(
            SelectedStationObservation(
                observation=observation,
                distance_meters=round(distance, 1),
                observation_age_seconds=age,
                observation_stale=stale,
                cache_stale=cache_stale,
                useful_measurements=useful,
                selection_reason=reason,
            )
        )
    return selected


class EcccSwobClient:
    """Bounded regional GeoMet client with atomic validated cache and stale fallback."""

    def __init__(
        self,
        *,
        bbox: str | None = None,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl_seconds: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.bbox = bbox or os.getenv("SWOB_BBOX", DEFAULT_BBOX)
        _bbox_parts(self.bbox)
        configured_ttl = (
            ttl_seconds
            if ttl_seconds is not None
            else int(os.getenv("SWOB_CACHE_TTL_SECONDS", CACHE_TTL_SECONDS))
        )
        if not 600 <= configured_ttl <= 900:
            raise ValueError("SWOB cache TTL must be between 600 and 900 seconds")
        self.ttl_seconds = configured_ttl
        self.cache_dir = Path(cache_dir)
        self.now = now
        self._transport = transport
        self._lock = asyncio.Lock()
        identity_material = "".join(
            f"{len(part)}:{part}" for part in (SOURCE, COLLECTION, self.bbox, str(LOOKBACK.total_seconds()), str(PAGE_SIZE))
        )
        self.cache_identity = hashlib.sha256(identity_material.encode()).hexdigest()
        self.cache_path = self.cache_dir / f"{self.cache_identity}.json"

    def _read_cache(self) -> _CacheEnvelope | None:
        try:
            value = json.loads(self.cache_path.read_text(encoding="utf-8"))
            envelope = _CacheEnvelope.model_validate(value)
            if (
                envelope.schema_version != CACHE_SCHEMA_VERSION
                or envelope.cache_identity != self.cache_identity
                or envelope.bbox != self.bbox
                or envelope.fetched_at > _utc(self.now()) + FUTURE_SKEW
                or envelope.diagnostics.station_count != len(envelope.observations)
            ):
                return None
            return envelope
        except (OSError, ValueError, ValidationError, TypeError):
            return None

    def _write_cache(self, fetched_at: datetime, observations: list[StationObservation], diagnostics: SwobDiagnostics) -> None:
        envelope = _CacheEnvelope(
            schema_version=CACHE_SCHEMA_VERSION,
            cache_identity=self.cache_identity,
            fetched_at=fetched_at,
            bbox=self.bbox,
            observations=observations,
            diagnostics=diagnostics,
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.cache_dir, delete=False) as handle:
                temporary = handle.name
                handle.write(envelope.model_dump_json())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.cache_path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    async def _get_page(
        self, client: httpx.AsyncClient, *, start: datetime, end: datetime, offset: int
    ) -> dict[str, Any]:
        params = {
            "f": "json",
            "bbox": self.bbox,
            "datetime": (
                f"{start.isoformat(timespec='seconds').replace('+00:00', 'Z')}/"
                f"{end.isoformat(timespec='seconds').replace('+00:00', 'Z')}"
            ),
            "sortby": "date_tm-value",
            "offset": offset,
            "limit": PAGE_SIZE,
        }
        raw = bytearray()
        try:
            async with client.stream("GET", ITEMS_URL, params=params, follow_redirects=False) as response:
                if 300 <= response.status_code < 400:
                    raise _ExpectedFailure("redirect_rejected")
                if response.status_code >= 400:
                    raise _ExpectedFailure(f"http_{response.status_code}")
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_PAGE_BYTES:
                        raise _ExpectedFailure("response_size_limit")
        except httpx.TimeoutException:
            raise _ExpectedFailure("timeout") from None
        except httpx.RequestError:
            raise _ExpectedFailure("network_error") from None
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _ExpectedFailure("invalid_json") from None
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise _ExpectedFailure("invalid_feature_collection")
        return payload

    async def _fetch_snapshot(self) -> tuple[list[StationObservation], SwobDiagnostics]:
        at = _utc(self.now())
        start = at - LOOKBACK
        all_features: list[Any] = []
        total: int | None = None
        pages = 0
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            transport=self._transport,
            headers={"Accept": "application/geo+json, application/json", "User-Agent": "RouteLens-AI/1.0"},
        ) as client:
            while total is None or len(all_features) < total:
                if pages >= MAX_PAGES:
                    raise _ExpectedFailure("page_limit")
                payload = await self._get_page(client, start=start, end=at, offset=len(all_features))
                features = payload.get("features")
                matched, returned = payload.get("numberMatched"), payload.get("numberReturned")
                if (
                    not isinstance(features, list)
                    or not _nonnegative_int(matched)
                    or not _nonnegative_int(returned)
                    or returned != len(features)
                    or returned > PAGE_SIZE
                ):
                    raise _ExpectedFailure("invalid_page_metadata")
                if total is None:
                    total = matched
                    if total > MAX_RECORDS:
                        raise _ExpectedFailure("record_limit")
                elif total != matched:
                    raise _ExpectedFailure("unstable_page_count")
                if not features and len(all_features) < total:
                    raise _ExpectedFailure("truncated_pagination")
                all_features.extend(features)
                pages += 1
                if total == 0:
                    break

        combined = {"type": "FeatureCollection", "numberMatched": len(all_features), "numberReturned": len(all_features), "features": all_features}
        observations, diagnostics, _ = parse_feature_collection(combined, at)
        # Preserve regional response volume in diagnostics, not just latest rows.
        diagnostics = diagnostics.model_copy(update={"records_received": len(all_features)})
        return observations, diagnostics

    def _result(
        self,
        *,
        observations: list[StationObservation],
        diagnostics: SwobDiagnostics,
        fetched_at: datetime | None,
        success: bool,
        available: bool,
        cache_hit: bool = False,
        refreshed: bool = False,
        stale: bool = False,
        cache_age_seconds: int | None = None,
        error: str | None = None,
    ) -> RegionalSwobResult:
        status = SwobSourceStatus(
            success=success,
            available=available,
            fetched_at=fetched_at,
            cache_hit=cache_hit,
            refreshed=refreshed,
            stale=stale,
            cache_age_seconds=cache_age_seconds,
            error=error,
            records_received=diagnostics.records_received,
            records_normalized=diagnostics.records_normalized,
            records_skipped=diagnostics.records_skipped,
        )
        return RegionalSwobResult(observations=observations, diagnostics=diagnostics, status=status, bbox=self.bbox)

    async def fetch_regional_observations(self, *, force_refresh: bool = False) -> RegionalSwobResult:
        async with self._lock:
            at = _utc(self.now())
            cached = self._read_cache()
            cache_age = int(max(0, (at - cached.fetched_at).total_seconds())) if cached else None
            if cached and cache_age is not None and cache_age < self.ttl_seconds and not force_refresh:
                return self._result(
                    observations=cached.observations,
                    diagnostics=cached.diagnostics,
                    fetched_at=cached.fetched_at,
                    success=True,
                    available=True,
                    cache_hit=True,
                    cache_age_seconds=cache_age,
                )
            try:
                observations, diagnostics = await asyncio.wait_for(
                    self._fetch_snapshot(), timeout=MAX_REFRESH_SECONDS
                )
                fetched_at = _utc(self.now())
                self._write_cache(fetched_at, observations, diagnostics)
                return self._result(
                    observations=observations,
                    diagnostics=diagnostics,
                    fetched_at=fetched_at,
                    success=True,
                    available=True,
                    refreshed=True,
                    cache_age_seconds=0,
                )
            except _ExpectedFailure as exc:
                error = exc.code
            except TimeoutError:
                error = "refresh_time_limit"
            except OSError:
                error = "cache_write_failure"
            if cached is not None:
                return self._result(
                    observations=cached.observations,
                    diagnostics=cached.diagnostics,
                    fetched_at=cached.fetched_at,
                    success=False,
                    available=True,
                    stale=True,
                    cache_age_seconds=cache_age,
                    error=error,
                )
            return self._result(
                observations=[],
                diagnostics=SwobDiagnostics(),
                fetched_at=None,
                success=False,
                available=False,
                error=error,
            )


async def fetch_regional_observations(*, force_refresh: bool = False) -> RegionalSwobResult:
    """Convenience entry point for Assignment 6D callers."""
    return await EcccSwobClient().fetch_regional_observations(force_refresh=force_refresh)


def select_for_destination(
    result: RegionalSwobResult,
    *,
    latitude: float,
    longitude: float,
    now: datetime | None = None,
    limit: int = MAX_SELECTED_STATIONS,
    preferred_measurements: list[str] | None = None,
) -> list[SelectedStationObservation]:
    """Select stations from an already fetched regional result, without I/O."""
    return select_destination_observations(
        result.observations,
        latitude=latitude,
        longitude=longitude,
        now=now,
        cache_stale=result.status.stale,
        limit=limit,
        preferred_measurements=preferred_measurements,
    )
