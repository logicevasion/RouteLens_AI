from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import pytest
from PIL import Image

from app import camera_images as images
from app.main import app
from app.models import Location
from app.vancouver_cameras import (
    CameraCatalogue,
    CameraIntersection,
    CameraView,
    CatalogueDiagnostics,
    CatalogueResult,
)

NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
DESTINATION = Location(name="Downtown Vancouver", latitude=49.2827, longitude=-123.1207)


def jpeg(color: str = "red", size: tuple[int, int] = (640, 480)) -> bytes:
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format="JPEG")
    return stream.getvalue()


def intersection(identity: str, latitude: float, longitude: float, count: int = 1) -> CameraIntersection:
    views = [
        CameraView(
            view_id=f"view-{n}",
            direction_label=f"View {n + 1}",
            image_url=f"https://trafficcams.vancouver.ca/cameraimages/{identity}-{n}.jpg",
            image_host="trafficcams.vancouver.ca",
            discovery_status="url_validated",
        )
        for n in range(count)
    ]
    return CameraIntersection(
        intersection_id=identity,
        source_mapids=[identity],
        source_record_ids=[identity],
        name=identity,
        source_names=[identity],
        latitude=latitude,
        longitude=longitude,
        official_page_url=f"https://trafficcams.vancouver.ca/{identity}.htm",
        catalogue_updated_at=NOW,
        enrichment_checked_at=NOW,
        enrichment_status="inspected_with_views",
        directional_views=views,
    )


def catalogue_result(items: list[CameraIntersection]) -> CatalogueResult:
    catalogue = CameraCatalogue(
        source_total_count=len(items),
        source_fetched_at=NOW,
        catalogue_updated_at=NOW,
        enrichment_completed_at=NOW,
        enrichment_complete=True,
        intersections=items,
        diagnostics=CatalogueDiagnostics(
            source_rows_received=len(items), normalized_intersections=len(items), source_total_count=len(items)
        ),
    )
    return CatalogueResult(catalogue=catalogue, available=True, success=True)


class FakeCatalogueStore:
    def __init__(self, result: CatalogueResult):
        self.result = result
        self.calls = 0

    async def get_catalogue(self):
        self.calls += 1
        return self.result


def test_image_validation_checks_type_signature_decode_and_dimensions():
    body = jpeg()
    assert images._validated_image(body, "image/jpeg") == ("image/jpeg", 640, 480)
    for payload, content_type in ((body, "text/html"), (b"<html>error</html>", "image/jpeg"), (body[:80], "image/jpeg")):
        with pytest.raises(images.CameraImageError):
            images._validated_image(payload, content_type)
    tiny = jpeg(size=(80, 80))
    with pytest.raises(images.CameraImageError, match="dimensions"):
        images._validated_image(tiny, "image/jpeg")


@pytest.mark.parametrize("status", [403, 404, 429, 500])
def test_http_failures_are_sanitized(status: int, tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    store = images.CameraImageStore(
        cache_dir=tmp_path,
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="private details")),
        now=lambda: NOW,
    )
    assert asyncio.run(store.get_view(item, item.directional_views[0])) is None


def test_rejects_unapproved_url_and_redirect(tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    view = item.directional_views[0].model_copy(update={"image_url": "https://127.0.0.1/private.jpg"})
    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(lambda request: pytest.fail("request made")))
    with pytest.raises(images.CameraImageError):
        asyncio.run(store.get_view(item, view))
    store = images.CameraImageStore(
        cache_dir=tmp_path,
        transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/x"})),
    )
    assert asyncio.run(store.get_view(item, item.directional_views[0])) is None


