"""Official Vancouver camera metadata and directional URL catalogue enrichment.

This module discovers and validates URL metadata only. It never requests image
bytes and does not imply that a discovered URL currently serves a usable image.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SOURCE_NAME = "City of Vancouver Open Data Portal"
DATASET_ID = "web-cam-url-links"
CATALOGUE_URL = (
    "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/"
    f"{DATASET_ID}/records"
)
SOURCE_PAGE_HOST = "trafficcams.vancouver.ca"
IMAGE_HOSTS = frozenset({SOURCE_PAGE_HOST})
ATTRIBUTION = "Contains information licensed under the Open Government Licence – Vancouver."
SCHEMA_VERSION = 2
QUERY_IDENTITY = (
    "explore-v2.1:web-cam-url-links:mapid,name,url,geo_point_2d,geo_local_area,geom;"
    "official-camera-block-html-v2"
)
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_RECORDS = 1000
MAX_CATALOGUE_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGE_HTML_BYTES = 512 * 1024
MAX_CACHE_BYTES = 16 * 1024 * 1024
REQUEST_TIMEOUT = httpx.Timeout(12.0, connect=4.0)
MAX_METADATA_SECONDS = 120.0
MAX_REFRESH_SECONDS = 240.0
PAGE_CONCURRENCY = 4
CACHE_TTL_SECONDS = 24 * 60 * 60
USER_AGENT = "RouteLensAI/0.1 (bounded official camera catalogue metadata enrichment)"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "cache" / "vancouver_cameras" / "catalogue.json"

PageStatus = Literal[
    "inspected_with_views",
    "inspected_no_views",
    "unrecognized_structure",
    "fetch_failed",
    "stale_previous_views",
]
DiscoveryStatus = Literal["slot_present", "url_discovered", "url_validated"]
KNOWN_DIRECTIONS = frozenset({"North", "East", "South", "West"})


class CameraCatalogueError(Exception):
    """Sanitized catalogue, source or cache failure."""


class CameraCatalogueIncomplete(CameraCatalogueError):
    """A source response cannot establish a complete, internally consistent snapshot."""


class CameraView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_id: str
    direction_label: str | None = None
    image_url: str | None = None
    image_host: str | None = None
    discovery_source: Literal["official_intersection_html"] = "official_intersection_html"
    discovery_status: DiscoveryStatus
    diagnostic: Literal["invalid_image_url", "unsupported_direction"] | None = None


class CameraIntersection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intersection_id: str
    source_mapids: list[str]
    source_record_ids: list[str]
    name: str
    source_names: list[str]
    latitude: float
    longitude: float
    official_page_url: str
    local_area: str | None = None
    source: Literal["City of Vancouver Open Data Portal"] = SOURCE_NAME
    attribution: str = ATTRIBUTION
    catalogue_updated_at: datetime
    enrichment_checked_at: datetime | None = None
    enrichment_status: PageStatus
    enrichment_error: Literal[
        "request_failed", "invalid_response", "page_not_found", "unsupported_html"
    ] | None = None
    directional_views: list[CameraView] = Field(default_factory=list)


class CatalogueDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_rows_received: int = 0
    normalized_intersections: int = 0
    repeated_mapid_count: int = 0
    ambiguous_mapid_count: int = 0
    pages_inspected: int = 0
    pages_failing_enrichment: int = 0
    pages_with_unrecognized_structure: int = 0
    directional_slots_found: int = 0
    urls_discovered: int = 0
    urls_validated: int = 0
    invalid_urls_rejected: int = 0
    intersections_with_no_discovered_views: int = 0
    source_total_count: int = 0


class CameraCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    query_identity: str = QUERY_IDENTITY
    source_url: str = CATALOGUE_URL
    dataset_id: str = DATASET_ID
    source_total_count: int
    source_fetched_at: datetime
    catalogue_updated_at: datetime
    enrichment_completed_at: datetime
    complete_metadata: Literal[True] = True
    enrichment_complete: bool
    intersections: list[CameraIntersection]
    diagnostics: CatalogueDiagnostics


class CatalogueResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalogue: CameraCatalogue | None
    available: bool
    success: bool
    cache_hit: bool = False
    stale: bool = False
    cache_age_seconds: int | None = None
    error: str | None = None


def _utc(now: Any) -> datetime:
    value = now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _official_url(value: Any, *, hosts: frozenset[str]) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    if any(ord(char) < 32 or char.isspace() for char in value) or "#" in value:
        return None
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme.lower() != "https"
            or host not in hosts
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith("/")
            or parsed.port not in (None, 443)
        ):
            return None
    except ValueError:
        return None
    return value


def _normalized_source_page(value: Any) -> str | None:
    return _official_url(value, hosts=frozenset({SOURCE_PAGE_HOST}))


def _valid_point(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    lon, lat = value.get("lon"), value.get("lat")
    if (
        isinstance(lon, bool)
        or isinstance(lat, bool)
        or not isinstance(lon, (int, float))
        or not isinstance(lat, (int, float))
        or not math.isfinite(lon)
        or not math.isfinite(lat)
        or not -180 <= lon <= 180
        or not -90 <= lat <= 90
    ):
        return None
    return float(lat), float(lon)


def _validate_catalogue_snapshot(catalogue: CameraCatalogue) -> None:
    diagnostics = catalogue.diagnostics
    if (
        catalogue.source_total_count != diagnostics.source_rows_received
        or diagnostics.normalized_intersections != len(catalogue.intersections)
        or diagnostics.source_rows_received < len(catalogue.intersections)
    ):
        raise CameraCatalogueError("The enriched camera catalogue counts are inconsistent.")
    intersection_ids = [item.intersection_id for item in catalogue.intersections]
    if len(intersection_ids) != len(set(intersection_ids)) or intersection_ids != sorted(intersection_ids):
        raise CameraCatalogueError("The enriched camera catalogue contains unstable intersection identities.")
    for item in catalogue.intersections:
        if _normalized_source_page(item.official_page_url) is None:
            raise CameraCatalogueError("The enriched camera catalogue contains an unapproved page URL.")
        identity = _fingerprint(
            {
                "page": item.official_page_url,
                "latitude": item.latitude,
                "longitude": item.longitude,
            }
        )
        if item.intersection_id != f"vancouver-camera:{identity}":
            raise CameraCatalogueError("The enriched camera catalogue contains an invalid intersection identity.")
        if (
            item.source_mapids != sorted(set(item.source_mapids))
            or item.source_record_ids != sorted(set(item.source_record_ids))
            or item.source_names
            != sorted(set(item.source_names), key=lambda value: (value.casefold(), value))
        ):
            raise CameraCatalogueError("The enriched camera catalogue provenance is not normalized.")
        view_ids = [view.view_id for view in item.directional_views]
        if len(view_ids) != len(set(view_ids)):
            raise CameraCatalogueError("An intersection contains duplicate view identities.")
        for view in item.directional_views:
            if view.image_url is None:
                if (
                    view.image_host is not None
                    or view.discovery_status == "url_validated"
                    or (view.discovery_status == "url_discovered" and view.diagnostic != "invalid_image_url")
                ):
                    raise CameraCatalogueError("A camera view has inconsistent URL validation metadata.")
                continue
            if (
                _official_url(view.image_url, hosts=IMAGE_HOSTS) is None
                or view.discovery_status != "url_validated"
                or view.image_host != urlparse(view.image_url).hostname
            ):
                raise CameraCatalogueError("The enriched camera catalogue contains an unapproved image URL.")


def normalize_catalogue_records(
    records: list[dict[str, Any]], *, fetched_at: datetime
) -> tuple[list[CameraIntersection], CatalogueDiagnostics]:
    """Validate rows and reconcile identities using official page plus approximate point."""
    if not records or len(records) > MAX_RECORDS:
        raise CameraCatalogueIncomplete("The City camera catalogue row count is outside supported bounds.")

    valid: list[dict[str, Any]] = []
    mapid_counts = Counter(
        row.get("mapid") for row in records if isinstance(row.get("mapid"), str) and row["mapid"].strip()
    )
    invalid_rows = 0
    for row in records:
        if not isinstance(row, dict):
            invalid_rows += 1
            continue
        mapid = row.get("mapid")
        name = row.get("name")
        page_url = _normalized_source_page(row.get("url"))
        point = _valid_point(row.get("geo_point_2d"))
        if (
            not isinstance(mapid, str)
            or not mapid.strip()
            or not isinstance(name, str)
            or not name.strip()
            or page_url is None
            or point is None
        ):
            invalid_rows += 1
            continue
        latitude, longitude = point
        # The geometry is retained by the source but the documented coordinate contract
        # for this catalogue is geo_point_2d; malformed geometry does not override it.
        local_area = row.get("geo_local_area")
        if not isinstance(local_area, str) or not local_area.strip():
            local_area = None
        identity_material = {
            "page": page_url,
            "latitude": latitude,
            "longitude": longitude,
        }
        valid.append(
            {
                "mapid": mapid.strip(),
                "name": name.strip(),
                "page_url": page_url,
                "latitude": latitude,
                "longitude": longitude,
                "local_area": local_area.strip() if local_area else None,
                "record_id": f"city-web-cam:{_fingerprint(row)}",
                "identity": _fingerprint(identity_material),
            }
        )

    if invalid_rows:
        raise CameraCatalogueIncomplete("The City camera catalogue contains incomplete or invalid records.")
    if not valid:
        raise CameraCatalogueIncomplete("The City camera catalogue contains no valid camera rows.")

    by_identity: dict[str, list[dict[str, Any]]] = {}
    for item in valid:
        by_identity.setdefault(item["identity"], []).append(item)

    intersections: list[CameraIntersection] = []
    for identity, items in by_identity.items():
        names = sorted({item["name"] for item in items}, key=lambda value: (value.casefold(), value))
        mapids = sorted({item["mapid"] for item in items})
        record_ids = sorted({item["record_id"] for item in items})
        areas = sorted(
            {item["local_area"] for item in items if item["local_area"]},
            key=lambda value: (value.casefold(), value),
        )
        sample = items[0]
        intersections.append(
            CameraIntersection(
                intersection_id=f"vancouver-camera:{identity}",
                source_mapids=mapids,
                source_record_ids=record_ids,
                name=names[0],
                source_names=names,
                latitude=sample["latitude"],
                longitude=sample["longitude"],
                official_page_url=sample["page_url"],
                local_area=areas[0] if areas else None,
                catalogue_updated_at=fetched_at,
                enrichment_status="fetch_failed",
                enrichment_error="request_failed",
            )
        )
    intersections.sort(key=lambda item: item.intersection_id)
    repeated_mapids = {key for key, count in mapid_counts.items() if count > 1}
    ambiguous_mapids = {
        mapid
        for mapid in repeated_mapids
        if len({item["identity"] for item in valid if item["mapid"] == mapid}) > 1
    }
    diagnostics = CatalogueDiagnostics(
        source_rows_received=len(records),
        normalized_intersections=len(intersections),
        repeated_mapid_count=len(repeated_mapids),
        ambiguous_mapid_count=len(ambiguous_mapids),
    )
    return intersections, diagnostics


class _CameraMarkupParser(HTMLParser):
    """Extract src/label pairs only from the observed official .camera blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.camera_depth = 0
        self.strong_depth = 0
        self.current_label: str | None = None
        self.current_src: str | None = None
        self.slots: list[tuple[str | None, str | None]] = []
        self.camera_blocks = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag.lower() == "div" and "camera" in classes:
            self.camera_depth += 1
            self.camera_blocks += 1
            self.current_label = None
            self.current_src = None
        if self.camera_depth and tag.lower() == "strong":
            self.strong_depth += 1
        if self.camera_depth and tag.lower() == "img":
            src = values.get("src")
            self.current_src = src.strip() if isinstance(src, str) and src.strip() else None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "strong" and self.strong_depth:
            self.strong_depth -= 1
        if tag.lower() == "div" and self.camera_depth:
            if self.current_label is not None or self.current_src is not None:
                self.slots.append((self.current_label, self.current_src))
            self.camera_depth -= 1
            if not self.camera_depth:
                self.current_label = None
                self.current_src = None

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if self.camera_depth and self.strong_depth and value:
            self.current_label = f"{self.current_label or ''} {value}".strip()


