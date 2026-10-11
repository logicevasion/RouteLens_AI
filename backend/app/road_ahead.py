"""Validated ingestion and local caching for the City of Vancouver Road Ahead feeds."""

from __future__ import annotations

import asyncio
import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

PORTAL_API = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets"
REQUEST_TIMEOUT_SECONDS = 20.0
PAGE_SIZE = 100
CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "road_ahead"
ATTRIBUTION = "City of Vancouver Open Data Portal — Open Government Licence – Vancouver"


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    dataset_id: str
    event_type: str
    title: str

    @property
    def url(self) -> str:
        return f"{PORTAL_API}/{self.dataset_id}/records"


DATASETS = (
    DatasetSpec("closures", "road-ahead-current-road-closures", "road_closure", "Road closure"),
    DatasetSpec(
        "construction",
        "road-ahead-projects-under-construction",
        "construction",
        "Project under construction",
    ),
)


class CityEvent(BaseModel):
    """RouteLens normalized event with source identity and retained provider metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    source_dataset_id: str
    source_record_id: str
    event_type: str
    title: str
    description: str | None = None
    geometry: dict[str, Any] | None = None
    latitude: float | None = None
    longitude: float | None = None
    severity: str | None = None
    status: str | None = None
    schedule_text: str | None = None
    restriction_text: str | None = None
    observed_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    relevance_reason: str | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    attribution: str = ATTRIBUTION


class SourceStatus(BaseModel):
    """Independent freshness and availability state for a Road Ahead dataset."""

    model_config = ConfigDict(extra="forbid")

    source: str
    dataset_id: str
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


class RoadAheadResult(BaseModel):
    """Combined independent results, retaining a status for each feed."""

    events: list[CityEvent]
    source_statuses: list[SourceStatus]


class RoadAheadError(Exception):
    """Sanitized source or response validation failure."""


class _InvalidPayload(RoadAheadError):
    pass


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_position(position: Any) -> bool:
    return (
        isinstance(position, list)
        and len(position) >= 2
        and _valid_number(position[0])
        and _valid_number(position[1])
        and -180 <= position[0] <= 180
        and -90 <= position[1] <= 90
        and all(_valid_number(value) for value in position[2:])
    )


def _validate_geometry(geometry: Any) -> dict[str, Any] | None:
    """Validate complete supported GeoJSON while preserving every coordinate."""
    if geometry is None:
        return None
    if not isinstance(geometry, dict):
        raise TypeError("geometry must be a GeoJSON object")
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "LineString":
        if not isinstance(coordinates, list) or len(coordinates) < 2 or not all(
            _validate_position(position) for position in coordinates
        ):
            raise ValueError("invalid LineString coordinates")
    elif kind == "MultiLineString":
        if not isinstance(coordinates, list) or not coordinates or any(
            not isinstance(line, list)
            or len(line) < 2
            or not all(_validate_position(position) for position in line)
            for line in coordinates
        ):
            raise ValueError("invalid MultiLineString coordinates")
    elif kind == "Polygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("invalid Polygon coordinates")
        for ring in coordinates:
            if (
                not isinstance(ring, list)
                or len(ring) < 4
                or not all(_validate_position(position) for position in ring)
                or ring[0][:2] != ring[-1][:2]
            ):
                raise ValueError("invalid Polygon ring")
    elif kind == "GeometryCollection":
        geometries = geometry.get("geometries")
        if not isinstance(geometries, list) or not geometries:
            raise ValueError("invalid GeometryCollection")
        for component in geometries:
            if component is None:
                raise ValueError("invalid GeometryCollection component")
            _validate_geometry(component)
    else:
        raise ValueError("unsupported geometry type")
    return geometry


def _source_id(record: dict[str, Any]) -> str | None:
    for key in ("recordid", "record_id", "id", "_id", "uuid"):
        value = record.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value).strip():
            return str(value).strip()
    # The API omits recordid unless explicitly selected. The official detail
    # link is a source-provided fallback identity when that field is absent.
    source_url = record.get("url_link")
    if isinstance(source_url, str):
        segments = [unquote(segment) for segment in urlparse(source_url).path.rstrip("/").split("/")]
        if len(segments) >= 2 and segments[-2] == "details" and segments[-1]:
            return segments[-1]
    return None


def _normalize_record(spec: DatasetSpec, record: Any) -> CityEvent | None:
    """Normalize a single record; individual field/geometry defects are isolated."""
    if not isinstance(record, dict):
        return None
    record_id = _source_id(record)
    if record_id is None:
        return None
    try:
        source_geometry = record.get("geom")
        if isinstance(source_geometry, dict) and source_geometry.get("type") == "Feature":
            source_geometry = source_geometry.get("geometry")
        geometry = _validate_geometry(source_geometry)
    except (TypeError, ValueError):
        return None

    point = record.get("geo_point_2d")
    latitude: float | None = None
    longitude: float | None = None
    if (
        (
            isinstance(point, list)
            and len(point) >= 2
            and _valid_number(point[0])
            and _valid_number(point[1])
            and -90 <= point[0] <= 90
            and -180 <= point[1] <= 180
        )
        or (
            isinstance(point, dict)
            and _valid_number(point.get("lat"))
            and _valid_number(point.get("lon"))
            and -90 <= point["lat"] <= 90
            and -180 <= point["lon"] <= 180
        )
    ):
        # This portal emits {lat, lon}; older fixtures used [latitude, longitude].
        if isinstance(point, dict):
            latitude, longitude = float(point["lat"]), float(point["lon"])
        else:
            latitude, longitude = float(point[0]), float(point[1])

    text_fields = ("project", "location", "street")
    values = {key: value.strip() for key in text_fields if isinstance((value := record.get(key)), str) and value.strip()}
    title = next((values.get(key) for key in text_fields if values.get(key)), spec.title)
    descriptions = [values[key] for key in ("location", "street") if values.get(key) and values[key] != title]
    source_url = record.get("url_link")
    if not isinstance(source_url, str) or urlparse(source_url).scheme not in {"http", "https"}:
        source_url = None
    metadata = {key: value for key, value in record.items() if key not in {"geom", "geo_point_2d"}}

    return CityEvent(
        id=f"{spec.dataset_id}:{record_id}",
        source="City of Vancouver Road Ahead",
        source_dataset_id=spec.dataset_id,
        source_record_id=record_id,
        event_type=spec.event_type,
        title=title,
        description="; ".join(dict.fromkeys(descriptions)) or None,
        geometry=geometry,
        latitude=latitude,
        longitude=longitude,
        source_url=source_url,
        source_metadata=metadata,
    )


def validate_page(payload: Any, *, expected_offset: int, requested_limit: int) -> tuple[int, list[dict[str, Any]]]:
    """Validate the City portal Explore API pagination envelope."""
    if not isinstance(payload, dict):
        raise _InvalidPayload("Road Ahead returned an invalid response structure.")
    total = payload.get("total_count")
    records = payload.get("results")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0 or not isinstance(records, list):
        raise _InvalidPayload("Road Ahead returned an invalid response structure.")
    if len(records) > requested_limit or (total > expected_offset and not records):
        raise _InvalidPayload("Road Ahead returned an incomplete paginated response.")
    if any(not isinstance(record, dict) for record in records):
        raise _InvalidPayload("Road Ahead returned an invalid record collection.")
    return total, records


def _cache_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _read_cache(path: Path) -> tuple[datetime, list[dict[str, Any]], int] | None:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        timestamp = _cache_timestamp(envelope.get("retrieved_at"))
        payload = envelope.get("payload")
        records = payload.get("records")
        total = payload.get("total_count")
        if timestamp is None or not isinstance(records, list) or isinstance(total, bool) or not isinstance(total, int):
            return None
        if len(records) != total or any(not isinstance(record, dict) for record in records):
            return None
        return timestamp, records, total
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _write_cache(path: Path, fetched_at: datetime, records: list[dict[str, Any]], total: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        {"retrieved_at": fetched_at.isoformat(), "payload": {"total_count": total, "records": records}},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    file_descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


class RoadAheadClient:
    """Fetch both independent City portal datasets and use a validated 24-hour cache."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self._transport = transport
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._locks = {spec.key: asyncio.Lock() for spec in DATASETS}

    async def _download(self, spec: DatasetSpec) -> tuple[list[dict[str, Any]], int]:
        records: list[dict[str, Any]] = []
        offset = 0
        total: int | None = None
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, transport=self._transport) as client:
                while total is None or offset < total:
                    response = await client.get(
                        spec.url,
                        params={"limit": PAGE_SIZE, "offset": offset, "select": "*,recordid"},
                    )
                    response.raise_for_status()
                    try:
                        payload = response.json()
                    except (ValueError, TypeError):
                        raise _InvalidPayload("Road Ahead returned malformed JSON.") from None
                    page_total, page_records = validate_page(
                        payload, expected_offset=offset, requested_limit=PAGE_SIZE
                    )
                    if total is None:
                        total = page_total
                    elif total != page_total:
                        raise _InvalidPayload("Road Ahead record count changed during pagination.")
                    records.extend(page_records)
                    offset += len(page_records)
                    if offset < total and len(page_records) < PAGE_SIZE:
                        raise _InvalidPayload("Road Ahead returned an incomplete paginated response.")
            if total is None or len(records) != total:
                raise _InvalidPayload("Road Ahead returned an incomplete dataset.")
            return records, total
        except _InvalidPayload:
            raise
        except httpx.TimeoutException:
            raise RoadAheadError("Road Ahead request timed out.") from None
        except (httpx.HTTPError, OSError):
            raise RoadAheadError("Road Ahead is temporarily unavailable.") from None

    async def _load_dataset(self, spec: DatasetSpec) -> tuple[list[CityEvent], SourceStatus]:
        async with self._locks[spec.key]:
            path = self.cache_dir / f"{spec.key}.json"
            cached = _read_cache(path)
            now = self._now().astimezone(timezone.utc)
            if cached:
                cached_at, cached_records, cached_total = cached
                try:
                    events, skipped = self._normalize_dataset(spec, cached_records, cached_total)
                except _InvalidPayload:
                    cached = None
                else:
                    age = max(0, int((now - cached_at).total_seconds()))
                    if age < CACHE_TTL_SECONDS:
                        return events, SourceStatus(
                            source="City of Vancouver Road Ahead",
                            dataset_id=spec.dataset_id,
                            success=True,
                            available=True,
                            fetched_at=cached_at,
                            cache_hit=True,
                            cache_age_seconds=age,
                            records_received=cached_total,
                            records_normalized=len(events),
                            records_skipped=skipped,
                        )

            try:
                records, total = await self._download(spec)
                events, skipped = self._normalize_dataset(spec, records, total)
                retrieved_at = self._now().astimezone(timezone.utc)
                _write_cache(path, retrieved_at, records, total)
                return events, SourceStatus(
                    source="City of Vancouver Road Ahead",
                    dataset_id=spec.dataset_id,
                    success=True,
                    available=True,
                    fetched_at=retrieved_at,
                    refreshed=True,
                    records_received=total,
                    records_normalized=len(events),
                    records_skipped=skipped,
                )
            except (RoadAheadError, OSError, ValueError) as error:
                if cached:
                    cached_at, cached_records, cached_total = cached
                    age = max(0, int((now - cached_at).total_seconds()))
                    try:
                        events, skipped = self._normalize_dataset(spec, cached_records, cached_total)
                    except _InvalidPayload:
                        pass
                    else:
                        return events, SourceStatus(
                            source="City of Vancouver Road Ahead",
                            dataset_id=spec.dataset_id,
                            success=False,
                            available=True,
                            fetched_at=cached_at,
                            cache_hit=True,
                            stale=True,
                            cache_age_seconds=age,
                            error=str(error),
                            records_received=cached_total,
                            records_normalized=len(events),
                            records_skipped=skipped,
                        )
                return [], SourceStatus(
                    source="City of Vancouver Road Ahead",
                    dataset_id=spec.dataset_id,
                    success=False,
                    available=False,
                    error=str(error),
                )

    @staticmethod
    def _normalize_dataset(
        spec: DatasetSpec, records: list[dict[str, Any]], total: int
    ) -> tuple[list[CityEvent], int]:
        events = [event for record in records if (event := _normalize_record(spec, record)) is not None]
        skipped = total - len(events)
        # Small isolated defects are tolerated; large/systemic record loss rejects the dataset.
        if total and (not events or skipped > max(1, math.floor(total * 0.2))):
            raise _InvalidPayload("Road Ahead records failed validation at an unsafe rate.")
        return events, skipped

    async def get_data(self) -> RoadAheadResult:
        """Return usable events with independent status for closures and construction."""
        results = await asyncio.gather(*(self._load_dataset(spec) for spec in DATASETS))
        return RoadAheadResult(
            events=[event for events, _ in results for event in events],
            source_statuses=[status for _, status in results],
        )


_default_client: RoadAheadClient | None = None


async def get_road_ahead_data() -> RoadAheadResult:
    """Application-facing callable; network retrieval occurs only when requested."""
    global _default_client
    if _default_client is None:
        _default_client = RoadAheadClient()
    return await _default_client.get_data()