def test_transport_timeout_and_redirect_budget_are_bounded(tmp_path):
    item = intersection("near", 49.2827, -123.1207)

    def timeout(request):
        raise httpx.ReadTimeout("secret-free test timeout")

    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(timeout))
    assert asyncio.run(store.get_view(item, item.directional_views[0])) is None

    calls = []

    def redirect(request):
        calls.append(request.url.path)
        return httpx.Response(302, headers={"location": "/replacement.jpg"})

    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(redirect))
    assert asyncio.run(store.get_view(item, item.directional_views[0], max_upstream_requests=1)) is None
    assert len(calls) == 1
    assert store.upstream_requests == 1


def test_oversized_response_is_rejected_before_decode(tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    response = httpx.Response(
        200,
        headers={"content-type": "image/jpeg", "content-length": str(images.MAX_IMAGE_BYTES + 1)},
        content=b"",
    )
    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(lambda request: response))
    assert asyncio.run(store.get_view(item, item.directional_views[0])) is None


def test_fresh_cache_hit_coalescing_and_corrupt_replacement_keeps_last_frame(tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=jpeg())

    store = images.CameraImageStore(
        cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW
    )

    async def run():
        first = await asyncio.gather(*(store.get_view(item, item.directional_views[0]) for _ in range(5)))
        second = await store.get_view(item, item.directional_views[0])
        return first, second

    first, second = asyncio.run(run())
    assert len(calls) == 1
    assert all(value is not None for value in first) and second is not None
    data_path, meta_path = images._frame_paths(tmp_path, "near", "view-0")
    data_path.write_bytes(b"broken")
    assert images._cached_frame(tmp_path, item, item.directional_views[0]) is None
    assert "sha256" in meta_path.read_text()


def test_expired_frame_refresh_replaces_atomically_and_stale_fallback_is_labeled(tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    clock = [NOW]
    responses = [jpeg("red"), jpeg("blue")]
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if responses:
            body = responses.pop(0)
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=body)
        return httpx.Response(503)

    store = images.CameraImageStore(
        cache_dir=tmp_path, ttl_seconds=300, transport=httpx.MockTransport(handler), now=lambda: clock[0]
    )
    view = item.directional_views[0]
    first = asyncio.run(store.get_view(item, view))
    assert first is not None and not first[2]
    image_path, _ = images._frame_paths(tmp_path, "near", "view-0")
    original = image_path.read_bytes()
    clock[0] = NOW + timedelta(seconds=301)
    replacement = asyncio.run(store.get_view(item, view))
    assert replacement is not None and not replacement[2]
    assert image_path.read_bytes() != original
    clock[0] = NOW + timedelta(seconds=602)
    stale = asyncio.run(store.get_view(item, view))
    assert stale is not None and stale[2]
    clock[0] = NOW + timedelta(seconds=1_202)
    too_old = asyncio.run(store.get_view(item, view))
    assert too_old is None
    assert len(calls) == 4


def test_nearest_fresh_intersection_selected_and_partial_views_retained(tmp_path):
    near = intersection("near", 49.2827, -123.1207, count=5)
    farther = intersection("far", 49.2850, -123.1207, count=1)
    calls: list[str] = []

    def handler(request):
        calls.append(request.url.path)
        if "near-1" in request.url.path:
            return httpx.Response(200, headers={"content-type": "text/html"}, text="no image")
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=jpeg())

    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW)
    catalogue = FakeCatalogueStore(catalogue_result([farther, near]))
    service = images.DestinationCameraService(catalogue_store=catalogue, image_store=store)
    result = asyncio.run(service.nearest(DESTINATION))
    assert result.status == "available"
    assert result.intersection.intersection_id == "near"
    assert len(result.views) == 4
    assert result.diagnostics.views_failed == 1
    assert result.diagnostics.candidates_attempted == 1
    assert len(calls) == 5