def _view_id(direction: str | None, url: str | None, index_hint: int = 0) -> str:
    direction_key = direction.casefold() if direction else "unknown"
    basis = f"{direction_key}:{_fingerprint(url or index_hint)}"
    return f"view:{_fingerprint(basis)}"


def extract_directional_views(page_url: str, html_text: str) -> tuple[list[CameraView], PageStatus, int]:
    """Parse observed .camera blocks; validate but do not retrieve image URLs."""
    parser = _CameraMarkupParser()
    try:
        parser.feed(html_text)
        parser.close()
    except ValueError:
        return [], "unrecognized_structure", 0
    if not parser.camera_blocks:
        return [], "unrecognized_structure", 0

    views: list[CameraView] = []
    seen: set[tuple[str | None, str | None]] = set()
    invalid_count = 0
    for index, (raw_direction, raw_src) in enumerate(parser.slots):
        source_label = " ".join(raw_direction.split()) if raw_direction else None
        canonical = {label.casefold(): label for label in KNOWN_DIRECTIONS}
        direction = canonical.get(source_label.casefold(), source_label) if source_label else None
        unsupported_direction = bool(
            source_label
            and (
                len(source_label) > 80
                or any(ord(char) < 32 for char in source_label)
            )
        )
        if unsupported_direction:
            direction = None
        resolved: str | None = None
        valid_url: str | None = None
        diagnostic: Literal["invalid_image_url", "unsupported_direction"] | None = None
        if raw_src:
            try:
                resolved = urljoin(page_url, raw_src)
            except ValueError:
                resolved = raw_src
            valid_url = _official_url(resolved, hosts=IMAGE_HOSTS)
            if valid_url is None:
                invalid_count += 1
                diagnostic = "invalid_image_url"
        elif direction is None:
            diagnostic = "unsupported_direction"
        if unsupported_direction:
            diagnostic = "unsupported_direction"
        key = (direction, valid_url if valid_url else (resolved if resolved else None))
        if key in seen:
            continue
        seen.add(key)
        if valid_url:
            status: DiscoveryStatus = "url_validated"
            host = urlparse(valid_url).hostname
        elif raw_src:
            status = "url_discovered"
            host = None
        else:
            status = "slot_present"
            host = None
        views.append(
            CameraView(
                view_id=_view_id(direction, valid_url or resolved, index),
                direction_label=direction,
                image_url=valid_url,
                image_host=host,
                discovery_status=status,
                diagnostic=diagnostic,
            )
        )
    views.sort(key=lambda view: (view.direction_label or "~", view.view_id))
    status = "inspected_with_views" if any(view.image_url for view in views) else "inspected_no_views"
    return views, status, invalid_count


