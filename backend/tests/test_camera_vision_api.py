from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import pytest
from PIL import Image
from test_camera_images import OFFLINE_FIXTURE, FakeCatalogueStore, catalogue_result, intersection

from app import camera_images as images
from app.main import app
from app.models import Location
from app.openrouter_vision import MODEL_ID, AttemptBudget, OpenRouterVisionAdapter
from app.vancouver_cameras import (
    CameraCatalogue,
    CameraIntersection,
    CameraView,
    CatalogueDiagnostics,
)

NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
DESTINATION = Location(name="Downtown Vancouver", latitude=49.2827, longitude=-123.1207)
ROUTE = {"type": "LineString", "coordinates": [[-123.12, 49.27], [-123.11, 49.28]]}


def trip_payload(destination: Location = DESTINATION) -> dict:
    return {
        "origin": {"name": "Richmond", "latitude": 49.163168, "longitude": -123.137414},
        "destination": destination.model_dump(),
        "mode": "drive",
        "selected_route": {
            "candidate_id": "route-2",
            "geometry": ROUTE,
            "distance_meters": 7100,
            "duration_seconds": 900,
            "label": "Alternative 2",
        },
    }


def jpeg(color: str) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (320, 240), color).save(stream, format="JPEG")
    return stream.getvalue()


def model_output(ids: list[str], *, valid: bool = True) -> dict:
    return {
        "views": [
            {
                "view_id": view_id,
                "road_surface": "wet_looking" if valid else "wet",
                "visibility": "adequate",
                "vehicle_activity": "some_visible",
                "conditions": ["glare"],
                "uncertainty": "moderate",
                "note": "Reflective pavement is visible.",
            }
            for view_id in ids
        ],
        "intersection_summary": "Pavement looks reflective in both views.",
        "summary_evidence_view_ids": ids,
    }


def provider_response(ids: list[str], *, valid: bool = True) -> dict:
    return {
        "model": MODEL_ID,
        "provider": "CoreWeave",
        "choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps(model_output(ids, valid=valid))},
        }],
        "usage": {"prompt_tokens": 400, "completion_tokens": 100, "total_tokens": 500, "cost": 0.00012},
    }


