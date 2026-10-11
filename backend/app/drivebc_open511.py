"""Regional DriveBC Open511 ingestion with validated caching and stale fallback."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx

from app.road_ahead import CityEvent, SourceStatus

API_BASE = "https://api.open511.gov.bc.ca"
EVENTS_URL = f"{API_BASE}/events"
SOURCE_NAME = "DriveBC Open511"
ATTRIBUTION = (
    "Contains information licensed under the Open Government Licence – British Columbia. "
    "Source: DriveBC Open511 (Government of British Columbia)."
)
SCHEMA_VERSION = "v1"
STATUS_FILTER = "ACTIVE"
DEFAULT_BBOX = "-123.45,48.99,-122.45,49.49"
PAGE_SIZE = 100
MAX_PAGE_SIZE = 500
MAX_PAGES = 50
MAX_EVENTS = PAGE_SIZE * MAX_PAGES
MAX_PAGE_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 12.0
MAX_REFRESH_SECONDS = 60.0
CACHE_TTL_SECONDS = 10 * 60
CACHE_SCHEMA_VERSION = 1
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "drivebc_open511"


class Open511Error(Exception):
    """Sanitized source, pagination, or cache validation failure."""


class _InvalidPayload(Open511Error):
    pass


def _now_utc(now: Any) -> datetime:
    value = now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_position(position: Any) -> bool:
    return (
        isinstance(position, list)
        and len(position) >= 2
        and _valid_number(position[0])
        and _valid_number(position[1])
        and -180 <= position[0] <= 180
        and -90 <= position[1] <= 90
        and all(_valid_number(value) for value in position[2:])
    )


def _validate_geometry(value: Any) -> dict[str, Any] | None:
    """Validate observed Open511 Point/LineString GeoJSON without changing it."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("geometry must be an object")
    kind = value.get("type")
    coordinates = value.get("coordinates")
    if kind == "Point":
        if not _valid_position(coordinates):
            raise ValueError("invalid Point")
    elif kind == "LineString":
        if (
            not isinstance(coordinates, list)
            or len(coordinates) < 2
            or not all(_valid_position(position) for position in coordinates)
        ):
            raise ValueError("invalid LineString")
    else:
        raise ValueError("unsupported geometry")
    return value


def _parse_source_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _safe_source_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    absolute = urljoin(f"{API_BASE}/", value.strip())
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or parsed.hostname != "api.open511.gov.bc.ca":
        return None
    if not parsed.path.startswith("/events/"):
        return None
    return absolute


def normalize_event(record: Any, *, dataset_id: str) -> CityEvent | None:
    """Map one source record into the accepted CityEvent contract."""
    if not isinstance(record, dict):
        return None
    raw_id = record.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        return None
    headline = record.get("headline")
    event_type = record.get("event_type")
    status = record.get("status")
    if not all(
        isinstance(value, str) and value.strip() for value in (headline, event_type, status)
    ):
        return None
    if status.strip() != STATUS_FILTER:
        return None
    try:
        geometry = _validate_geometry(record.get("geography"))
    except (TypeError, ValueError):
        return None

    latitude: float | None = None
    longitude: float | None = None
    if geometry is not None and geometry["type"] == "Point":
        longitude = float(geometry["coordinates"][0])
        latitude = float(geometry["coordinates"][1])

    source_id = raw_id.strip()
    metadata = {key: value for key, value in record.items() if key != "geography"}
    description = record.get("description")
    if not isinstance(description, str) or not description.strip():
        description = None
    return CityEvent(
        id=f"{dataset_id}:{source_id}",
        source=SOURCE_NAME,
        source_dataset_id=dataset_id,
        source_record_id=source_id,
        event_type=event_type.strip(),
        title=headline.strip(),
        description=description.strip() if description else None,
        geometry=geometry,
        latitude=latitude,
        longitude=longitude,
        severity=(record.get("severity") if isinstance(record.get("severity"), str) else None),
        status=status.strip(),
        schedule_text=(
            record.get("schedule_text") if isinstance(record.get("schedule_text"), str) else None
        ),
        observed_at=_parse_source_datetime(record.get("created")),
        updated_at=_parse_source_datetime(record.get("updated")),
        source_url=_safe_source_url(record.get("url")),
        source_metadata=metadata,
        attribution=ATTRIBUTION,
    )


