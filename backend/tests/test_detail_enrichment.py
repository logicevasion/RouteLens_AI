"""Offline parser, URL safety, cache, and failure-isolation tests."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.detail_enrichment import (
    DETAIL_CACHE_TTL_SECONDS,
    MAX_CONCURRENT_REQUESTS,
    RoadAheadDetailEnricher,
    _cache_path,
    _encode_cache_identity,
    parse_detail_html,
)
from app.road_ahead import CityEvent

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "road_ahead"
NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


def html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def event(
    record_id: str = "event-1",
    *,
    url: str | None = None,
    dataset_id: str = "road-ahead-current-road-closures",
) -> CityEvent:
    return CityEvent(
        id=f"{dataset_id}:{record_id}",
        source="City of Vancouver Road Ahead",
        source_dataset_id=dataset_id,
        source_record_id=record_id,
        event_type="road_closure",
        title="Fixture event",
        geometry={"type": "LineString", "coordinates": [[-123.1, 49.25], [-123.11, 49.26]]},
        source_url=url or "http://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d",
    )


def test_parses_observed_closure_schedule_status_and_literal_restriction() -> None:
    result = parse_detail_html(html("detail_closure.html"), event_id="closure-1", source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d")
    assert result.availability == "available"
    assert result.title == "Water Service of 4000 block of Manitoba St"
    assert result.location == "Manitoba St from W 23rd Av to W King Edward Av"
    assert result.status == "Active"
    assert result.schedule_text == "May 28, 2026 - May 28, 2027; Weekdays; 7:00 AM - 3:30 PM"
    assert result.restriction_text == result.description
    assert result.posted_text == "Jun 1, 2026"
    assert "ignored" not in result.model_dump_json()


def test_parses_construction_with_blank_location_and_multiline_description() -> None:
    result = parse_detail_html(html("detail_construction.html"), event_id="construction-1", source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/0a4e0683-e652-49af-b3ef-d40722ba1732")
    assert result.title == "E King Edward Av, St Catherines St to Kingsway"
    assert result.location is None
    assert result.status == "Design"
    assert result.schedule_text.startswith("Sep 14, 2026")
    assert "St Catherines St to Knight St" in result.description
    assert result.restriction_text is None
    assert result.updated_text == "Sep 23, 2026 10:28 AM"


def test_fixture_fields_exclude_trailing_navigation_footer_and_contact_text() -> None:
    closure_html = html("detail_closure.html").replace(
        "</body>",
        "<nav>Unrelated trailing navigation</nav><footer>Unrelated footer copy</footer></body>",
    )
    closure = parse_detail_html(
        closure_html,
        event_id="closure-1",
        source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d",
    )
    construction = parse_detail_html(
        html("detail_construction.html"),
        event_id="construction-1",
        source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/0a4e0683-e652-49af-b3ef-d40722ba1732",
    )

    assert closure.updated_text == "Jun 1, 2026 2:11 PM"
    assert construction.updated_text == "Sep 23, 2026 10:28 AM"
    assert "The Road Ahead" not in closure.model_dump_json()
    assert "Unrelated trailing navigation" not in closure.model_dump_json()
    assert "Unrelated footer copy" not in closure.model_dump_json()
    assert "City Contact" not in construction.model_dump_json()
    assert "Omitted from the sanitized fixture" not in construction.model_dump_json()


@pytest.mark.parametrize("document", ["", "<html><body></body></html>", "<html><b>Unknown page"])
def test_empty_or_unknown_pages_do_not_fabricate_details(document: str) -> None:
    if not document:
        with pytest.raises(ValueError):
            parse_detail_html(document, event_id="e", source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d")
        return
    result = parse_detail_html(document, event_id="e", source_url="https://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d")
    assert result.availability == "no_supported_fields"
    assert result.title is None and result.schedule_text is None


def test_successful_fetch_is_cached_and_reused(tmp_path: Path) -> None:
    count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html("detail_closure.html"))

    enricher = RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW)

    async def run():
        return await enricher.enrich(event()), await enricher.enrich(event())

    first, second = asyncio.run(run())
    assert first.availability == "available" and not first.from_cache
    assert second.availability == "available" and second.from_cache
    assert count == 1


def test_stale_cache_falls_back_after_failed_refresh(tmp_path: Path) -> None:
    page = html("detail_closure.html")
    cache_time = NOW - timedelta(seconds=DETAIL_CACHE_TTL_SECONDS + 1)
    request_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(503)

    async def run():
        initial = RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(
            lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text=page)
        ), now=lambda: cache_time)
        await initial.enrich(event())
        stale = RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW)
        return await stale.enrich(event())

    result = asyncio.run(run())
    assert result.availability == "available" and result.from_cache and result.stale
    assert result.error is None and result.title is not None
    assert request_count == 1


def test_stale_cache_survives_a_page_with_changed_unusable_structure(tmp_path: Path) -> None:
    page = html("detail_closure.html")
    cache_time = NOW - timedelta(seconds=DETAIL_CACHE_TTL_SECONDS + 1)

    async def run():
        initial = RoadAheadDetailEnricher(
            cache_dir=tmp_path,
            transport=httpx.MockTransport(lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text=page)),
            now=lambda: cache_time,
        )
        await initial.enrich(event())
        changed = RoadAheadDetailEnricher(
            cache_dir=tmp_path,
            transport=httpx.MockTransport(lambda _: httpx.Response(200, headers={"content-type": "text/html"}, text="<html><body>New layout</body></html>")),
            now=lambda: NOW,
        )
        return await changed.enrich(event())

    result = asyncio.run(run())
    assert result.availability == "available" and result.from_cache and result.stale
    assert result.title == "Water Service of 4000 block of Manitoba St"


def test_unsafe_url_is_rejected_without_network_access(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("unsafe URL must not be requested")

    unsafe = event(url="https://example.test/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d")
    result = asyncio.run(RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler)).enrich(unsafe))
    assert result.availability == "unavailable" and result.error == "invalid_source_url"


def test_redirect_to_unapproved_host_is_rejected(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.test/collect"})

    result = asyncio.run(RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler)).enrich(event()))
    assert result.availability == "unavailable" and result.error == "invalid_content"
    assert len(requests) == 1


def test_same_host_http_to_https_redirect_is_allowed(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        if request.url.scheme == "http":
            return httpx.Response(301, headers={"location": str(request.url).replace("http://", "https://")})
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html("detail_closure.html"))

    result = asyncio.run(RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW).enrich(event()))
    assert result.availability == "available"
    assert requests[0].startswith("http://") and requests[1].startswith("https://")


def test_non_html_response_is_unavailable(tmp_path: Path) -> None:
    result = asyncio.run(RoadAheadDetailEnricher(
        cache_dir=tmp_path,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, headers={"content-type": "application/json"}, json={"ok": True})),
    ).enrich(event()))
    assert result.availability == "unavailable" and result.error == "invalid_content"


@pytest.mark.parametrize("content_length", ["abc", "-1", "+5", "1_0", "1000001"])
def test_invalid_content_length_is_reported_as_invalid_content(tmp_path: Path, content_length: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": content_length},
            content=html("detail_closure.html").encode(),
        )

    result = asyncio.run(
        RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler)).enrich(event())
    )
    assert result.availability == "unavailable"
    assert result.error == "invalid_content"


def test_collision_resistant_cache_identity_encodes_pair_boundaries(tmp_path: Path) -> None:
    first = _encode_cache_identity("dataset-a-b", "record-c")
    second = _encode_cache_identity("dataset-a", "b-record-c")
    assert first != second
    assert _cache_path(tmp_path, event("record-c", dataset_id="dataset-a-b")).name != _cache_path(
        tmp_path, event("b-record-c", dataset_id="dataset-a")
    ).name


def test_failed_fetch_without_cache_preserves_unavailable_state(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("internal detail")

    result = asyncio.run(RoadAheadDetailEnricher(cache_dir=tmp_path, transport=httpx.MockTransport(handler)).enrich(event()))
    assert result.availability == "unavailable" and result.error == "timeout"
    assert result.title is None and result.retrieved_at is None


def test_invalid_cached_content_is_ignored_and_refetched(tmp_path: Path) -> None:
    event_value = event()
    cache_dir = tmp_path
    cache_dir.mkdir(exist_ok=True)
    _cache_path(cache_dir, event_value).write_text("{}", encoding="utf-8")
    count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html("detail_closure.html"))

    result = asyncio.run(RoadAheadDetailEnricher(cache_dir=cache_dir, transport=httpx.MockTransport(handler), now=lambda: NOW).enrich(event_value))
    assert result.availability == "available" and count == 1


def test_parallel_detail_requests_respect_small_concurrency_limit(tmp_path: Path) -> None:
    in_flight = 0
    peak = 0
    body = html("detail_closure.html").encode()

    class TrackingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, content=body, request=request)

    events = [
        event(
            f"event-{index}",
            url=f"https://vanmapp1.vancouver.ca/roadahead/events/details/00000000-0000-0000-0000-{index:012d}",
        )
        for index in range(1, 9)
    ]
    results = asyncio.run(
        RoadAheadDetailEnricher(cache_dir=tmp_path, transport=TrackingTransport(), now=lambda: NOW).enrich_many(events)
    )
    assert len(results) == 8 and all(result.availability == "available" for result in results)
    assert 1 < peak <= MAX_CONCURRENT_REQUESTS