def setup_api(monkeypatch, tmp_path, *, adapter=None, destination=DESTINATION, with_frames=True):
    views = [
        CameraView(
            view_id=f"view-{direction}", direction_label=direction.title(),
            image_url=f"https://trafficcams.vancouver.ca/cameraimages/{direction}.jpg",
            image_host="trafficcams.vancouver.ca", discovery_status="url_validated",
        )
        for direction in ("east", "west")
    ]
    camera = CameraIntersection(
        intersection_id="intersection-1", source_mapids=["1"], source_record_ids=["row-1"],
        name="Cambie St & W Broadway", source_names=["Cambie St & W Broadway"],
        latitude=destination.latitude, longitude=destination.longitude,
        official_page_url="https://trafficcams.vancouver.ca/intersection-1.htm",
        catalogue_updated_at=NOW, enrichment_checked_at=NOW,
        enrichment_status="inspected_with_views", directional_views=views,
    )
    catalogue = CameraCatalogue(
        source_total_count=1, source_fetched_at=NOW, catalogue_updated_at=NOW,
        enrichment_completed_at=NOW, enrichment_complete=True, intersections=[camera],
        diagnostics=CatalogueDiagnostics(source_rows_received=1, normalized_intersections=1, source_total_count=1),
    )
    store = images.CameraImageStore(cache_dir=tmp_path / "frames", now=lambda: NOW)
    selected_views = []
    for index, view in enumerate(views):
        if with_frames:
            body = jpeg(("red", "blue")[index])
            frame = images.StoredFrame(
                intersection_id=camera.intersection_id, view_id=view.view_id, source_url=view.image_url,
                retrieved_at=NOW, content_type="image/jpeg", width=320, height=240,
                byte_length=len(body), sha256=images.hashlib.sha256(body).hexdigest(),
            )
            data_path, metadata_path = images._frame_paths(store.cache_dir, camera.intersection_id, view.view_id)
            images._atomic_write(data_path, body)
            images._atomic_write(metadata_path, frame.model_dump_json().encode())
        selected_views.append(images.CameraImageViewResult(
            view_id=view.view_id, direction_label=view.direction_label,
            image_reference=f"/api/cameras/images/{index:032d}", retrieved_at=NOW,
            source_capture_at=None, cache_age_seconds=0, stale=False,
            width=320, height=240, content_type="image/jpeg",
        ))
    selection = images.DestinationCameraResult(
        destination=destination, status="available",
        intersection=images.CameraIntersectionResult(
            intersection_id=camera.intersection_id, name=camera.name,
            latitude=camera.latitude, longitude=camera.longitude, distance_metres=0,
            official_page_url=camera.official_page_url,
        ),
        views=selected_views, diagnostics=images.CameraDiagnostics(views_succeeded=2),
    )

    class FakeService:
        image_store = store

        def __init__(self):
            self.catalogue_store = self
            self.nearest_calls = 0
            self.catalogue_calls = 0
            self.selection = selection
            self.catalogue = catalogue

        async def nearest(self, requested_destination):
            self.nearest_calls += 1
            return self.selection

        async def get_catalogue(self):
            self.catalogue_calls += 1
            return type("CatalogueResult", (), {"catalogue": self.catalogue})()

    service = FakeService()
    test_adapter = adapter or OpenRouterVisionAdapter(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(["view-east"]))),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW),
        now=lambda: NOW,
    )
    monkeypatch.setattr("app.routes.camera_service", service)
    monkeypatch.setattr("app.routes.vision_adapter", test_adapter)
    return service, test_adapter, catalogue, store, selection


def post(path: str, body: dict | None = None) -> httpx.Response:
    async def request() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(path, json=body) if body is not None else await client.get(path)
    return asyncio.run(request())


def test_observe_returns_validated_provenance_for_selected_direction(monkeypatch, tmp_path):
    service, _adapter, _catalogue, _store, _selection = setup_api(monkeypatch, tmp_path)

    response = post("/api/cameras/observe", trip_payload())

    assert response.status_code == 200
    body = response.json()
    observation = body["observation"]
    assert observation["status"] == "available"
    assert observation["intersection_id"] == "intersection-1"
    assert observation["intersection_name"] == "Cambie St & W Broadway"
    assert observation["street_names"] == ["Cambie St", "W Broadway"]
    assert observation["distance_from_destination_metres"] == 0
    assert observation["source_name"] == "City of Vancouver Open Data Portal"
    assert [view["view_id"] for view in observation["included_views"]] == ["view-east"]
    assert [view["direction_label"] for view in observation["included_views"]] == ["East"]
    assert all(view["retrieved_at"] == NOW.isoformat().replace("+00:00", "Z") for view in observation["included_views"])
    assert all(view["source_capture_at"] is None for view in observation["included_views"])
    assert len({view["sha256"] for view in observation["included_views"]}) == 1
    assert [view["view_id"] for view in observation["views"]] == ["view-east"]
    assert observation["requested_model_id"] == MODEL_ID
    assert observation["actual_provider_id"] == "CoreWeave"
    assert observation["usage"]["cost_usd"] == 0.00012
    assert service.nearest_calls == service.catalogue_calls == 1


