"""Bounded destination camera retrieval and overwrite-only current-frame cache."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import os
import socket
import tempfile
import warnings
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from app.api_usage import Operation, usage_hooks
from app.camera_placeholder import matches_offline_placeholder
from app.geography import validate_destination
from app.models import Location
from app.vancouver_cameras import (
    ATTRIBUTION,
    IMAGE_HOSTS,
    SOURCE_NAME,
    CameraIntersection,
    CameraView,
    CatalogueResult,
    VancouverCameraCatalogueStore,
    _official_url,
)

IMAGE_CACHE_TTL_SECONDS = 300
MIN_IMAGE_CACHE_TTL_SECONDS = 60
MAX_IMAGE_CACHE_TTL_SECONDS = 900
MAX_STALE_IMAGE_AGE_SECONDS = 900
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_WIDTH = 8192
MAX_IMAGE_HEIGHT = 8192
MAX_IMAGE_PIXELS = 40_000_000
MIN_IMAGE_WIDTH = 160
MIN_IMAGE_HEIGHT = 120
MAX_CANDIDATES = 12
MAX_SCREENED_INTERSECTIONS = 4
MAX_CANDIDATE_DISTANCE_METRES = 2_000
MAX_NEARBY_MARKERS = 4
MAX_VIEWS_PER_INTERSECTION = 12
MAX_VIEW_REQUESTS_PER_SELECTION = 24
MAX_REDIRECTS = 2
IMAGE_TIMEOUT = httpx.Timeout(8.0, connect=3.0)
IMAGE_OVERALL_TIMEOUT_SECONDS = 10.0
DEFAULT_IMAGE_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "vancouver_cameras" / "current"
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
SELECTION_HEADER = "X-Camera-Selection"


class CameraImageError(Exception):
    """Sanitized retrieval, validation, or cache error."""


class CameraImageConfigurationError(CameraImageError):
    """Invalid bounded cache configuration."""


class CameraImageViewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_id: str
    direction_label: str | None
    image_reference: str
    retrieved_at: datetime
    source_capture_at: datetime | None = None
    cache_age_seconds: int
    stale: bool
    width: int
    height: int
    content_type: str
    sha256: str | None = Field(default=None, exclude=True)


class CameraIntersectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intersection_id: str
    name: str
    latitude: float
    longitude: float
    distance_metres: float
    distance_is_approximate: bool = True
    official_page_url: str
    source: str = SOURCE_NAME
    attribution: str = ATTRIBUTION


class CameraViewFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    view_id: str
    error_code: str


class CameraDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates_attempted: int = 0
    views_attempted: int = 0
    views_succeeded: int = 0
    views_failed: int = 0
    fallback_used: bool = False
    catalogue_stale: bool = False
    failures: list[CameraViewFailure] = Field(default_factory=list)


class DestinationCameraResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: Location
    status: Literal["available", "stale", "unavailable"]
    intersection: CameraIntersectionResult | None = None
    views: list[CameraImageViewResult] = Field(default_factory=list)
    stale_views: list[CameraImageViewResult] = Field(default_factory=list)
    diagnostics: CameraDiagnostics

    def selection_fingerprint(self) -> str:
        """Bind vision to the fresh views returned for this destination."""
        material = [
            self.destination.model_dump(),
            self.intersection.model_dump() if self.intersection else None,
            [(view.view_id, view.retrieved_at.isoformat(), view.sha256) for view in self.views],
        ]
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


class DestinationCameraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: Location


class NearbyCameraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: Location
    selected_intersection_id: str | None = Field(default=None, max_length=128)


class NearbyCameraMarker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intersection_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    latitude: float
    longitude: float
    distance_metres: float
    official_page_url: str = Field(min_length=1, max_length=2048)
    source: str = Field(default=SOURCE_NAME, max_length=128)
    attribution: str = Field(default=ATTRIBUTION, max_length=256)


class NearbyCameraResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: Location
    status: Literal["available", "stale", "unavailable"]
    cameras: list[NearbyCameraMarker] = Field(default_factory=list, max_length=MAX_NEARBY_MARKERS)


class StoredFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intersection_id: str
    view_id: str
    source_url: str
    retrieved_at: datetime
    source_capture_at: datetime | None = None
    content_type: str
    width: int
    height: int
    byte_length: int
    sha256: str
    offline_placeholder: bool = Field(default=False, exclude=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _distance_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """WGS84 geodesic distance using the same installed pyproj stack as RouteLens."""
    from pyproj import Geod

    _, _, metres = Geod(ellps="WGS84").inv(lon1, lat1, lon2, lat2)
    return max(0.0, float(metres))


def _safe_coordinates(item: CameraIntersection) -> bool:
    return (
        -90 <= item.latitude <= 90
        and -180 <= item.longitude <= 180
        and item.latitude == item.latitude
        and item.longitude == item.longitude
    )


def rank_intersections(
    intersections: list[CameraIntersection], destination: Location
) -> list[tuple[CameraIntersection, float]]:
    ranked = []
    for item in intersections:
        if not _safe_coordinates(item) or not item.directional_views:
            continue
        distance = _distance_metres(
            destination.latitude, destination.longitude, item.latitude, item.longitude
        )
        if distance <= MAX_CANDIDATE_DISTANCE_METRES:
            ranked.append((item, distance))
    return sorted(ranked, key=lambda pair: (pair[1], pair[0].intersection_id))[:MAX_CANDIDATES]


def _frame_key(intersection_id: str, view_id: str) -> str:
    return hashlib.sha256(f"{intersection_id}\0{view_id}".encode()).hexdigest()


def _image_reference(intersection_id: str, view_id: str) -> str:
    token = hashlib.sha256(f"camera-view\0{intersection_id}\0{view_id}".encode()).hexdigest()[:32]
    return f"/api/cameras/images/{token}"


def _validated_image(data: bytes, content_type: str, sha256: str) -> tuple[str, int, int, bool]:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise CameraImageError("image_size_invalid")
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type not in ALLOWED_IMAGE_FORMATS.values():
        raise CameraImageError("content_type_invalid")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                image_format = image.format
                width, height = image.size
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
                offline = matches_offline_placeholder(sha256, image)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise CameraImageError("image_decode_failed") from None
    if (
        image_format not in ALLOWED_IMAGE_FORMATS
        or ALLOWED_IMAGE_FORMATS[image_format] != normalized_type
        or width < MIN_IMAGE_WIDTH
        or height < MIN_IMAGE_HEIGHT
        or width > MAX_IMAGE_WIDTH
        or height > MAX_IMAGE_HEIGHT
        or width * height > MAX_IMAGE_PIXELS
    ):
        raise CameraImageError("image_dimensions_or_format_invalid")
    return normalized_type, width, height, offline


def _frame_paths(cache_dir: Path, intersection_id: str, view_id: str) -> tuple[Path, Path]:
    key = _frame_key(intersection_id, view_id)
    return cache_dir / f"{key}.img", cache_dir / f"{key}.json"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _cached_frame(cache_dir: Path, intersection: CameraIntersection, view: CameraView) -> tuple[StoredFrame, bytes] | None:
    data_path, metadata_path = _frame_paths(cache_dir, intersection.intersection_id, view.view_id)
    try:
        raw = data_path.read_bytes()
        if len(raw) > MAX_IMAGE_BYTES:
            return None
        frame = StoredFrame.model_validate_json(metadata_path.read_text(encoding="utf-8"))
        if (
            frame.intersection_id != intersection.intersection_id
            or frame.view_id != view.view_id
            or frame.source_url != view.image_url
            or frame.byte_length != len(raw)
            or frame.sha256 != hashlib.sha256(raw).hexdigest()
        ):
            return None
        _, _, _, frame.offline_placeholder = _validated_image(raw, frame.content_type, frame.sha256)
        return frame, raw
    except (OSError, ValueError, CameraImageError):
        for path in (data_path, metadata_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue
        return None


def read_current_cached_frame(
    store: CameraImageStore, intersection: CameraIntersection, view: CameraView
) -> tuple[StoredFrame, bytes] | None:
    """Read one Phase 7 validated current-frame cache entry without an HTTP request."""
    if view.discovery_status != "url_validated" or view.image_url is None:
        return None
    cached = _cached_frame(store.cache_dir, intersection, view)
    if cached is None:
        return None
    frame, body = cached
    now = store.now().astimezone(timezone.utc)
    age = (now - frame.retrieved_at.astimezone(timezone.utc)).total_seconds()
    if age < 0 or age >= store.ttl_seconds:
        return None
    return frame, body


def _prune(cache_dir: Path, keep: set[str]) -> None:
    if not cache_dir.exists():
        return
    current_time = _now().timestamp()
    stems = {path.stem for path in cache_dir.iterdir() if path.suffix in {".img", ".json"}}
    for stem in stems:
        image_path = cache_dir / f"{stem}.img"
        metadata_path = cache_dir / f"{stem}.json"
        try:
            image_age = current_time - image_path.stat().st_mtime
        except OSError:
            image_age = MAX_STALE_IMAGE_AGE_SECONDS + 1
        if stem in keep and image_age <= MAX_STALE_IMAGE_AGE_SECONDS:
            continue
        for path in (image_path, metadata_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue


def _public_host(host: str) -> bool:
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(record[4][0]).is_global for record in addresses)


class CameraImageStore:
    """Stable latest-frame records with fresh reuse, bounded stale fallback and coalescing."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = DEFAULT_IMAGE_CACHE_DIR,
        ttl_seconds: int | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        now=None,
    ) -> None:
        if ttl_seconds is None:
            try:
                ttl_seconds = int(os.getenv("CAMERA_IMAGE_CACHE_TTL_SECONDS", str(IMAGE_CACHE_TTL_SECONDS)))
            except ValueError:
                raise CameraImageConfigurationError("cache_ttl_invalid") from None
        if not MIN_IMAGE_CACHE_TTL_SECONDS <= ttl_seconds <= MAX_IMAGE_CACHE_TTL_SECONDS:
            raise CameraImageConfigurationError("cache_ttl_out_of_range")
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.transport = transport
        self.now = now or _now
        self._semaphore = asyncio.Semaphore(4)
        self._locks: dict[str, asyncio.Lock] = {}
        self.upstream_requests = 0

    async def get_view(
        self,
        intersection: CameraIntersection,
        view: CameraView,
        *,
        max_upstream_requests: int = MAX_VIEW_REQUESTS_PER_SELECTION,
    ) -> tuple[StoredFrame, bytes, bool] | None:
        if view.image_url is None or view.discovery_status != "url_validated":
            raise CameraImageError("view_url_unavailable")
        if _official_url(view.image_url, hosts=IMAGE_HOSTS) is None:
            raise CameraImageError("view_url_untrusted")
        key = _frame_key(intersection.intersection_id, view.view_id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = self.now().astimezone(timezone.utc)
            cached = _cached_frame(self.cache_dir, intersection, view)
            if cached:
                frame, body = cached
                age = max(0, int((now - frame.retrieved_at).total_seconds()))
                if age < self.ttl_seconds:
                    return frame, body, False
            stale = cached
            try:
                fresh = await asyncio.wait_for(
                    self._fetch(intersection, view, max_upstream_requests=max_upstream_requests),
                    timeout=IMAGE_OVERALL_TIMEOUT_SECONDS,
                )
                return fresh[0], fresh[1], False
            except (CameraImageError, asyncio.TimeoutError):
                if stale:
                    frame, body = stale
                    age = max(0, int((now - frame.retrieved_at).total_seconds()))
                    if age <= MAX_STALE_IMAGE_AGE_SECONDS:
                        return frame, body, True
                return None

    async def _fetch(
        self,
        intersection: CameraIntersection,
        view: CameraView,
        *,
        max_upstream_requests: int,
    ) -> tuple[StoredFrame, bytes]:
        url = view.image_url
        request_start = self.upstream_requests
        for redirects in range(MAX_REDIRECTS + 1):
            parsed = urlparse(url or "")
            host = (parsed.hostname or "").lower().rstrip(".")
            if _official_url(url, hosts=IMAGE_HOSTS) is None:
                raise CameraImageError("redirect_untrusted")
            if self.transport is None:
                try:
                    public = await asyncio.wait_for(asyncio.to_thread(_public_host, host), timeout=3.0)
                except asyncio.TimeoutError:
                    raise CameraImageError("host_unavailable") from None
                if not public:
                    raise CameraImageError("host_unavailable")
            async with self._semaphore:
                try:
                    if self.upstream_requests - request_start >= max_upstream_requests:
                        raise CameraImageError("request_budget_exhausted")
                    self.upstream_requests += 1
                    async with httpx.AsyncClient(
                        timeout=IMAGE_TIMEOUT,
                        follow_redirects=False,
                        transport=self.transport,
                        event_hooks=usage_hooks(Operation.CAMERA_FRAME),
                        headers={"User-Agent": "RouteLensAI/0.1 (bounded current camera frame)"},
                    ) as client, client.stream("GET", url) as response:
                        if response.is_redirect:
                            if redirects >= MAX_REDIRECTS or not response.headers.get("location"):
                                raise CameraImageError("redirect_limit")
                            target = urljoin(url, response.headers["location"])
                            if _official_url(target, hosts=IMAGE_HOSTS) is None:
                                raise CameraImageError("redirect_untrusted")
                            url = target
                            continue
                        if response.status_code != 200:
                            raise CameraImageError("upstream_unavailable")
                        content_type = response.headers.get("content-type", "")
                        length = response.headers.get("content-length")
                        if length:
                            try:
                                if int(length) > MAX_IMAGE_BYTES:
                                    raise CameraImageError("image_size_invalid")
                            except ValueError:
                                raise CameraImageError("content_length_invalid") from None
                        chunks = bytearray()
                        async for chunk in response.aiter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > MAX_IMAGE_BYTES:
                                raise CameraImageError("image_size_invalid")
                        body = bytes(chunks)
                        digest = hashlib.sha256(body).hexdigest()
                        content_type, width, height, offline = _validated_image(body, content_type, digest)
                        break
                except (httpx.HTTPError, TimeoutError, OSError):
                    raise CameraImageError("upstream_unavailable") from None
        else:
            raise CameraImageError("redirect_limit")

        frame = StoredFrame(
            intersection_id=intersection.intersection_id,
            view_id=view.view_id,
            source_url=view.image_url,
            retrieved_at=self.now().astimezone(timezone.utc),
            content_type=content_type,
            width=width,
            height=height,
            byte_length=len(body),
            sha256=digest,
            offline_placeholder=offline,
        )
        data_path, metadata_path = _frame_paths(self.cache_dir, intersection.intersection_id, view.view_id)
        try:
            _atomic_write(data_path, body)
            _atomic_write(metadata_path, frame.model_dump_json().encode("utf-8"))
        except OSError:
            raise CameraImageError("cache_write_failed") from None
        return frame, body

    def get_by_reference(
        self,
        catalogue: CatalogueResult,
        reference: str,
    ) -> tuple[StoredFrame, bytes] | None:
        token = reference.rsplit("/", 1)[-1]
        if catalogue.catalogue is None or len(token) != 32:
            return None
        for intersection in catalogue.catalogue.intersections:
            for view in intersection.directional_views:
                if _image_reference(intersection.intersection_id, view.view_id).rsplit("/", 1)[-1] != token:
                    continue
                if view.image_url is None or _official_url(view.image_url, hosts=IMAGE_HOSTS) is None:
                    return None
                cached = _cached_frame(self.cache_dir, intersection, view)
                if cached is None:
                    return None
                frame, body = cached
                age = max(0, int((self.now().astimezone(timezone.utc) - frame.retrieved_at).total_seconds()))
                if age > MAX_STALE_IMAGE_AGE_SECONDS or frame.offline_placeholder:
                    return None
                return frame, body
        return None


class DestinationCameraService:
    def __init__(self, *, catalogue_store=None, image_store=None) -> None:
        self.catalogue_store = catalogue_store or VancouverCameraCatalogueStore()
        self.image_store = image_store or CameraImageStore()

    async def nearest(
        self, destination: Location, *, cached_only: bool = False
    ) -> DestinationCameraResult:
        if not validate_destination(destination).valid:
            raise ValueError("Destination must be inside the City of Vancouver municipal boundary.")
        catalogue_result = await self.catalogue_store.get_catalogue()
        diagnostics = CameraDiagnostics(catalogue_stale=catalogue_result.stale)
        if catalogue_result.catalogue is None:
            return DestinationCameraResult(destination=destination, status="unavailable", diagnostics=diagnostics)
        ranked = rank_intersections(catalogue_result.catalogue.intersections, destination)
        ranked = [pair for pair in ranked if pair[0].enrichment_status in {"inspected_with_views", "stale_previous_views"}]
        if not cached_only:
            _prune(
                self.image_store.cache_dir,
                {
                    _frame_key(camera.intersection_id, view.view_id)
                    for camera in catalogue_result.catalogue.intersections
                    for view in camera.directional_views
                },
            )
        stale_candidate: tuple[
            CameraIntersection, CameraIntersectionResult, CameraImageViewResult, bool
        ] | None = None
        upstream_start = self.image_store.upstream_requests

        async def inspect(
            intersection: CameraIntersection, view: CameraView, *, stale_only: bool = False
        ) -> CameraImageViewResult | None:
            requests_used = self.image_store.upstream_requests - upstream_start
            if diagnostics.views_attempted >= MAX_VIEW_REQUESTS_PER_SELECTION or (
                not (cached_only or stale_only) and requests_used >= MAX_VIEW_REQUESTS_PER_SELECTION
            ):
                return None
            diagnostics.views_attempted += 1
            try:
                if stale_only:
                    cached = _cached_frame(self.image_store.cache_dir, intersection, view)
                    result = None
                    if cached:
                        age = self.image_store.now().astimezone(timezone.utc) - cached[0].retrieved_at
                        if self.image_store.ttl_seconds <= age.total_seconds() <= MAX_STALE_IMAGE_AGE_SECONDS:
                            result = (*cached, True)
                elif cached_only:
                    cached = read_current_cached_frame(self.image_store, intersection, view)
                    result = (*cached, False) if cached else None
                else:
                    result = await self.image_store.get_view(
                        intersection,
                        view,
                        max_upstream_requests=MAX_VIEW_REQUESTS_PER_SELECTION - requests_used,
                    )
                if result is None:
                    raise CameraImageError("image_unavailable")
                frame, _, stale = result
                if frame.offline_placeholder:
                    raise CameraImageError("offline_placeholder")
            except CameraImageError as error:
                diagnostics.views_failed += 1
                diagnostics.failures.append(
                    CameraViewFailure(view_id=view.view_id, error_code=str(error))
                )
                return None
            age = self.image_store.now().astimezone(timezone.utc) - frame.retrieved_at
            diagnostics.views_succeeded += 1
            return CameraImageViewResult(
                view_id=view.view_id,
                direction_label=view.direction_label,
                image_reference=_image_reference(intersection.intersection_id, view.view_id),
                retrieved_at=frame.retrieved_at,
                source_capture_at=frame.source_capture_at,
                cache_age_seconds=max(0, int(age.total_seconds())),
                stale=stale,
                width=frame.width,
                height=frame.height,
                content_type=frame.content_type,
                sha256=frame.sha256,
            )

        for candidate_index, (intersection, distance) in enumerate(ranked[:MAX_SCREENED_INTERSECTIONS]):
            diagnostics.candidates_attempted += 1
            views = intersection.directional_views[:MAX_VIEWS_PER_INTERSECTION]
            # Ignore catalogue slots that have no validated URL when choosing the primary.
            primary = next(
                (view for view in views if view.discovery_status == "url_validated" and view.image_url),
                None,
            )
            if primary is None:
                continue
            screened = await inspect(intersection, primary)
            if screened is None:
                continue
            metadata = CameraIntersectionResult(
                intersection_id=intersection.intersection_id,
                name=intersection.name,
                latitude=intersection.latitude,
                longitude=intersection.longitude,
                distance_metres=distance,
                official_page_url=intersection.official_page_url,
            )
            if screened.stale:
                if stale_candidate is None:
                    stale_candidate = (intersection, metadata, screened, candidate_index > 0)
                continue

            diagnostics.fallback_used = candidate_index > 0
            usable = [screened]
            stale_views = []
            for view in views:
                if view.view_id == primary.view_id:
                    continue
                gallery_view = await inspect(intersection, view)
                if gallery_view is not None:
                    (stale_views if gallery_view.stale else usable).append(gallery_view)
            return DestinationCameraResult(
                destination=destination,
                status="available",
                intersection=metadata,
                views=usable,
                stale_views=stale_views,
                diagnostics=diagnostics,
            )
        if stale_candidate:
            intersection, metadata, screened, diagnostics.fallback_used = stale_candidate
            stale_views = [screened]
            for view in intersection.directional_views[:MAX_VIEWS_PER_INTERSECTION]:
                if view.view_id != screened.view_id and view.image_url:
                    gallery_view = await inspect(intersection, view, stale_only=True)
                    if gallery_view is not None:
                        stale_views.append(gallery_view)
            return DestinationCameraResult(
                destination=destination,
                status="stale",
                intersection=metadata,
                stale_views=stale_views,
                diagnostics=diagnostics,
            )
        return DestinationCameraResult(destination=destination, status="unavailable", diagnostics=diagnostics)

    async def nearby(self, destination: Location, selected_intersection_id: str | None = None) -> NearbyCameraResult:
        """Return bounded catalogue locations without consulting the image store."""
        if not validate_destination(destination).valid:
            raise ValueError("Destination must be inside the City of Vancouver municipal boundary.")
        catalogue_result = await self.catalogue_store.get_catalogue()
        if catalogue_result.catalogue is None:
            return NearbyCameraResult(destination=destination, status="unavailable")

        ranked: list[tuple[CameraIntersection, float]] = []
        for intersection in catalogue_result.catalogue.intersections:
            if (
                not _safe_coordinates(intersection)
                or not intersection.intersection_id
                or len(intersection.intersection_id) > 128
                or not intersection.name
                or len(intersection.name) > 256
            ):
                continue
            official_url = _official_url(intersection.official_page_url, hosts=IMAGE_HOSTS)
            if official_url is None:
                continue
            distance = _distance_metres(
                destination.latitude, destination.longitude, intersection.latitude, intersection.longitude
            )
            if distance <= MAX_CANDIDATE_DISTANCE_METRES:
                ranked.append((intersection, distance))
        ranked.sort(key=lambda pair: (pair[1], pair[0].intersection_id))

        selected = next((pair for pair in ranked if pair[0].intersection_id == selected_intersection_id), None)
        chosen = ranked[:MAX_NEARBY_MARKERS]
        if selected is not None and all(pair[0].intersection_id != selected[0].intersection_id for pair in chosen):
            chosen = [*chosen[: MAX_NEARBY_MARKERS - 1], selected]
            chosen.sort(key=lambda pair: (pair[1], pair[0].intersection_id))

        return NearbyCameraResult(
            destination=destination,
            status=("stale" if catalogue_result.stale else "available") if chosen else "unavailable",
            cameras=[
                NearbyCameraMarker(
                    intersection_id=item.intersection_id,
                    name=item.name,
                    latitude=item.latitude,
                    longitude=item.longitude,
                    distance_metres=distance,
                    official_page_url=item.official_page_url,
                )
                for item, distance in chosen
            ],
        )
