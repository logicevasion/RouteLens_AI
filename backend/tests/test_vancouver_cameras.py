from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app import vancouver_cameras as cameras

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "vancouver_cameras"
NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
PAGE_URL = "https://trafficcams.vancouver.ca/example.htm"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def row(mapid: str = "TCM001", *, name: str = "Example", url: str = PAGE_URL, lon: float = -123.1, lat: float = 49.25):
    return {
        "mapid": mapid,
        "name": name,
        "url": url,
        "geo_point_2d": {"lon": lon, "lat": lat},
        "geo_local_area": "Example",
    }


def page(total: int, rows: list[dict]) -> dict:
    return {"total_count": total, "results": rows}


def test_catalogue_pagination_multiple_pages_final_partial() -> None:
    seen: list[int] = []
    values = [row(f"TCM{i:03d}") for i in range(205)]

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        seen.append(offset)
        return httpx.Response(200, json=page(len(values), values[offset : offset + limit]))

    records, _ = asyncio.run(cameras.fetch_catalogue_records(transport=httpx.MockTransport(handler)))
    assert len(records) == 205
    assert seen == [0, 100, 200]


@pytest.mark.parametrize(
    "payloads",
    [
        [page(101, [row(f"{i}") for i in range(100)]), page(101, [])],
        [page(101, [row(f"{i}") for i in range(100)]), page(102, [row("last")])],
        [page(200, [row(f"{i}") for i in range(100)]), page(200, [row(f"{i}") for i in range(100)])],
        [page(101, [row(f"{i}") for i in range(100)]), page(101, [row("0")])],
    ],
)
def test_catalogue_incomplete_total_truncated_or_repeated_page_rejected(payloads: list[dict]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        index = min(offset // 100, len(payloads) - 1)
        return httpx.Response(200, json=payloads[index])

    with pytest.raises(cameras.CameraCatalogueIncomplete):
        asyncio.run(cameras.fetch_catalogue_records(transport=httpx.MockTransport(handler)))


def test_page_validation_rejects_missing_fields_invalid_coordinates_and_unofficial_url() -> None:
    records = [row()]
    assert cameras.normalize_catalogue_records(records, fetched_at=NOW)[1].source_rows_received == 1
    for invalid in (
        {**row(), "name": None},
        {**row(), "geo_point_2d": {"lon": float("nan"), "lat": 49.2}},
        {**row(), "geo_point_2d": {"lon": -181, "lat": 49.2}},
        {**row(), "url": "https://example.invalid/camera.htm"},
        {**row(), "url": "http://trafficcams.vancouver.ca/camera.htm"},
    ):
        with pytest.raises(cameras.CameraCatalogueIncomplete):
            cameras.normalize_catalogue_records([invalid], fetched_at=NOW)


def test_duplicate_mapids_merge_same_intersection_and_preserve_ambiguous_locations() -> None:
    payload = json.loads(fixture_text("catalogue_duplicate_cases.json"))
    normalized, diagnostics = cameras.normalize_catalogue_records(payload["records"], fetched_at=NOW)
    assert len(normalized) == 3
    assert diagnostics.repeated_mapid_count == 2
    assert diagnostics.ambiguous_mapid_count == 1
    repeated = next(item for item in normalized if "TEST-REPEAT" in item.source_mapids)
    assert repeated.source_names == ["Example Ave and Main St", "Main St and Example Ave"]
    assert len(repeated.source_record_ids) == 2
    ambiguous = [item for item in normalized if "TEST-AMBIGUOUS" in item.source_mapids]
    assert len({item.intersection_id for item in ambiguous}) == 2
    again, _ = cameras.normalize_catalogue_records(list(reversed(payload["records"])), fetched_at=NOW)
    assert [item.intersection_id for item in normalized] == [item.intersection_id for item in again]


def test_views_discovered_directions_relative_absolute_duplicates_and_offhost_rejected() -> None:
    views, status, rejected = cameras.extract_directional_views(
        PAGE_URL, fixture_text("intersection_views_synthetic.html")
    )
    assert status == "inspected_with_views"
    assert rejected == 1
    assert len({item.view_id for item in views}) == len(views)
    assert [(item.direction_label, item.discovery_status) for item in views] == [
        ("East", "url_validated"),
        ("North", "url_validated"),
        ("West", "url_discovered"),
    ]
    north = next(item for item in views if item.direction_label == "North")
    assert north.image_url == "https://trafficcams.vancouver.ca/cameraimages/FixtureNorth.jpg?view=fixture"
    assert north.image_host == cameras.SOURCE_PAGE_HOST
    west = next(item for item in views if item.direction_label == "West")
    assert west.image_url is None
    assert west.diagnostic == "invalid_image_url"


def test_one_view_zero_views_and_changed_structure_are_distinguished() -> None:
    one, one_status, _ = cameras.extract_directional_views(PAGE_URL, fixture_text("intersection_one_view_synthetic.html"))
    none, none_status, _ = cameras.extract_directional_views(PAGE_URL, fixture_text("intersection_no_views_synthetic.html"))
    changed, changed_status, _ = cameras.extract_directional_views(PAGE_URL, "<html><body>Updated page</body></html>")
    assert len(one) == 1 and one[0].direction_label == "South"
    assert one_status == "inspected_with_views"
    assert none == [] and none_status == "inspected_no_views"
    assert changed == [] and changed_status == "unrecognized_structure"


def test_composite_source_direction_labels_remain_distinct() -> None:
    views, status, _ = cameras.extract_directional_views(
        PAGE_URL, fixture_text("intersection_composite_views_synthetic.html")
    )
    assert status == "inspected_with_views"
    assert [view.direction_label for view in views] == [
        "North",
        "South - Example Ave",
        "South - Sample Blvd",
    ]
    assert len({view.view_id for view in views}) == 3


def test_url_security_rejects_credentials_fragments_unsafe_hosts_and_schemes() -> None:
    for candidate in (
        "http://trafficcams.vancouver.ca/x.jpg",
        "https://user:pass@trafficcams.vancouver.ca/x.jpg",
        "https://trafficcams.vancouver.ca/x.jpg#frag",
        "https://127.0.0.1/x.jpg",
        "https://example.invalid/x.jpg",
        "javascript:alert(1)",
    ):
        views, _status, rejected = cameras.extract_directional_views(
            PAGE_URL,
            f'<div class="camera"><p><strong>North</strong></p><img src="{candidate}" /></div>',
        )
        assert rejected == 1
        assert views[0].image_url is None


def _cache_catalogue(now: datetime = NOW) -> cameras.CameraCatalogue:
    intersections, diagnostics = cameras.normalize_catalogue_records([row()], fetched_at=now)
    intersections[0] = intersections[0].model_copy(
        update={
            "enrichment_status": "inspected_with_views",
            "enrichment_error": None,
            "enrichment_checked_at": now,
            "directional_views": [
                cameras.CameraView(
                    view_id="view:north",
                    direction_label="North",
                    image_url="https://trafficcams.vancouver.ca/cameraimages/north.jpg",
                    image_host=cameras.SOURCE_PAGE_HOST,
                    discovery_status="url_validated",
                )
            ],
        }
    )
    diagnostics = diagnostics.model_copy(
        update={"pages_inspected": 1, "directional_slots_found": 1, "urls_discovered": 1, "urls_validated": 1}
    )
    return cameras.CameraCatalogue(
        source_total_count=1,
        source_fetched_at=now,
        catalogue_updated_at=now,
        enrichment_completed_at=now,
        enrichment_complete=True,
        intersections=intersections,
        diagnostics=diagnostics,
    )


def test_fresh_cache_reuse_and_corrupt_or_incompatible_cache(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    cameras._cache_write(path, _cache_catalogue(), NOW)
    store = cameras.VancouverCameraCatalogueStore(cache_path=path, now=lambda: NOW + timedelta(hours=2))
    result = asyncio.run(store.get_catalogue())
    assert result.cache_hit and result.available and result.cache_age_seconds == 7200
    data = json.loads(path.read_text())
    data["query_identity"] = "old-query"
    path.write_text(json.dumps(data))
    assert cameras._cache_read(path) == (None, None)


def test_invalid_duplicate_view_replacement_does_not_replace_good_cache(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    good = _cache_catalogue()
    cameras._cache_write(path, good, NOW)
    original = path.read_bytes()
    item = good.intersections[0]
    duplicated = item.model_copy(update={"directional_views": item.directional_views * 2})
    invalid = good.model_copy(update={"intersections": [duplicated]})
    with pytest.raises(cameras.CameraCatalogueError):
        cameras._cache_write(path, invalid, NOW + timedelta(minutes=1))
    assert path.read_bytes() == original
    path.write_text("{")
    assert cameras._cache_read(path) == (None, None)


def _refresh_transport(*, failing_page: bool = False, failing_catalogue: bool = False):
    payload = page(1, [row()])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "opendata.vancouver.ca":
            if failing_catalogue:
                return httpx.Response(503, text="internal catalogue response")
            return httpx.Response(200, json=payload)
        if failing_page:
            return httpx.Response(503, text="internal provider body")
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<h1>Example</h1><div class="camera"><p><strong>North</strong></p><img src="cameraimages/north.jpg" /></div>',
        )

    return httpx.MockTransport(handler)


def test_expired_cache_refresh_atomic_replace_and_failed_refresh_stale_fallback(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "catalogue.json"
    cameras._cache_write(path, _cache_catalogue(), NOW)
    calls: list[str] = []
    original_replace = cameras.os.replace

    def tracking_replace(src, dst):
        calls.append(str(dst))
        original_replace(src, dst)

    monkeypatch.setattr(cameras.os, "replace", tracking_replace)
    fresh_now = NOW + timedelta(hours=25)
    store = cameras.VancouverCameraCatalogueStore(
        cache_path=path, now=lambda: fresh_now, transport=_refresh_transport()
    )
    refreshed = asyncio.run(store.get_catalogue())
    assert refreshed.success and not refreshed.cache_hit
    assert calls == [str(path)]
    failed = cameras.VancouverCameraCatalogueStore(
        cache_path=path,
        now=lambda: fresh_now + timedelta(hours=25),
        transport=_refresh_transport(failing_page=True),
    )
    partial = asyncio.run(failed.get_catalogue())
    assert partial.available and not partial.success
    assert not partial.stale  # Snapshot metadata is current; prior view metadata is labeled below.
    assert partial.catalogue.intersections[0].enrichment_status == "stale_previous_views"
    assert partial.catalogue.intersections[0].directional_views[0].image_url.endswith("north.jpg")
    assert partial.catalogue.intersections[0].enrichment_error == "request_failed"


def test_partial_page_enrichment_preserves_previous_views_with_stale_label() -> None:
    async def run() -> cameras.CameraCatalogue:
        return await cameras.build_catalogue(
            previous=_cache_catalogue(),
            transport=_refresh_transport(failing_page=True),
            now=lambda: NOW + timedelta(days=1),
            concurrency=2,
        )

    result = asyncio.run(run())
    intersection = result.intersections[0]
    assert not result.enrichment_complete
    assert intersection.enrichment_status == "stale_previous_views"
    assert intersection.directional_views[0].direction_label == "North"
    assert result.diagnostics.pages_failing_enrichment == 1


def test_concurrent_gets_coalesce_refresh_and_never_fetch_image_bytes(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host + request.url.path)
        if request.url.host == "opendata.vancouver.ca":
            return httpx.Response(200, json=page(1, [row()]))
        assert request.url.path == "/example.htm"
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<div class="camera"><p><strong>North</strong></p><img src="cameraimages/north.jpg" /></div>',
        )

    store = cameras.VancouverCameraCatalogueStore(
        cache_path=tmp_path / "catalogue.json", transport=httpx.MockTransport(handler), now=lambda: NOW
    )

    async def run():
        return await asyncio.gather(store.get_catalogue(), store.get_catalogue())

    first, second = asyncio.run(run())
    assert first.available and second.cache_hit
    assert calls.count("opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/web-cam-url-links/records") == 1
    assert all("cameraimages" not in call for call in calls)


def test_cache_rejects_unsafe_view_url_and_stale_fallback_when_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    value = _cache_catalogue().model_dump(mode="json")
    value["intersections"][0]["directional_views"][0]["image_url"] = "https://127.0.0.1/x.jpg"
    envelope = {
        "cache_schema_version": cameras.SCHEMA_VERSION,
        "query_identity": cameras.QUERY_IDENTITY,
        "generated_at": NOW.isoformat(),
        "catalogue": value,
    }
    path.write_text(json.dumps(envelope))
    assert cameras._cache_read(path) == (None, None)
    result = asyncio.run(
        cameras.VancouverCameraCatalogueStore(
            cache_path=path,
            now=lambda: NOW,
            transport=_refresh_transport(failing_catalogue=True),
        ).get_catalogue()
    )
    assert not result.available and result.catalogue is None


def test_failed_catalogue_refresh_retains_valid_stale_cache(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    cameras._cache_write(path, _cache_catalogue(), NOW)
    store = cameras.VancouverCameraCatalogueStore(
        cache_path=path,
        now=lambda: NOW + timedelta(hours=30),
        transport=_refresh_transport(failing_catalogue=True),
    )
    result = asyncio.run(store.get_catalogue())
    assert result.available and result.stale and result.cache_hit
    assert result.error == "refresh_failed"
    assert result.catalogue.intersections[0].directional_views[0].direction_label == "North"


def test_partial_fresh_cache_is_available_but_not_reported_healthy(tmp_path: Path) -> None:
    path = tmp_path / "catalogue.json"
    catalogue = _cache_catalogue()
    item = catalogue.intersections[0].model_copy(update={"enrichment_status": "stale_previous_views"})
    catalogue = catalogue.model_copy(
        update={
            "enrichment_complete": False,
            "intersections": [item],
            "diagnostics": catalogue.diagnostics.model_copy(update={"pages_failing_enrichment": 1}),
        }
    )
    cameras._cache_write(path, catalogue, NOW)
    result = asyncio.run(
        cameras.VancouverCameraCatalogueStore(cache_path=path, now=lambda: NOW).get_catalogue()
    )
    assert result.available and result.cache_hit
    assert not result.success and result.stale
    assert result.error == "partial_enrichment"