def test_unavailable_vision_is_separate_from_existing_journey_analysis(monkeypatch, tmp_path):
    unavailable = OpenRouterVisionAdapter(api_key="", budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW))
    service, _adapter, _catalogue, _store, _selection = setup_api(monkeypatch, tmp_path, adapter=unavailable)
    failed = post("/api/cameras/observe", trip_payload())
    assert failed.status_code == 200
    assert failed.json()["observation"]["failure_code"] == "configuration_missing"

    monkeypatch.setattr("app.analysis.get_road_ahead_data", _empty_road_data)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", _empty_open511_data)
    monkeypatch.setattr("app.analysis._destination_openweather", _empty_weather)
    monkeypatch.setattr("app.analysis._destination_swob", _empty_swob)
    analysis = post("/api/trips/analyze", trip_payload())
    assert analysis.status_code == 200
    assert {"trip", "status", "findings", "drivebc_findings", "regional_events", "unmatchable_events",
            "source_statuses", "destination_weather", "summary", "analyzed_at"} <= set(analysis.json())
    assert service.nearest_calls == 1


async def _empty_road_data():
    from app.road_ahead import RoadAheadResult
    return RoadAheadResult(events=[], source_statuses=[])


async def _empty_open511_data():
    from app.drivebc_open511 import Open511Result
    from app.road_ahead import SourceStatus
    return Open511Result(events=[], source_status=SourceStatus(
        source="DriveBC Open511", dataset_id="drivebc-open511-active-unavailable",
        success=True, available=True,
    ))


async def _empty_weather(trip, evaluation_time):
    from app.analysis import _unavailable_openweather
    return _unavailable_openweather()


async def _empty_swob(trip, evaluation_time):
    from app.analysis import _unavailable_swob
    return _unavailable_swob(), []


def test_no_selected_intersection_and_no_current_frames_do_not_call_provider(monkeypatch, tmp_path):
    _service, adapter, _catalogue, _store, selection = setup_api(monkeypatch, tmp_path)
    selection.intersection = None
    selection.status = "unavailable"
    no_selection = post("/api/cameras/observe", trip_payload()).json()["observation"]
    assert no_selection["failure_code"] == "no_selected_intersection"
    assert no_selection["intersection_id"] is None
    assert adapter.budget.path.exists() is False

    _service, adapter, _catalogue, _store, selection = setup_api(monkeypatch, tmp_path / "empty", with_frames=False)
    no_frames = post("/api/cameras/observe", trip_payload()).json()["observation"]
    assert no_frames["failure_code"] == "no_eligible_frames"
    assert no_frames["intersection_id"] == "intersection-1"
    assert adapter.budget.path.exists() is False


