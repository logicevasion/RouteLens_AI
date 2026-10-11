"""Bounded deterministic enrichment of official Road Ahead detail pages."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, ClassVar, Literal
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.road_ahead import CityEvent

DETAIL_TIMEOUT_SECONDS = 7.0
DETAIL_CACHE_TTL_SECONDS = 6 * 60 * 60
DEFAULT_DETAIL_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "road_ahead" / "details"
DETAIL_HOST = "vanmapp1.vancouver.ca"
DETAIL_PATH = re.compile(
    r"^/roadahead/events/details/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/?$"
)
MAX_PAGE_BYTES = 1_000_000
MAX_REDIRECTS = 3
MAX_CONCURRENT_REQUESTS = 4


class DetailEnrichment(BaseModel):
    """Source-grounded detail fields associated with one normalized event."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    source_url: str | None
    availability: Literal["available", "no_supported_fields", "unavailable", "parse_failed"]
    title: str | None = None
    location: str | None = None
    description: str | None = None
    status: str | None = None
    schedule_text: str | None = None
    restriction_text: str | None = None
    exceptions: str | None = None
    posted_text: str | None = None
    updated_text: str | None = None
    retrieved_at: datetime | None = None
    from_cache: bool = False
    stale: bool = False
    error: Literal[
        "invalid_source_url", "http_failure", "timeout", "invalid_content", "parse_failure"
    ] | None = None


class _VisibleTextParser(HTMLParser):
    """Collect human-readable text and omit executable and non-content elements."""

    _BLOCKS: ClassVar[set[str]] = {
        "address",
        "article",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "p",
        "section",
        "td",
        "th",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "iframe", "nav", "header", "footer", "aside"}:
            self._ignored.append(tag)
        elif not self._ignored and tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._ignored:
            if tag == self._ignored[-1]:
                self._ignored.pop()
        elif tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored and data.strip():
            self.parts.append(data)