def _bbox_parts(bbox: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(part.strip()) for part in bbox.split(","))
    except (TypeError, ValueError):
        raise ValueError("Open511 bbox must contain four numeric coordinates.") from None
    if (
        len(parts) != 4
        or not all(math.isfinite(part) for part in parts)
        or not (-180 <= parts[0] < parts[2] <= 180)
        or not (-90 <= parts[1] < parts[3] <= 90)
    ):
        raise ValueError("Open511 bbox is invalid.")
    return parts  # type: ignore[return-value]


class DriveBCOpen511Client:
    """Fetch and cache one configurable regional ACTIVE Open511 collection."""

    def __init__(
        self,
        *,
        bbox: str = DEFAULT_BBOX,
        page_size: int = PAGE_SIZE,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = None,
        ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self.bbox = ",".join(f"{part:g}" for part in _bbox_parts(bbox))
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= MAX_PAGE_SIZE
        ):
            raise ValueError(f"Open511 page size must be between 1 and {MAX_PAGE_SIZE}.")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
            raise ValueError("Open511 cache TTL must be a positive integer.")
        self.page_size = page_size
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir)
        self._transport = transport
        self._now = now or (lambda: datetime.now(timezone.utc))
        query = {
            "endpoint": EVENTS_URL,
            "schema": SCHEMA_VERSION,
            "status": STATUS_FILTER,
            "bbox": self.bbox,
            "limit": self.page_size,
            "format": "json",
        }
        self.query_identity = hashlib.sha256(
            json.dumps(query, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.dataset_id = f"drivebc-open511-active-v1-{self.query_identity[:12]}"
        self.cache_path = self.cache_dir / f"{self.query_identity}.json"
        self._lock = asyncio.Lock()

    def _request_params(self, offset: int) -> dict[str, str | int]:
        return {
            "format": "json",
            "status": STATUS_FILTER,
            "bbox": self.bbox,
            "limit": self.page_size,
            "offset": offset,
        }

    def _validate_page(
        self, payload: Any, *, expected_offset: int
    ) -> tuple[list[dict[str, Any]], str | None]:
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise _InvalidPayload("DriveBC Open511 returned an invalid collection.")
        events = payload["events"]
        if len(events) > self.page_size or any(not isinstance(event, dict) for event in events):
            raise _InvalidPayload("DriveBC Open511 returned an invalid page.")
        meta = payload.get("meta")
        pagination = payload.get("pagination")
        if not isinstance(meta, dict) or meta.get("version") != SCHEMA_VERSION:
            raise _InvalidPayload("DriveBC Open511 returned an unsupported response version.")
        if not isinstance(pagination, dict):
            raise _InvalidPayload("DriveBC Open511 omitted pagination metadata.")
        raw_offset = pagination.get("offset")
        try:
            page_offset = int(raw_offset)
        except (TypeError, ValueError):
            raise _InvalidPayload("DriveBC Open511 returned invalid pagination metadata.") from None
        if isinstance(raw_offset, bool) or page_offset != expected_offset:
            raise _InvalidPayload("DriveBC Open511 returned an inconsistent page offset.")
        next_url = pagination.get("next_url")
        if next_url is not None and (not isinstance(next_url, str) or not next_url.strip()):
            raise _InvalidPayload("DriveBC Open511 returned an invalid next-page link.")
        return events, next_url

    def _next_page_url(self, next_url: str, expected_offset: int) -> str:
        absolute = urljoin(f"{API_BASE}/", next_url)
        parsed = urlparse(absolute)
        query = parse_qs(parsed.query, keep_blank_values=True)
        try:
            offset = int(query["offset"][0])
            limit = int(query["limit"][0])
        except (KeyError, IndexError, ValueError):
            raise _InvalidPayload("DriveBC Open511 returned an invalid next-page link.") from None
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.open511.gov.bc.ca"
            or parsed.path != "/events"
            or offset != expected_offset
            or limit != self.page_size
            or query.get("status", [None])[0] != STATUS_FILTER
            or query.get("bbox", [None])[0] != self.bbox
            or query.get("format", ["json"])[0] != "json"
        ):
            raise _InvalidPayload("DriveBC Open511 returned an inconsistent next-page link.")
        return absolute

    async def _download(self) -> tuple[list[dict[str, Any]], int]:
        records: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_pages: set[str] = set()
        offset = 0
        pages = 0
        next_url: str | None = None

        async def retrieve() -> tuple[list[dict[str, Any]], int]:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                nonlocal offset, pages, next_url
                while True:
                    if pages >= MAX_PAGES:
                        raise _InvalidPayload(
                            "DriveBC Open511 pagination exceeded the safety limit."
                        )
                    request_url = next_url or EVENTS_URL
                    request_key = (
                        f"{request_url}?{urlencode(self._request_params(offset))}"
                        if not next_url
                        else request_url
                    )
                    if request_key in seen_pages:
                        raise _InvalidPayload("DriveBC Open511 pagination repeated a page.")
                    seen_pages.add(request_key)
                    response = await client.get(
                        request_url,
                        params=None if next_url else self._request_params(offset),
                        headers={"Accept-Encoding": "identity"},
                    )
                    response.raise_for_status()
                    declared_length = response.headers.get("content-length")
                    if declared_length is not None:
                        try:
                            parsed_length = int(declared_length)
                        except ValueError:
                            raise _InvalidPayload(
                                "DriveBC Open511 returned invalid response length metadata."
                            ) from None
                        if parsed_length < 0 or parsed_length != len(response.content):
                            raise _InvalidPayload("DriveBC Open511 response was truncated.")
                    if len(response.content) > MAX_PAGE_BYTES:
                        raise _InvalidPayload("DriveBC Open511 response exceeded the size limit.")
                    try:
                        payload = response.json()
                    except (ValueError, TypeError):
                        raise _InvalidPayload("DriveBC Open511 returned malformed JSON.") from None
                    page, provider_next = self._validate_page(payload, expected_offset=offset)
                    for event in page:
                        source_id = event.get("id")
                        if isinstance(source_id, str) and source_id in seen_ids:
                            raise _InvalidPayload("DriveBC Open511 repeated an event across pages.")
                        if isinstance(source_id, str):
                            seen_ids.add(source_id)
                    records.extend(page)
                    pages += 1
                    if len(records) > MAX_EVENTS:
                        raise _InvalidPayload("DriveBC Open511 dataset exceeded the safety limit.")
                    offset += len(page)
                    if provider_next is not None:
                        next_url = self._next_page_url(provider_next, offset)
                        if len(page) == 0:
                            raise _InvalidPayload(
                                "DriveBC Open511 returned an empty non-final page."
                            )
                        continue
                    next_url = None
                    if len(page) == self.page_size:
                        # The provider omits a total count. Probe the next documented offset
                        # to distinguish a full final page from a truncated collection.
                        continue
                    return records, pages

        try:
            return await asyncio.wait_for(retrieve(), timeout=MAX_REFRESH_SECONDS)
        except _InvalidPayload:
            raise
        except asyncio.TimeoutError:
            raise Open511Error("DriveBC Open511 refresh exceeded its time limit.") from None
        except httpx.TimeoutException:
            raise Open511Error("DriveBC Open511 request timed out.") from None
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 429:
                raise Open511Error(
                    "DriveBC Open511 temporarily rate limited the request."
                ) from None
            raise Open511Error("DriveBC Open511 is temporarily unavailable.") from None
        except (httpx.HTTPError, OSError):
            raise Open511Error("DriveBC Open511 is temporarily unavailable.") from None

    def _normalize_dataset(self, records: list[dict[str, Any]]) -> tuple[list[CityEvent], int]:
        events = [
            event
            for record in records
            if (event := normalize_event(record, dataset_id=self.dataset_id)) is not None
        ]
        skipped = len(records) - len(events)
        if records and (not events or skipped > max(1, math.floor(len(records) * 0.2))):
            raise _InvalidPayload("DriveBC Open511 records failed validation at an unsafe rate.")
        return events, skipped

    def _read_cache(self) -> tuple[datetime, list[dict[str, Any]], int] | None:
        try:
            envelope = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(envelope, dict):
                return None
            retrieved_at = _parse_source_datetime(envelope.get("retrieved_at"))
            records = envelope.get("records")
            pages = envelope.get("page_count")
            received = envelope.get("records_received")
            if (
                isinstance(envelope.get("cache_schema_version"), bool)
                or not isinstance(envelope.get("cache_schema_version"), int)
                or envelope.get("cache_schema_version") != CACHE_SCHEMA_VERSION
                or envelope.get("query_identity") != self.query_identity
                or envelope.get("complete") is not True
                or retrieved_at is None
                or not isinstance(records, list)
                or any(not isinstance(record, dict) for record in records)
                or isinstance(pages, bool)
                or not isinstance(pages, int)
                or pages < 1
                or pages > MAX_PAGES
                or isinstance(received, bool)
                or received != len(records)
            ):
                return None
            if retrieved_at > _now_utc(self._now) or len(records) > MAX_EVENTS:
                return None
            return retrieved_at, records, pages
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def _write_cache(self, fetched_at: datetime, records: list[dict[str, Any]], pages: int) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "query_identity": self.query_identity,
            "query": {
                "endpoint": EVENTS_URL,
                "schema": SCHEMA_VERSION,
                "status": STATUS_FILTER,
                "bbox": self.bbox,
                "limit": self.page_size,
                "format": "json",
            },
            "retrieved_at": fetched_at.isoformat(),
            "complete": True,
            "page_count": pages,
            "records_received": len(records),
            "records": records,
        }
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{self.cache_path.name}.", suffix=".tmp", dir=self.cache_path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.cache_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    async def get_data(self) -> Open511Result:
        async with self._lock:
            now = _now_utc(self._now)
            cached = self._read_cache()
            cached_normalized: tuple[list[CityEvent], int] | None = None
            if cached is not None:
                cached_at, cached_records, _cached_pages = cached
                try:
                    cached_normalized = self._normalize_dataset(cached_records)
                except _InvalidPayload:
                    cached = None
                else:
                    age = max(0, int((now - cached_at).total_seconds()))
                    if age < self.ttl_seconds:
                        events, skipped = cached_normalized
                        return Open511Result(
                            events=events,
                            source_status=SourceStatus(
                                source=SOURCE_NAME,
                                dataset_id=self.dataset_id,
                                success=True,
                                available=True,
                                fetched_at=cached_at,
                                cache_hit=True,
                                cache_age_seconds=age,
                                records_received=len(cached_records),
                                records_normalized=len(events),
                                records_skipped=skipped,
                            ),
                        )
            try:
                records, page_count = await self._download()
                events, skipped = self._normalize_dataset(records)
                fetched_at = _now_utc(self._now)
                self._write_cache(fetched_at, records, page_count)
                return Open511Result(
                    events=events,
                    source_status=SourceStatus(
                        source=SOURCE_NAME,
                        dataset_id=self.dataset_id,
                        success=True,
                        available=True,
                        fetched_at=fetched_at,
                        refreshed=True,
                        records_received=len(records),
                        records_normalized=len(events),
                        records_skipped=skipped,
                    ),
                )
            except (Open511Error, OSError, ValueError) as error:
                safe_error = (
                    str(error)
                    if isinstance(error, Open511Error)
                    else "DriveBC Open511 refresh or cache replacement failed."
                )
                if cached is not None and cached_normalized is not None:
                    cached_at, cached_records, _ = cached
                    events, skipped = cached_normalized
                    return Open511Result(
                        events=events,
                        source_status=SourceStatus(
                            source=SOURCE_NAME,
                            dataset_id=self.dataset_id,
                            success=False,
                            available=True,
                            fetched_at=cached_at,
                            cache_hit=True,
                            stale=True,
                            cache_age_seconds=max(0, int((now - cached_at).total_seconds())),
                            error=f"{safe_error} Serving the last valid snapshot.",
                            records_received=len(cached_records),
                            records_normalized=len(events),
                            records_skipped=skipped,
                        ),
                    )
                return Open511Result(
                    events=[],
                    source_status=SourceStatus(
                        source=SOURCE_NAME,
                        dataset_id=self.dataset_id,
                        success=False,
                        available=False,
                        error=safe_error,
                    ),
                )


@dataclass(frozen=True)
class Open511Result:
    """Normalized regional event snapshot and its independent source status."""

    events: list[CityEvent]
    source_status: SourceStatus


_default_client: DriveBCOpen511Client | None = None


async def get_drivebc_open511_data() -> Open511Result:
    """Application-facing callable; fetches only when a consumer requests the source."""
    global _default_client
    if _default_client is None:
        _default_client = DriveBCOpen511Client()
    return await _default_client.get_data()
