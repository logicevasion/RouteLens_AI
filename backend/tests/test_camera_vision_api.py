from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from io import BytesIO

import httpx
from PIL import Image

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
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(["view-east", "view-west"]))),
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


def test_observe_returns_validated_provenance_for_each_ordered_direction(monkeypatch, tmp_path):
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
    assert [view["view_id"] for view in observation["included_views"]] == ["view-east", "view-west"]
    assert [view["direction_label"] for view in observation["included_views"]] == ["East", "West"]
    assert all(view["retrieved_at"] == NOW.isoformat().replace("+00:00", "Z") for view in observation["included_views"])
    assert all(view["source_capture_at"] is None for view in observation["included_views"])
    assert len({view["sha256"] for view in observation["included_views"]}) == 2
    assert [view["view_id"] for view in observation["views"]] == ["view-east", "view-west"]
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
            ["view-east", "view-west"], valid=False,
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