def _safe_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        allowed_port = {None, 80} if parsed.scheme.lower() == "http" else {None, 443}
        return (
            parsed.scheme.lower() in {"http", "https"}
            and parsed.hostname is not None
            and parsed.hostname.lower() == DETAIL_HOST
            and parsed.port in allowed_port
            and parsed.username is None
            and parsed.password is None
            and DETAIL_PATH.fullmatch(parsed.path) is not None
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def _normalize_lines(html: str) -> list[str]:
    parser = _VisibleTextParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # HTMLParser is tolerant; guard unusual malformed input.
        raise ValueError("page could not be parsed") from exc
    return [line.strip() for line in re.sub(r"[\t\r ]+", " ", "".join(parser.parts)).splitlines() if line.strip()]


_LABELS = {
    "event": "title",
    "location": "location",
    "expected schedule": "schedule_text",
    "status": "status",
    "description": "description",
    "exceptions": "exceptions",
    "exception": "exceptions",
    "restriction": "restriction_text",
    "restrictions": "restriction_text",
    "posted": "posted_text",
    "updated": "updated_text",
}


def parse_detail_html(html: str, *, event_id: str, source_url: str) -> DetailEnrichment:
    """Extract only labeled fields observed on City Road Ahead detail pages."""
    if not html.strip() or len(html.encode("utf-8", errors="replace")) > MAX_PAGE_BYTES:
        raise ValueError("page is empty or too large")
    lines = _normalize_lines(html)
    fields: dict[str, str] = {}
    active: str | None = None
    for line in lines:
        label = line.rstrip(":").strip().lower()
        if label in {"city contact", "terms of use", "privacy policy"}:
            active = None
            continue
        if label in _LABELS:
            active = _LABELS[label]
            fields.setdefault(active, "")
            continue
        if active and line not in fields[active].splitlines():
            fields[active] = "\n".join(part for part in (fields[active], line) if part)

    for name, value in tuple(fields.items()):
        fields[name] = value.strip() or None

    # Road Ahead describes restrictions in plain source text rather than a
    # universal structured restriction field. Keep that exact text only when
    # the description explicitly names a closure, lane restriction, or access limit.
    description = fields.get("description")
    restriction = fields.get("restriction_text")
    if restriction is None and description and re.search(
        r"\b(closure|closed|lane restriction|lane closure|restricted access|no access)\b",
        description,
        flags=re.IGNORECASE,
    ):
        restriction = description

    supported = {key: value for key, value in fields.items() if value}
    return DetailEnrichment(
        event_id=event_id,
        source_url=source_url,
        availability="available" if supported else "no_supported_fields",
        title=fields.get("title"),
        location=fields.get("location"),
        description=description,
        status=fields.get("status"),
        schedule_text=fields.get("schedule_text"),
        restriction_text=restriction,
        exceptions=fields.get("exceptions"),
        posted_text=fields.get("posted_text"),
        updated_text=fields.get("updated_text"),
    )


def _cache_path(cache_dir: Path, event: CityEvent) -> Path:
    digest = hashlib.sha256(
        _encode_cache_identity(event.source_dataset_id, event.source_record_id)
    ).hexdigest()
    return cache_dir / f"{digest}.json"


def _encode_cache_identity(dataset_id: str, record_id: str) -> bytes:
    """Encode identity components with explicit lengths before hashing."""
    dataset = dataset_id.encode("utf-8")
    record = record_id.encode("utf-8")
    namespace = b"routelens-road-ahead-detail-cache-v1\0"
    return namespace + len(dataset).to_bytes(8, "big") + dataset + len(record).to_bytes(8, "big") + record


def _read_cache(path: Path, event: CityEvent) -> DetailEnrichment | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        detail = DetailEnrichment.model_validate(payload)
        if detail.event_id != event.id or detail.source_url != event.source_url:
            return None
        if detail.availability != "available" or detail.retrieved_at is None:
            return None
        return detail
    except (OSError, ValueError, TypeError, ValidationError):
        return None


def _write_cache(path: Path, detail: DetailEnrichment) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(detail.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    descriptor, temporary_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(raw)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


class RoadAheadDetailEnricher:
    """Fetch only matched event pages with bounded concurrency and validated cache."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = DEFAULT_DETAIL_CACHE_DIR,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = None,
        cache_ttl_seconds: int = DETAIL_CACHE_TTL_SECONDS,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.transport = transport
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.cache_ttl_seconds = cache_ttl_seconds
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def enrich(self, event: CityEvent) -> DetailEnrichment:
        if not _safe_url(event.source_url):
            return DetailEnrichment(
                event_id=event.id, source_url=event.source_url, availability="unavailable", error="invalid_source_url"
            )
        path = _cache_path(self.cache_dir, event)
        cached = _read_cache(path, event)
        now = self.now()
        if cached and cached.retrieved_at and now - cached.retrieved_at <= timedelta(seconds=self.cache_ttl_seconds):
            return cached.model_copy(update={"from_cache": True})

        async with self._semaphore:
            try:
                html = await self._download(event.source_url)
                detail = parse_detail_html(html, event_id=event.id, source_url=event.source_url)
                detail = detail.model_copy(update={"retrieved_at": now})
                if detail.availability == "available":
                    _write_cache(path, detail)
                    return detail
                if cached:
                    return cached.model_copy(update={"from_cache": True, "stale": True})
                return detail
            except (httpx.TimeoutException, asyncio.TimeoutError):
                error: Literal["timeout", "http_failure", "invalid_content", "parse_failure"] = "timeout"
                availability: Literal["unavailable", "parse_failed"] = "unavailable"
            except ValueError:
                error, availability = "parse_failure", "parse_failed"
            except (httpx.HTTPError, OSError):
                error, availability = "http_failure", "unavailable"
            except _InvalidPage:
                error, availability = "invalid_content", "unavailable"

        if cached:
            return cached.model_copy(update={"from_cache": True, "stale": True})
        return DetailEnrichment(
            event_id=event.id, source_url=event.source_url, availability=availability, error=error
        )

    async def enrich_many(self, events: list[CityEvent]) -> list[DetailEnrichment]:
        return list(await asyncio.gather(*(self.enrich(event) for event in events)))

    async def _download(self, source_url: str) -> str:
        current_url = source_url
        expected_path = urlparse(source_url).path
        async with httpx.AsyncClient(timeout=DETAIL_TIMEOUT_SECONDS, follow_redirects=False, transport=self.transport) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                if not _safe_url(current_url) or urlparse(current_url).path != expected_path:
                    raise _InvalidPage
                async with client.stream("GET", current_url, headers={"Accept": "text/html"}) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count == MAX_REDIRECTS:
                            raise _InvalidPage
                        location = response.headers.get("location")
                        if not location:
                            raise _InvalidPage
                        current_url = urljoin(str(response.url), location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    content_length = response.headers.get("content-length")
                    if content_type.split(";", maxsplit=1)[0].strip() != "text/html":
                        raise _InvalidPage
                    if content_length is not None and _invalid_content_length(content_length):
                        raise _InvalidPage
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_PAGE_BYTES:
                            raise _InvalidPage
                    if not body:
                        raise _InvalidPage
                    try:
                        return body.decode(response.encoding or "utf-8")
                    except (LookupError, UnicodeDecodeError):
                        return body.decode("utf-8", errors="replace")
        raise _InvalidPage


class _InvalidPage(Exception):
    pass


def _invalid_content_length(value: str) -> bool:
    """Reject malformed, negative, or over-limit Content-Length values."""
    declared = value.strip()
    if not declared or not declared.isascii() or not declared.isdigit():
        return True
    normalized = declared.lstrip("0") or "0"
    if len(normalized) > len(str(MAX_PAGE_BYTES)):
        return True
    return int(normalized) > MAX_PAGE_BYTES