def test_invalid_model_output_and_provider_errors_expose_only_bounded_diagnostics(monkeypatch, tmp_path):
    invalid = OpenRouterVisionAdapter(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(
            ["view-east"], valid=False,
        ))),
        budget=AttemptBudget(tmp_path / "invalid-budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    setup_api(monkeypatch, tmp_path, adapter=invalid)
    invalid_body = post("/api/cameras/observe", trip_payload()).json()
    assert invalid_body["observation"]["failure_code"] == "invalid_model_output"
    assert invalid_body["observation"]["views"] == []

    provider_failure = OpenRouterVisionAdapter(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(502, json={
            "error": {"message": "secret provider body with encoded image data"},
        })),
        budget=AttemptBudget(tmp_path / "provider-budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    setup_api(monkeypatch, tmp_path, adapter=provider_failure)
    failure_body = post("/api/cameras/observe", trip_payload()).json()
    serialized = json.dumps(failure_body)
    assert failure_body["observation"]["failure_code"] == "provider_unavailable"
    assert failure_body["provider_error"]["category"] == "other_provider_error"
    assert "secret provider body" not in serialized
    assert "encoded image data" not in serialized


def test_view_identity_mismatch_response_contains_only_integer_diagnostics(monkeypatch, tmp_path):
    returned_id = "model-invented-view-id"
    untrusted_text = "unfiltered model explanation"
    output = model_output([returned_id])
    output["views"][0]["note"] = untrusted_text
    adapter = OpenRouterVisionAdapter(
        api_key="test-key",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
            "model": MODEL_ID,
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(output)}}],
        })),
        budget=AttemptBudget(tmp_path / "mismatch-budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    setup_api(monkeypatch, tmp_path, adapter=adapter)

    response = post("/api/cameras/observe", trip_payload())
    body = response.json()
    serialized = json.dumps(body)
    assert response.status_code == 200
    assert body["semantic_error_code"] == "view_identity_or_order_mismatch"
    assert body["semantic_mismatch"] == {
        "expected_view_count": 1,
        "actual_view_count": 1,
        "first_mismatched_position": 1,
    }
    assert body["observation"]["failure_code"] == "invalid_model_output"
    assert returned_id not in serialized
    assert untrusted_text not in serialized


def test_destination_and_catalogue_identity_mismatches_stop_before_inference(monkeypatch, tmp_path):
    service, adapter, catalogue, _store, selection = setup_api(monkeypatch, tmp_path)
    other = Location(name="Other Vancouver destination", latitude=49.27, longitude=-123.12)
    service.selection = selection.model_copy(update={"destination": other})
    mismatch = post("/api/cameras/observe", trip_payload()).json()["observation"]
    assert mismatch["failure_code"] == "journey_context_mismatch"
    assert mismatch["status"] == "error"
    assert service.catalogue_calls == 0

    service, adapter, catalogue, _store, selection = setup_api(monkeypatch, tmp_path / "catalogue")
    unrelated_camera = catalogue.intersections[0].model_copy(update={"intersection_id": "different-intersection"})
    service.catalogue = catalogue.model_copy(update={"intersections": [unrelated_camera]})
    rejected = post("/api/cameras/observe", trip_payload()).json()["observation"]
    assert rejected["failure_code"] == "no_eligible_frames"
    assert rejected["views"] == []
    assert adapter.budget.path.exists() is False


def test_ordinary_camera_and_health_requests_never_start_vision(monkeypatch, tmp_path):
    service, adapter, _catalogue, _store, _selection = setup_api(monkeypatch, tmp_path)
    assert post("/api/health").json() == {"status": "ok"}
    nearest = post("/api/cameras/nearest", {"destination": DESTINATION.model_dump()})
    assert nearest.status_code == 200
    assert service.nearest_calls == 1
    assert adapter.budget.path.exists() is False


def test_observe_rejects_client_selected_intersection_model_and_image_inputs(monkeypatch, tmp_path):
    service, adapter, _catalogue, _store, _selection = setup_api(monkeypatch, tmp_path)
    body = trip_payload()
    body.update({
        "intersection_id": "client-chosen-camera",
        "image_url": "https://example.invalid/image.jpg",
        "image_bytes": "encoded-image",
        "model": "client-selected-model",
    })
    response = post("/api/cameras/observe", body)
    assert response.status_code == 422
    assert service.nearest_calls == 0
    assert adapter.budget.path.exists() is False


@pytest.mark.parametrize("has_fallback", [True, False])
def test_gallery_fallback_and_vision_share_selected_frames(monkeypatch, tmp_path, has_fallback):
    near = intersection("offline-near", 49.2827, -123.1207, count=2)
    far = intersection("fallback", 49.2830, -123.1207, count=2).model_copy(
        update={"name": "Maple St & W 4th Ave"}
    )
    offline = OFFLINE_FIXTURE.read_bytes()
    live = jpeg("green")
    clock = [NOW]
    upstream_calls = []
    provider_calls = []

    def camera_response(request):
        upstream_calls.append(request.url.path)
        is_live = has_fallback and request.url.path.endswith("-0.jpg") and "offline-near" not in request.url.path
        return httpx.Response(
            200, headers={"content-type": "image/jpeg"}, content=live if is_live else offline
        )

    def vision_response(request):
        parts = json.loads(request.content)["messages"][1]["content"]
        provider_calls.append(base64.b64decode(parts[-1]["image_url"]["url"].split(",", 1)[1]))
        return httpx.Response(200, json=provider_response(["view-0"]))

    service = images.DestinationCameraService(
        catalogue_store=FakeCatalogueStore(catalogue_result([near, far])),
        image_store=images.CameraImageStore(
            cache_dir=tmp_path / "frames", transport=httpx.MockTransport(camera_response),
            now=lambda: clock[0],
        ),
    )
    adapter = OpenRouterVisionAdapter(
        api_key="test-key", transport=httpx.MockTransport(vision_response),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    monkeypatch.setattr("app.routes.camera_service", service)
    monkeypatch.setattr("app.routes.vision_adapter", adapter)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            gallery = await client.post("/api/cameras/nearest", json={"destination": DESTINATION.model_dump()})
            assert gallery.status_code == 200
            selected = gallery.json()
            if not has_fallback:
                assert selected["status"] == "unavailable"
                assert images.SELECTION_HEADER not in gallery.headers
                response = await client.post("/api/cameras/observe", json=trip_payload())
                assert response.json()["observation"]["failure_code"] == "no_selected_intersection"
                assert len(upstream_calls) == 2
                assert not provider_calls and not adapter.budget.path.exists()
                return

            assert selected["intersection"]["intersection_id"] == far.intersection_id
            assert selected["intersection"]["official_page_url"] == far.official_page_url
            assert [view["view_id"] for view in selected["views"]] == ["view-0"]
            assert "sha256" not in selected["views"][0]
            panel_frame = await client.get(selected["views"][0]["image_reference"])
            assert panel_frame.content == live
            blocked = await client.get(images._image_reference(far.intersection_id, "view-1"))
            assert blocked.status_code == 404
            headers = {images.SELECTION_HEADER: gallery.headers[images.SELECTION_HEADER]}
            response = await client.post("/api/cameras/observe", json=trip_payload(), headers=headers)
            assert response.status_code == 200
            observation = response.json()["observation"]
            assert observation["intersection_id"] == far.intersection_id
            assert observation["intersection_name"] == selected["intersection"]["name"]
            assert observation["distance_from_destination_metres"] == selected["intersection"]["distance_metres"]
            assert observation["included_views"][0]["retrieved_at"] == selected["views"][0]["retrieved_at"]
            assert provider_calls == [live]
            assert len(upstream_calls) == 3

            clock[0] += timedelta(seconds=service.image_store.ttl_seconds)
            changed = await client.post("/api/cameras/observe", json=trip_payload(), headers=headers)
            assert changed.json()["observation"]["failure_code"] == "no_eligible_frames"
            assert provider_calls == [live]
            assert len(upstream_calls) == 3

    asyncio.run(exercise())


@pytest.mark.parametrize("change", [
    "forged", "malformed", "destination", "image_bytes", "retrieved_at", "primary_offline"
])
def test_observe_rejects_stale_or_unrelated_gallery_fingerprint(monkeypatch, tmp_path, change):
    primary = intersection("primary", DESTINATION.latitude, DESTINATION.longitude)
    fallback = intersection("fallback", DESTINATION.latitude + 0.0003, DESTINATION.longitude)
    live = jpeg("green")
    store = images.CameraImageStore(
        cache_dir=tmp_path / "frames", now=lambda: NOW,
        transport=httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"content-type": "image/jpeg"}, content=live,
        )),
    )
    provider_calls = []

    def provider(request):
        provider_calls.append(request)
        return httpx.Response(200, json=provider_response(["view-0"]))

    adapter = OpenRouterVisionAdapter(
        api_key="test-key", transport=httpx.MockTransport(provider),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    service = images.DestinationCameraService(
        catalogue_store=FakeCatalogueStore(catalogue_result([primary, fallback])), image_store=store,
    )
    monkeypatch.setattr("app.routes.camera_service", service)
    monkeypatch.setattr("app.routes.vision_adapter", adapter)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            payload = trip_payload()
            gallery = await client.post("/api/cameras/nearest", json={"destination": payload["destination"]})
            assert gallery.json()["intersection"]["intersection_id"] == primary.intersection_id
            fingerprint = gallery.headers[images.SELECTION_HEADER]
            if change == "forged":
                fingerprint = ("0" if fingerprint[0] != "0" else "1") + fingerprint[1:]
            elif change == "malformed":
                fingerprint = "not-a-fingerprint"
            elif change == "destination":
                payload["destination"]["name"] = "Another destination at the same coordinates"
            else:
                data_path, metadata_path = images._frame_paths(store.cache_dir, primary.intersection_id, "view-0")
                frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
                if change == "retrieved_at":
                    frame = frame.model_copy(update={"retrieved_at": NOW - timedelta(seconds=1)})
                elif change == "image_bytes":
                    # Keep the view and its retrieval time identical so the digest decides the match.
                    body = jpeg("blue")
                    assert body != live
                    data_path.write_bytes(body)
                    frame = frame.model_copy(update={
                        "sha256": images.hashlib.sha256(body).hexdigest(), "byte_length": len(body),
                    })
                else:
                    # Seed an equally fresh candidate with the same view ID and frame bytes.
                    # Only the intersection distinguishes its fingerprint from the original one.
                    assert await store.get_view(fallback, fallback.directional_views[0]) is not None
                    body = OFFLINE_FIXTURE.read_bytes()
                    data_path.write_bytes(body)
                    frame = frame.model_copy(update={
                        "sha256": images.hashlib.sha256(body).hexdigest(), "byte_length": len(body),
                        "width": 300, "height": 205,
                    })
                metadata_path.write_text(frame.model_dump_json())

            requests_before = store.upstream_requests
            rejected = await client.post(
                "/api/cameras/observe", json=payload, headers={images.SELECTION_HEADER: fingerprint},
            )
            assert rejected.status_code == 200
            observation = rejected.json()["observation"]
            assert observation["failure_code"] == "no_eligible_frames"
            assert observation["included_views"] == []
            assert store.upstream_requests == requests_before
            assert not provider_calls and not adapter.budget.path.exists()

            # The current selection is still valid and can reach the mocked provider.
            current = await client.post("/api/cameras/nearest", json={"destination": payload["destination"]})
            accepted = await client.post(
                "/api/cameras/observe", json=payload,
                headers={images.SELECTION_HEADER: current.headers[images.SELECTION_HEADER]},
            )
            observation = accepted.json()["observation"]
            expected_id = fallback.intersection_id if change == "primary_offline" else primary.intersection_id
            assert observation["intersection_id"] == expected_id
            assert observation["status"] == "available"
            assert len(provider_calls) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("change", ["offline", "digest"])
def test_vision_excludes_replaced_cached_view_after_selection(monkeypatch, tmp_path, change):
    service, adapter, catalogue, store, selection = setup_api(monkeypatch, tmp_path)
    camera = catalogue.intersections[0]
    view = camera.directional_views[0]
    data_path, metadata_path = images._frame_paths(store.cache_dir, camera.intersection_id, view.view_id)
    frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
    body = OFFLINE_FIXTURE.read_bytes() if change == "offline" else jpeg("green")
    width, height = (300, 205) if change == "offline" else (frame.width, frame.height)
    selected_view = selection.views[0]
    if change == "digest":
        selected_view = selected_view.model_copy(update={"sha256": frame.sha256})
    data_path.write_bytes(body)
    metadata_path.write_text(frame.model_copy(update={
        "sha256": images.hashlib.sha256(body).hexdigest(), "byte_length": len(body),
        "width": width, "height": height,
    }).model_dump_json())
    service.selection = selection.model_copy(update={"views": [selected_view]})

    result = post("/api/cameras/observe", trip_payload()).json()["observation"]
    assert result["failure_code"] == "no_eligible_frames"
    assert result["included_views"] == []
    assert not adapter.budget.path.exists()