def test_candidate_order_ties_are_stable_invalid_points_and_radius_are_excluded():
    tie_b = intersection("b", 49.2827, -123.1207)
    tie_a = intersection("a", 49.2827, -123.1207)
    invalid = intersection("invalid", float("nan"), -123.1207)
    far = intersection("outside-radius", 49.33, -123.1207)
    ranked = images.rank_intersections([tie_b, invalid, far, tie_a], DESTINATION)
    assert [item.intersection_id for item, _ in ranked] == ["a", "b"]
    assert all(distance >= 0 for _, distance in ranked)
    many = [
        intersection(f"candidate-{index:02d}", 49.2827 + index * 0.0001, -123.1207)
        for index in range(15)
    ]
    assert len(images.rank_intersections(many, DESTINATION)) == images.MAX_CANDIDATES


def test_stale_only_frames_are_returned_degraded_and_do_not_qualify_fresh_selection(tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    clock = [NOW]
    fail = [False]

    def handler(request):
        if fail[0]:
            return httpx.Response(503)
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=jpeg())

    store = images.CameraImageStore(
        cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: clock[0]
    )
    catalogue = FakeCatalogueStore(catalogue_result([item]))
    service = images.DestinationCameraService(catalogue_store=catalogue, image_store=store)
    first = asyncio.run(service.nearest(DESTINATION))
    assert first.status == "available"
    clock[0] = NOW + timedelta(seconds=301)
    fail[0] = True
    stale = asyncio.run(service.nearest(DESTINATION))
    assert stale.status == "stale"
    assert stale.views == []
    assert len(stale.stale_views) == 1 and stale.stale_views[0].stale


def test_nearest_broken_falls_back_and_distance_ties_use_identity(tmp_path):
    near_a = intersection("a-near", 49.2827, -123.1207)
    near_b = intersection("b-near", 49.2827, -123.1207)
    farther = intersection("farther", 49.2840, -123.1207)

    def handler(request):
        if "near" in request.url.path:
            return httpx.Response(503)
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=jpeg())

    store = images.CameraImageStore(cache_dir=tmp_path, transport=httpx.MockTransport(handler), now=lambda: NOW)
    service = images.DestinationCameraService(
        catalogue_store=FakeCatalogueStore(catalogue_result([farther, near_b, near_a])), image_store=store
    )
    result = asyncio.run(service.nearest(DESTINATION))
    assert result.intersection.intersection_id == "farther"
    assert result.diagnostics.fallback_used
    assert result.diagnostics.candidates_attempted == 3


def test_outside_city_destination_is_rejected_before_catalogue_load():
    catalogue = FakeCatalogueStore(catalogue_result([]))
    service = images.DestinationCameraService(catalogue_store=catalogue)
    with pytest.raises(ValueError, match="inside the City"):
        asyncio.run(service.nearest(Location(name="Richmond", latitude=49.1666, longitude=-123.1336)))
    assert catalogue.calls == 0


def test_api_contract_and_image_endpoint(monkeypatch, tmp_path):
    item = intersection("near", 49.2827, -123.1207)
    body = jpeg()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, headers={"content-type": "image/jpeg"}, content=body))
    store = images.CameraImageStore(cache_dir=tmp_path, transport=transport, now=lambda: NOW)
    catalogue = FakeCatalogueStore(catalogue_result([item]))
    monkeypatch.setattr("app.routes.camera_service", images.DestinationCameraService(catalogue_store=catalogue, image_store=store))

    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            selected = await client.post("/api/cameras/nearest", json={"destination": DESTINATION.model_dump()})
            image = await client.get(selected.json()["views"][0]["image_reference"])
            invalid = await client.get("/api/cameras/images/unknown-reference")
            outside = await client.post(
                "/api/cameras/nearest",
                json={
                    "destination": Location(
                        name="Richmond", latitude=49.1666, longitude=-123.1336
                    ).model_dump()
                },
            )
            return selected, image, invalid, outside

    selected, image_response, invalid, outside = asyncio.run(request())
    assert selected.status_code == 200
    assert selected.json()["intersection"]["intersection_id"] == "near"
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/jpeg"
    assert image_response.headers["cache-control"] == "private, max-age=60, must-revalidate"
    assert image_response.content == body
    assert invalid.status_code == 404
    assert outside.status_code == 422