async def _read_bounded(response: httpx.Response, maximum: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > maximum:
            raise CameraCatalogueIncomplete("An official source response exceeded the configured size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_catalogue_page(payload: Any, *, offset: int, requested_limit: int) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise CameraCatalogueIncomplete("The City camera catalogue returned an invalid page structure.")
    total = payload.get("total_count")
    rows = payload.get("results")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0 or total > MAX_RECORDS:
        raise CameraCatalogueIncomplete("The City camera catalogue total is outside supported bounds.")
    if not isinstance(rows, list) or len(rows) > requested_limit:
        raise CameraCatalogueIncomplete("The City camera catalogue returned an invalid page.")
    expected = min(requested_limit, max(0, total - offset))
    if len(rows) != expected:
        raise CameraCatalogueIncomplete("The City camera catalogue page was truncated or incomplete.")
    if any(not isinstance(row, dict) for row in rows):
        raise CameraCatalogueIncomplete("The City camera catalogue page contains malformed records.")
    return total, rows


async def fetch_catalogue_records(
    *, transport: httpx.AsyncBaseTransport | None = None
) -> tuple[list[dict[str, Any]], datetime]:
    try:
        return await asyncio.wait_for(
            _fetch_catalogue_records(transport=transport), timeout=MAX_METADATA_SECONDS
        )
    except asyncio.TimeoutError:
        raise CameraCatalogueIncomplete("The City camera metadata refresh exceeded its time limit.") from None


async def _fetch_catalogue_records(
    *, transport: httpx.AsyncBaseTransport | None = None
) -> tuple[list[dict[str, Any]], datetime]:
    records: list[dict[str, Any]] = []
    seen_pages: set[str] = set()
    total: int | None = None
    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        transport=transport,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    ) as client:
        offset = 0
        while total is None or offset < total:
            if offset // PAGE_SIZE >= MAX_PAGES:
                raise CameraCatalogueIncomplete("The City camera catalogue exceeds the page limit.")
            async with client.stream(
                "GET",
                CATALOGUE_URL,
                params={"limit": PAGE_SIZE, "offset": offset, "order_by": "mapid"},
            ) as response:
                if response.status_code != 200:
                    raise CameraCatalogueIncomplete("The City camera catalogue request failed.")
                body = await _read_bounded(response, MAX_CATALOGUE_PAGE_BYTES)
            try:
                payload = json.loads(body)
            except (ValueError, TypeError):
                raise CameraCatalogueIncomplete("The City camera catalogue returned invalid JSON.") from None
            page_total, rows = validate_catalogue_page(payload, offset=offset, requested_limit=PAGE_SIZE)
            if total is not None and page_total != total:
                raise CameraCatalogueIncomplete("The City camera catalogue total changed during pagination.")
            total = page_total
            signature = _fingerprint(rows)
            if signature in seen_pages:
                raise CameraCatalogueIncomplete("The City camera catalogue repeated a page.")
            seen_pages.add(signature)
            records.extend(rows)
            offset += len(rows)
            if total == 0:
                break
        if total is None or len(records) != total:
            raise CameraCatalogueIncomplete("The City camera catalogue snapshot is incomplete.")
    record_ids = [_fingerprint(row) for row in records]
    if len(record_ids) != len(set(record_ids)):
        raise CameraCatalogueIncomplete("The City camera catalogue repeated a source record across pages.")
    return records, datetime.now(timezone.utc)


async def _inspect_page(
    client: httpx.AsyncClient, intersection: CameraIntersection, checked_at: datetime
) -> tuple[CameraIntersection, int]:
    try:
        async with client.stream("GET", intersection.official_page_url) as response:
            if response.status_code == 404:
                return intersection.model_copy(
                    update={"enrichment_status": "fetch_failed", "enrichment_error": "page_not_found", "enrichment_checked_at": checked_at}
                ), 0
            if response.status_code != 200:
                return intersection.model_copy(
                    update={"enrichment_status": "fetch_failed", "enrichment_error": "request_failed", "enrichment_checked_at": checked_at}
                ), 0
            if "text/html" not in response.headers.get("content-type", "").lower():
                return intersection.model_copy(
                    update={"enrichment_status": "fetch_failed", "enrichment_error": "invalid_response", "enrichment_checked_at": checked_at}
                ), 0
            body = await _read_bounded(response, MAX_PAGE_HTML_BYTES)
        try:
            page_text = body.decode("utf-8")
        except UnicodeDecodeError:
            return intersection.model_copy(
                update={"enrichment_status": "fetch_failed", "enrichment_error": "invalid_response", "enrichment_checked_at": checked_at}
            ), 0
        views, status, rejected = extract_directional_views(intersection.official_page_url, page_text)
        error = "unsupported_html" if status == "unrecognized_structure" else None
        return intersection.model_copy(
            update={
                "directional_views": views,
                "enrichment_status": status,
                "enrichment_error": error,
                "enrichment_checked_at": checked_at,
            }
        ), rejected
    except (httpx.HTTPError, OSError, CameraCatalogueIncomplete):
        return intersection.model_copy(
            update={"enrichment_status": "fetch_failed", "enrichment_error": "request_failed", "enrichment_checked_at": checked_at}
        ), 0


def _previous_enrichment(
    current: CameraIntersection, previous: CameraCatalogue | None, checked_at: datetime
) -> CameraIntersection:
    if previous is None:
        return current
    match = next(
        (
            item
            for item in previous.intersections
            if item.intersection_id == current.intersection_id
            and item.official_page_url == current.official_page_url
        ),
        None,
    )
    if match is None or not match.directional_views:
        return current
    return current.model_copy(
        update={
            "directional_views": match.directional_views,
            "enrichment_status": "stale_previous_views",
            "enrichment_error": current.enrichment_error,
            "enrichment_checked_at": checked_at,
        }
    )


def _diagnostics(
    base: CatalogueDiagnostics,
    intersections: list[CameraIntersection],
    *,
    source_total: int,
    invalid_urls: int,
) -> CatalogueDiagnostics:
    return base.model_copy(
        update={
            "normalized_intersections": len(intersections),
            "pages_inspected": sum(
                item.enrichment_status in {"inspected_with_views", "inspected_no_views", "unrecognized_structure"}
                for item in intersections
            ),
            "pages_failing_enrichment": sum(
                item.enrichment_status
                in {"fetch_failed", "stale_previous_views", "unrecognized_structure"}
                for item in intersections
            ),
            "pages_with_unrecognized_structure": sum(
                item.enrichment_status == "unrecognized_structure" for item in intersections
            ),
            "directional_slots_found": sum(len(item.directional_views) for item in intersections),
            "urls_discovered": sum(bool(view.image_url) for item in intersections for view in item.directional_views)
            + invalid_urls,
            "urls_validated": sum(bool(view.image_url) for item in intersections for view in item.directional_views),
            "invalid_urls_rejected": invalid_urls,
            "intersections_with_no_discovered_views": sum(
                not any(view.image_url for view in item.directional_views) for item in intersections
            ),
            "source_total_count": source_total,
        }
    )


async def build_catalogue(
    *,
    previous: CameraCatalogue | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    now: Any = None,
    concurrency: int = PAGE_CONCURRENCY,
) -> CameraCatalogue:
    """Fetch a complete metadata snapshot and inspect each official page with bounded concurrency."""
    fetched_at = _utc(now or (lambda: datetime.now(timezone.utc)))
    records, source_time = await fetch_catalogue_records(transport=transport)
    intersections, base_diagnostics = normalize_catalogue_records(records, fetched_at=fetched_at)
    if not intersections:
        raise CameraCatalogueIncomplete("No valid Vancouver camera intersections were available.")
    semaphore = asyncio.Semaphore(max(1, min(concurrency, 8)))
    checked_at = _utc(now or (lambda: datetime.now(timezone.utc)))
    invalid_urls = 0

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        transport=transport,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    ) as client:
        async def bounded_inspect(item: CameraIntersection) -> tuple[CameraIntersection, int]:
            async with semaphore:
                return await _inspect_page(client, item, checked_at)

        inspected = await asyncio.wait_for(
            asyncio.gather(*(bounded_inspect(item) for item in intersections)),
            timeout=MAX_REFRESH_SECONDS,
        )
    enriched: list[CameraIntersection] = []
    for item, rejected_count in inspected:
        invalid_urls += rejected_count
        if item.enrichment_status in {"fetch_failed", "unrecognized_structure"}:
            item = _previous_enrichment(item, previous, checked_at)
        enriched.append(item)
    enriched.sort(key=lambda item: item.intersection_id)
    any_failure = any(
        item.enrichment_status in {"fetch_failed", "stale_previous_views", "unrecognized_structure"}
        for item in enriched
    )
    diagnostics = _diagnostics(
        base_diagnostics, enriched, source_total=len(records), invalid_urls=invalid_urls
    )
    return CameraCatalogue(
        source_total_count=len(records),
        source_fetched_at=source_time,
        catalogue_updated_at=fetched_at,
        enrichment_completed_at=checked_at,
        enrichment_complete=not any_failure,
        intersections=enriched,
        diagnostics=diagnostics,
    )


def _cache_read(path: Path) -> tuple[CameraCatalogue | None, datetime | None]:
    try:
        if path.stat().st_size > MAX_CACHE_BYTES:
            return None, None
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(envelope, dict) or envelope.get("cache_schema_version") != SCHEMA_VERSION:
            return None, None
        if envelope.get("query_identity") != QUERY_IDENTITY:
            return None, None
        generated = envelope.get("generated_at")
        timestamp = datetime.fromisoformat(generated) if isinstance(generated, str) else None
        if timestamp is None or timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return None, None
        catalogue = CameraCatalogue.model_validate(envelope.get("catalogue"))
        _validate_catalogue_snapshot(catalogue)
        return catalogue, timestamp.astimezone(timezone.utc)
    except (CameraCatalogueError, OSError, ValueError, TypeError, ValidationError, AttributeError):
        return None, None


def _cache_write(path: Path, catalogue: CameraCatalogue, generated_at: datetime) -> None:
    _validate_catalogue_snapshot(catalogue)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(
        {
            "cache_schema_version": SCHEMA_VERSION,
            "query_identity": QUERY_IDENTITY,
            "generated_at": generated_at.isoformat(),
            "catalogue": catalogue.model_dump(mode="json"),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if len(body.encode("utf-8")) > MAX_CACHE_BYTES:
        raise CameraCatalogueError("The enriched camera catalogue exceeded the cache size limit.")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class VancouverCameraCatalogueStore:
    """24-hour cache with per-instance refresh coalescing and last-good fallback."""

    def __init__(
        self,
        *,
        cache_path: Path | str = DEFAULT_CACHE_PATH,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = None,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.ttl_seconds = ttl_seconds
        self.transport = transport
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._lock = asyncio.Lock()

    async def get_catalogue(self, *, force_refresh: bool = False) -> CatalogueResult:
        async with self._lock:
            now = _utc(self.now)
            cached, cached_at = _cache_read(self.cache_path)
            if cached_at is not None and cached_at > now:
                cached, cached_at = None, None
            age = max(0, int((now - cached_at).total_seconds())) if cached_at else None
            if cached is not None and age is not None and age < self.ttl_seconds and not force_refresh:
                cache_has_old_views = any(
                    item.enrichment_status == "stale_previous_views" for item in cached.intersections
                )
                return CatalogueResult(
                    catalogue=cached,
                    available=True,
                    success=cached.enrichment_complete,
                    cache_hit=True,
                    stale=cache_has_old_views,
                    cache_age_seconds=age,
                    error="partial_enrichment" if not cached.enrichment_complete else None,
                )
            try:
                fresh = await build_catalogue(previous=cached, transport=self.transport, now=self.now)
                _cache_write(self.cache_path, fresh, _utc(self.now))
                return CatalogueResult(
                    catalogue=fresh,
                    available=True,
                    success=fresh.enrichment_complete,
                    cache_hit=False,
                    stale=False,
                    cache_age_seconds=0,
                    error="partial_enrichment" if not fresh.enrichment_complete else None,
                )
            except (CameraCatalogueError, httpx.HTTPError, OSError, TimeoutError):
                if cached is not None and cached_at is not None:
                    return CatalogueResult(
                        catalogue=cached,
                        available=True,
                        success=False,
                        cache_hit=True,
                        stale=True,
                        cache_age_seconds=age,
                        error="refresh_failed",
                    )
                return CatalogueResult(
                    catalogue=None, available=False, success=False, error="catalogue_unavailable"
                )


async def _run_cli(args: argparse.Namespace) -> int:
    store = VancouverCameraCatalogueStore(cache_path=args.cache)
    result = await store.get_catalogue(force_refresh=args.refresh)
    if result.catalogue is None:
        print(json.dumps({"available": False, "error": result.error}))
        return 1
    catalogue = result.catalogue
    print(
        json.dumps(
            {
                "available": result.available,
                "success": result.success,
                "cache_hit": result.cache_hit,
                "stale": result.stale,
                "cache_age_seconds": result.cache_age_seconds,
                "error": result.error,
                "diagnostics": catalogue.diagnostics.model_dump(),
            },
            sort_keys=True,
        )
    )
    return 0 if result.available else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich and validate the official Vancouver camera catalogue.")
    parser.add_argument("--refresh", action="store_true", help="force a bounded catalogue and page refresh")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH, help="validated catalogue JSON path")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_cli(args)))


if __name__ == "__main__":
    main()
