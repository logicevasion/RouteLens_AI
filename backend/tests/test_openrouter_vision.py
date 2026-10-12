from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from app import camera_images as images
from app import openrouter_vision as vision_module
from app.models import Location
from app.openrouter_vision import (
    INTRO_PROMPT,
    MODEL_ID,
    PROMPT_VERSION,
    REQUEST_TIMEOUT_SECONDS,
    AttemptBudget,
    ModelCameraObservation,
    OpenRouterVisionAdapter,
    SemanticValidationError,
    _provider_error_diagnostic,
    _semantic_validate,
)
from app.vancouver_cameras import (
    CameraCatalogue,
    CameraIntersection,
    CameraView,
    CatalogueDiagnostics,
)

NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
DESTINATION = Location(name="Downtown Vancouver", latitude=49.2827, longitude=-123.1207)


def jpeg(color: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (320, 240), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def model_output(ids: list[str], *, summary: str | None = "Pavement appears reflective.", evidence: list[str] | None = None) -> dict:
    return {
        "views": [
            {
                "view_id": view_id,
                "road_surface": "wet_looking",
                "visibility": "adequate",
                "vehicle_activity": "some_visible",
                "conditions": ["glare"],
                "uncertainty": "moderate",
                "note": "Reflective pavement is visible.",
            }
            for view_id in ids
        ],
        "intersection_summary": summary,
        "summary_evidence_view_ids": evidence if evidence is not None else (ids if summary else []),
    }


def setup_snapshot(tmp_path, *, count: int = 2, colors: tuple[str, ...] = ("red", "blue")):
    camera_views = [
        CameraView(
            view_id=f"view-{direction}", direction_label=direction.title(),
            image_url=f"https://trafficcams.vancouver.ca/cameraimages/{direction}.jpg",
            image_host="trafficcams.vancouver.ca", discovery_status="url_validated",
        )
        for direction in ("east", "west")[:count]
    ]
    camera = CameraIntersection(
        intersection_id="intersection-1", source_mapids=["1"], source_record_ids=["row-1"],
        name="Cambie St & W Broadway", source_names=["Cambie St & W Broadway"],
        latitude=DESTINATION.latitude, longitude=DESTINATION.longitude,
        official_page_url="https://trafficcams.vancouver.ca/intersection-1.htm",
        catalogue_updated_at=NOW, enrichment_checked_at=NOW,
        enrichment_status="inspected_with_views", directional_views=camera_views,
    )
    catalogue = CameraCatalogue(
        source_total_count=1, source_fetched_at=NOW, catalogue_updated_at=NOW,
        enrichment_completed_at=NOW, enrichment_complete=True, intersections=[camera],
        diagnostics=CatalogueDiagnostics(source_rows_received=1, normalized_intersections=1, source_total_count=1),
    )
    selected_views = []
    store = images.CameraImageStore(cache_dir=tmp_path / "frames", now=lambda: NOW)
    for index, view in enumerate(camera_views):
        body = jpeg(colors[index])
        frame = images.StoredFrame(
            intersection_id=camera.intersection_id, view_id=view.view_id, source_url=view.image_url,
            retrieved_at=NOW, content_type="image/jpeg", width=320, height=240,
            byte_length=len(body), sha256=images.hashlib.sha256(body).hexdigest(),
        )
        image_path, metadata_path = images._frame_paths(store.cache_dir, camera.intersection_id, view.view_id)
        images._atomic_write(image_path, body)
        images._atomic_write(metadata_path, frame.model_dump_json().encode())
        selected_views.append(images.CameraImageViewResult(
            view_id=view.view_id, direction_label=view.direction_label,
            image_reference=f"/api/cameras/images/{index:032d}", retrieved_at=NOW,
            source_capture_at=None, cache_age_seconds=0, stale=False,
            width=320, height=240, content_type="image/jpeg",
        ))
    selected_intersection = images.CameraIntersectionResult(
        intersection_id=camera.intersection_id, name=camera.name, latitude=camera.latitude,
        longitude=camera.longitude, distance_metres=0,
        official_page_url=camera.official_page_url,
    )
    selection = images.DestinationCameraResult(
        destination=DESTINATION, status="available", intersection=selected_intersection,
        views=selected_views, diagnostics=images.CameraDiagnostics(views_succeeded=count),
    )
    return camera, catalogue, store, selection


def provider_response(ids: list[str], *, model: str = MODEL_ID, provider: str | None = "DeepInfra", content=None, finish: str = "stop"):
    response = {
        "model": model,
        "choices": [{"finish_reason": finish, "message": {"content": json.dumps(content or model_output(ids))}}],
        "usage": {"prompt_tokens": 400, "completion_tokens": 100, "total_tokens": 500, "cost": 0.00012},
    }
    if provider is not None:
        response["provider"] = provider
    return response


def test_model_schema_and_order_validation_for_one_four_and_five_views():
    for count in (1, 4, 5):
        ids = [f"view-{index}" for index in range(count)]
        parsed = ModelCameraObservation.model_validate(model_output(ids))
        _semantic_validate(parsed, ids)


def test_prompt_requires_exact_ordered_identity_and_includes_unclear_views(tmp_path, monkeypatch):
    assert PROMPT_VERSION == "camera-visual-observer-v2"
    for instruction in (
        "exactly one view observation for every submitted image",
        "exact submitted order",
        "copy each supplied view_id character-for-character",
        "never invent, abbreviate, normalize, or rename an ID",
        "Never omit a view when conditions are unclear",
        "unclear or not_observable",
        "corresponding labeled image",
    ):
        assert instruction.lower() in INTRO_PROMPT.lower()

    camera, _, store, _ = setup_snapshot(tmp_path)
    included = []
    for view in camera.directional_views:
        cached = images.read_current_cached_frame(store, camera, view)
        assert cached is not None
        frame, body = cached
        included.append((view, frame, body))
    before = vision_module.OpenRouterVisionAdapter._snapshot_identity("intersection-1", included)
    monkeypatch.setattr(vision_module, "PROMPT_VERSION", "camera-visual-observer-v3")
    after = vision_module.OpenRouterVisionAdapter._snapshot_identity("intersection-1", included)
    assert before != after


@pytest.mark.parametrize(
    ("ids", "first_position"),
    [(["view-a", "view-x"], 2), (["view-a", "view-a"], 2), (["view-b", "view-a"], 1), (["view-a"], 2)],
)
def test_rejects_unknown_duplicate_omitted_and_out_of_order_views(ids, first_position):
    parsed = ModelCameraObservation.model_validate(model_output(ids, evidence=["view-a", "view-b"]))
    with pytest.raises(SemanticValidationError) as exc_info:
        _semantic_validate(parsed, ["view-a", "view-b"])
    assert exc_info.value.code == "view_identity_or_order_mismatch"
    assert exc_info.value.expected_view_count == 2
    assert exc_info.value.actual_view_count == len(ids)
    assert exc_info.value.first_mismatched_position == first_position


def test_strict_schema_rejects_extra_fields_enums_lengths_and_duplicate_tags():
    value = model_output(["view-a"])
    value["unexpected"] = True
    with pytest.raises(ValidationError):
        ModelCameraObservation.model_validate(value)
    for key, invalid in (("road_surface", "wet"), ("note", "x" * 161)):
        value = model_output(["view-a"])
        value["views"][0][key] = invalid
        with pytest.raises(ValidationError):
            ModelCameraObservation.model_validate(value)
    value = model_output(["view-a"])
    value["views"][0]["conditions"] = ["glare", "glare"]
    with pytest.raises(ValidationError):
        ModelCameraObservation.model_validate(value)
    value = model_output(["view-a"])
    value["intersection_summary"] = "x" * 241
    with pytest.raises(ValidationError):
        ModelCameraObservation.model_validate(value)


def test_semantic_failures_have_fixed_codes_and_visibility_is_independent():
    value = ModelCameraObservation.model_validate(model_output(["view-a"], summary=None, evidence=[]))
    _semantic_validate(value, ["view-a"])
    value = model_output(["view-a"], summary="Claim", evidence=[])
    with pytest.raises(SemanticValidationError) as exc_info:
        _semantic_validate(ModelCameraObservation.model_validate(value), ["view-a"])
    assert exc_info.value.code == "summary_evidence_relationship_invalid"

    value = model_output(["view-a"])
    value["summary_evidence_view_ids"] = ["excluded-view"]
    with pytest.raises(SemanticValidationError) as exc_info:
        _semantic_validate(ModelCameraObservation.model_validate(value), ["view-a"])
    assert exc_info.value.code == "unknown_summary_evidence_view"

    value = model_output(["view-a"], summary=None, evidence=["view-a"])
    with pytest.raises(SemanticValidationError) as exc_info:
        _semantic_validate(ModelCameraObservation.model_validate(value), ["view-a"])
    assert exc_info.value.code == "summary_evidence_relationship_invalid"

    value = model_output(["view-a"])
    value["views"][0].update(visibility="not_observable", road_surface="wet_looking")
    _semantic_validate(ModelCameraObservation.model_validate(value), ["view-a"])


def test_one_ordered_single_image_request_uses_automatic_provider_selection(tmp_path):
    camera, catalogue, store, selection = setup_snapshot(tmp_path)
    selection = selection.model_copy(update={"views": list(reversed(selection.views))})
    _, east_metadata_path = images._frame_paths(store.cache_dir, camera.intersection_id, "view-east")
    east_frame = images.StoredFrame.model_validate_json(east_metadata_path.read_text())
    east_metadata_path.write_text(east_frame.model_copy(update={"retrieved_at": NOW - timedelta(seconds=200)}).model_dump_json())
    captured = []

    def handler(request: httpx.Request):
        payload = json.loads(request.content)
        captured.append((payload, request.extensions["timeout"]))
        return httpx.Response(200, json=provider_response(["view-east"]))

    adapter = OpenRouterVisionAdapter(
        api_key="test-secret", transport=httpx.MockTransport(handler),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW,
    )
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.status == "available"
    assert result.observation.distance_from_destination_metres == 0
    assert result.observation.street_names == ["Cambie St", "W Broadway"]
    assert result.observation.included_views[0].source_capture_at is None
    assert result.observation.usage.cost_usd == 0.00012
    assert result.observation.actual_endpoint_id is None
    payload, timeouts = captured[0]
    assert REQUEST_TIMEOUT_SECONDS == 60.0
    assert set(timeouts.values()) == {60.0}
    assert payload["model"] == MODEL_ID
    assert payload["max_tokens"] == 1024
    assert payload["response_format"]["json_schema"]["strict"] is True
    provider = payload["provider"]
    assert provider == {
        "allow_fallbacks": True, "require_parameters": True,
    }
    assert "data_collection" not in provider
    assert "zdr" not in provider
    assert "only" not in provider
    assert "quantizations" not in provider
    parts = payload["messages"][1]["content"]
    assert [part["type"] for part in parts] == ["text", "text", "image_url"]
    assert "view_id=view-east; direction=East" == parts[1]["text"]
    assert base64.b64decode(parts[2]["image_url"]["url"].split(",", 1)[1]) == jpeg("red")
    assert [view.view_id for view in result.observation.included_views] == ["view-east"]
    assert [view.view_id for view in result.observation.views] == ["view-east"]
    _semantic_validate(ModelCameraObservation.model_validate(model_output(["view-east"])), ["view-east"])


@pytest.mark.parametrize(
    ("earlier_frame_state", "expected_reason"),
    [("missing", "missing"), ("invalid", "invalid_or_mismatched"), ("stale", "stale"), ("oversized", "oversized")],
)
def test_skips_ineligible_earlier_catalogue_view_for_next_eligible(earlier_frame_state, expected_reason, tmp_path, monkeypatch):
    camera, catalogue, store, selection = setup_snapshot(tmp_path)
    image_path, metadata_path = images._frame_paths(store.cache_dir, camera.intersection_id, "view-east")
    if earlier_frame_state == "missing":
        image_path.unlink()
        metadata_path.unlink()
    elif earlier_frame_state == "invalid":
        frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
        metadata_path.write_text(frame.model_copy(update={"sha256": "f" * 64}).model_dump_json())
    elif earlier_frame_state == "stale":
        frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
        metadata_path.write_text(frame.model_copy(update={"retrieved_at": NOW - timedelta(seconds=store.ttl_seconds)}).model_dump_json())
    else:
        def replace_body(view_id: str, body: bytes) -> int:
            data_path, meta_path = images._frame_paths(store.cache_dir, camera.intersection_id, view_id)
            frame = images.StoredFrame.model_validate_json(meta_path.read_text())
            images._atomic_write(data_path, body)
            images._atomic_write(meta_path, frame.model_copy(update={
                "byte_length": len(body), "sha256": images.hashlib.sha256(body).hexdigest(),
            }).model_dump_json().encode())
            return len(body)

        noisy = bytes((index * 37) % 256 for index in range(320 * 240 * 3))
        noisy_image = Image.frombytes("RGB", (320, 240), noisy)
        large_buffer = BytesIO()
        noisy_image.save(large_buffer, format="JPEG", quality=95)
        east_size = replace_body("view-east", large_buffer.getvalue())
        small_buffer = BytesIO()
        Image.new("RGB", (320, 240), "white").save(small_buffer, format="JPEG", quality=10, optimize=True)
        west_size = replace_body("view-west", small_buffer.getvalue())
        assert east_size > west_size
        monkeypatch.setattr("app.openrouter_vision.MAX_FRAME_BYTES", west_size + 1)

    captured = []

    def handler(request):
        payload = json.loads(request.content)
        captured.append(payload)
        return httpx.Response(200, json=provider_response(["view-west"]))

    result = asyncio.run(OpenRouterVisionAdapter(
        api_key="test", transport=httpx.MockTransport(handler),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW,
    ).analyze_selected_intersection(selection, catalogue, store))

    content = captured[0]["messages"][1]["content"]
    assert result.observation.status == "partial"
    assert [view.view_id for view in result.observation.included_views] == ["view-west"]
    assert [view.view_id for view in result.observation.views] == ["view-west"]
    assert [(view.view_id, view.reason) for view in result.observation.excluded_views] == [("view-east", expected_reason)]
    assert [part["type"] for part in content] == ["text", "text", "image_url"]
    assert content[1]["text"] == "view_id=view-west; direction=West"


def test_snapshot_identity_depends_on_selected_frame_and_model_prompt_schema(tmp_path, monkeypatch):
    camera, _, store, _ = setup_snapshot(tmp_path)
    included = []
    for view in camera.directional_views[:1]:
        cached = images.read_current_cached_frame(store, camera, view)
        assert cached is not None
        frame, body = cached
        included.append((view, frame, body))
    adapter = OpenRouterVisionAdapter
    base = adapter._snapshot_identity(camera.intersection_id, included)
    for constant, changed in (("MODEL_ID", "another/model"), ("PROMPT_VERSION", "another-prompt"), ("SCHEMA_VERSION", "another-schema")):
        monkeypatch.setattr(vision_module, constant, changed)
        assert adapter._snapshot_identity(camera.intersection_id, included) != base
        monkeypatch.undo()
    west = camera.directional_views[1]
    cached_west = images.read_current_cached_frame(store, camera, west)
    assert cached_west is not None
    frame, body = cached_west
    assert adapter._snapshot_identity(camera.intersection_id, [(west, frame, body)]) != base


def test_identical_snapshot_reuse_and_frame_change_invalidates(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=provider_response(["view-east"]))

    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    first = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    second = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert calls == 1 and second.cache_reused
    image_path, _ = images._frame_paths(store.cache_dir, "intersection-1", "view-east")
    replacement = jpeg("green")
    image_path.write_bytes(replacement)
    metadata_path = images._frame_paths(store.cache_dir, "intersection-1", "view-east")[1]
    frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
    frame = frame.model_copy(update={"sha256": images.hashlib.sha256(replacement).hexdigest(), "byte_length": len(replacement)})
    metadata_path.write_text(frame.model_dump_json())
    third = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert calls == 2 and not third.cache_reused
    assert first.observation.included_views[0].sha256 != third.observation.included_views[0].sha256


def test_expired_underlying_frame_prevents_result_reuse(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path, count=1)
    clock = [NOW]
    store.now = lambda: clock[0]
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=provider_response(["view-east"]))

    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: clock[0])
    first = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert first.observation.status == "available"
    clock[0] += timedelta(seconds=301)
    expired = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert calls == 1
    assert expired.observation.failure_code == "stale_frames_only"


@pytest.mark.parametrize("finish,content", [("length", model_output(["view-east", "view-west"])), ("stop", None)])
def test_truncation_and_missing_content_are_invalid_without_retry(tmp_path, finish, content):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if content is None:
            response = provider_response([], content={})
            response["choices"][0]["message"]["content"] = None
        else:
            response = provider_response(["view-east", "view-west"], content=content, finish=finish)
        return httpx.Response(200, json=response)

    result = asyncio.run(OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "invalid_model_output"
    assert calls == 1


def test_adapter_returns_only_fixed_semantic_diagnostic_code(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    unsafe_detail = "provider-private-view-id"

    def handler(request):
        output = model_output([unsafe_detail, "view-west"])
        output["views"][0]["note"] = "private model response phrase"
        return httpx.Response(200, json=provider_response([], content=output))

    result = asyncio.run(
        OpenRouterVisionAdapter(
            api_key="test",
            transport=httpx.MockTransport(handler),
            budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW),
            now=lambda: NOW,
        ).analyze_selected_intersection(selection, catalogue, store)
    )
    assert result.observation.failure_code == "invalid_model_output"
    assert result.semantic_error_code == "view_identity_or_order_mismatch"
    assert result.semantic_mismatch.model_dump(mode="json") == {
        "expected_view_count": 1, "actual_view_count": 2, "first_mismatched_position": 1,
    }
    serialized = str(result.model_dump(mode="json"))
    assert unsafe_detail not in serialized
    assert "private model response phrase" not in serialized


@pytest.mark.parametrize("kind", ["malformed_json", "refusal"])
def test_malformed_json_and_refusal_are_rejected_without_retry(tmp_path, kind):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        response = provider_response(["view-east", "view-west"])
        if kind == "malformed_json":
            response["choices"][0]["message"]["content"] = "{truncated"
        else:
            response["choices"][0]["message"]["refusal"] = "refused"
        return httpx.Response(200, json=response)

    result = asyncio.run(OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "invalid_model_output"
    assert calls == 1


@pytest.mark.parametrize(
    ("provider", "expected_provider"),
    [("OtherProvider", "OtherProvider"), (None, None), ("CoreWeave\nBearer secret", None)],
)
def test_accepts_automatic_provider_and_preserves_safe_identity_or_unknown(tmp_path, provider, expected_provider):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(["view-east"], provider=provider))), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.status == "available"
    assert result.observation.actual_provider_id == expected_provider


def test_rejects_model_substitution(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(["view-east"], model="other/model"))), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "provider_error"


@pytest.mark.parametrize(
    ("status", "envelope", "expected_category", "expected_code"),
    [
        (404, {"error": {"code": 404, "message": "No endpoints found matching your data policy"}}, "no_eligible_provider", 404),
        (404, {"error": {"code": "model_not_allowed", "message": "Model is not allowed for this account"}}, "account_model_provider_restriction", "model_not_allowed"),
        (400, {"error": {"code": 400, "message": "Unsupported parameter: response_format"}}, "unsupported_request_parameters", 400),
        (404, {"error": {"code": 404, "message": "Model not found"}}, "invalid_model_or_provider_identifier", 404),
        (502, {"error": {"code": 502, "message": "upstream rejected request"}}, "other_provider_error", 502),
        (404, {"error": {"message": "opaque failure"}}, "other_provider_error", None),
    ],
)
def test_provider_error_diagnostic_classifies_safe_known_categories(status, envelope, expected_category, expected_code):
    diagnostic = _provider_error_diagnostic(httpx.Response(status, json=envelope))
    assert diagnostic.http_status == status
    assert diagnostic.error_code == expected_code
    assert diagnostic.category == expected_category
    assert diagnostic.explanation is not None
    if expected_category == "no_eligible_provider":
        assert diagnostic.explanation == "No provider matched the request's routing constraints."
        assert "privacy" not in diagnostic.explanation
    assert envelope["error"]["message"] not in diagnostic.explanation


def test_provider_error_diagnostic_preserves_unknown_and_never_echoes_untrusted_text():
    untrusted = "private image data:image/jpeg;base64,AAECAw== Bearer sk-secret-value"
    response = httpx.Response(404, json={"error": {"code": "code with spaces", "message": untrusted}})
    diagnostic = _provider_error_diagnostic(response)
    rendered = diagnostic.model_dump_json()
    assert diagnostic.http_status == 404
    assert diagnostic.error_code is None
    assert diagnostic.category == "other_provider_error"
    assert untrusted not in rendered
    assert "AAECAw==" not in rendered
    assert "sk-secret-value" not in rendered


def test_provider_error_diagnostic_handles_unstructured_and_malformed_bodies():
    responses = (
        httpx.Response(404, text="raw upstream message"),
        httpx.Response(404, json={"message": "not nested under error"}),
        httpx.Response(404, json={"error": {"code": {"unexpected": True}}}),
    )
    for response in responses:
        diagnostic = _provider_error_diagnostic(response)
        assert diagnostic.http_status == 404
        assert diagnostic.error_code is None
        assert diagnostic.category == "unknown"
        assert diagnostic.explanation is None


def test_adapter_attaches_only_sanitized_provider_diagnostic(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    untrusted = "No endpoints found; echoed private data:image/jpeg;base64,AAECAw=="
    body = {"error": {"code": 404, "message": untrusted}}
    adapter = OpenRouterVisionAdapter(
        api_key="test-secret",
        transport=httpx.MockTransport(lambda _request: httpx.Response(404, json=body)),
        budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW),
        now=lambda: NOW,
    )
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    rendered = result.model_dump_json()
    assert result.observation.failure_code == "provider_error"
    assert result.provider_error is not None
    assert result.provider_error.http_status == 404
    assert result.provider_error.error_code == 404
    assert result.provider_error.category == "no_eligible_provider"
    assert untrusted not in rendered
    assert "AAECAw==" not in rendered


def test_no_eligible_images_makes_no_provider_call_and_no_image_fetch(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    for view in catalogue.intersections[0].directional_views:
        image_path, metadata_path = images._frame_paths(store.cache_dir, "intersection-1", view.view_id)
        image_path.unlink()
        metadata_path.unlink()
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: pytest.fail("provider called")), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "no_eligible_frames"
    assert store.upstream_requests == 0


def test_snapshot_byte_ceiling_and_intersection_identity_fail_closed(tmp_path, monkeypatch):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    monkeypatch.setattr("app.openrouter_vision.MAX_TOTAL_IMAGE_BYTES", 1)
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: pytest.fail("provider called")), budget=AttemptBudget(tmp_path / "budget-overflow.json", now=lambda: NOW), now=lambda: NOW)
    overflow = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert overflow.observation.failure_code == "no_eligible_frames"

    wrong_camera = catalogue.intersections[0].model_copy(update={"intersection_id": "another-intersection"})
    wrong_catalogue = catalogue.model_copy(update={"intersections": [wrong_camera]})
    mismatch = asyncio.run(adapter.analyze_selected_intersection(selection, wrong_catalogue, store))
    assert mismatch.observation.failure_code == "no_eligible_frames"


def test_oversized_individual_frame_is_excluded_with_reason(tmp_path, monkeypatch):
    _, catalogue, store, selection = setup_snapshot(tmp_path, count=1)
    monkeypatch.setattr("app.openrouter_vision.MAX_FRAME_BYTES", 10)
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: pytest.fail("provider called")), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "no_eligible_frames"
    assert [(view.view_id, view.reason) for view in result.observation.excluded_views] == [("view-east", "oversized")]


def test_corrupt_cached_image_is_excluded_without_provider_call(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path, count=1)
    image_path, _ = images._frame_paths(store.cache_dir, "intersection-1", "view-east")
    image_path.write_bytes(b"not-an-image")
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: pytest.fail("provider called")), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "no_eligible_frames"
    assert [(view.view_id, view.reason) for view in result.observation.excluded_views] == [("view-east", "invalid_or_mismatched")]


def test_stale_frame_is_excluded_and_empty_stale_snapshot_has_explicit_status(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path, count=1)
    image_path, metadata_path = images._frame_paths(store.cache_dir, "intersection-1", "view-east")
    frame = images.StoredFrame.model_validate_json(metadata_path.read_text())
    metadata_path.write_text(frame.model_copy(update={"retrieved_at": NOW - timedelta(seconds=301)}).model_dump_json())
    stale_selection = selection.model_copy(update={"status": "stale", "views": [], "stale_views": selection.views})
    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: pytest.fail("provider called")), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.analyze_selected_intersection(stale_selection, catalogue, store))
    assert result.observation.failure_code == "stale_frames_only"
    assert image_path.exists()


def test_missing_credentials_and_http_failures_are_sanitized_and_counted(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    missing = asyncio.run(OpenRouterVisionAdapter(api_key="", budget=AttemptBudget(tmp_path / "budget-missing.json", now=lambda: NOW)).analyze_selected_intersection(selection, catalogue, store))
    assert missing.observation.failure_code == "configuration_missing"

    budget = AttemptBudget(tmp_path / "budget.json", now=lambda: NOW)
    adapter = OpenRouterVisionAdapter(api_key="test-secret", transport=httpx.MockTransport(lambda request: httpx.Response(503, text="secret payload and private image")), budget=budget, now=lambda: NOW)
    failed = asyncio.run(adapter.analyze_selected_intersection(selection, catalogue, store))
    assert failed.observation.failure_code == "provider_unavailable"
    assert "secret" not in failed.model_dump_json()
    assert json.loads((tmp_path / "budget.json").read_text())["attempts"]


def test_http_429_is_rate_limited_and_attempted_once(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    budget_path = tmp_path / "budget.json"
    result = asyncio.run(
        OpenRouterVisionAdapter(
            api_key="test",
            transport=httpx.MockTransport(lambda request: httpx.Response(429, text="private rate detail")),
            budget=AttemptBudget(budget_path, now=lambda: NOW),
            now=lambda: NOW,
        ).analyze_selected_intersection(selection, catalogue, store)
    )
    assert result.observation.failure_code == "rate_limited"
    assert len(json.loads(budget_path.read_text())["attempts"]) == 1


def test_transport_timeout_maps_to_controlled_status_and_attempt_is_counted(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)

    def handler(request):
        raise httpx.ReadTimeout("secret timeout detail")

    budget_path = tmp_path / "budget.json"
    result = asyncio.run(OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(budget_path, now=lambda: NOW), now=lambda: NOW).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "timeout"
    assert len(json.loads(budget_path.read_text())["attempts"]) == 1


def test_adapter_outer_deadline_maps_slow_transport_to_timeout_once(tmp_path, monkeypatch):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    monkeypatch.setattr("app.openrouter_vision.REQUEST_TIMEOUT_SECONDS", 0.005)
    calls = 0

    class SlowTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.05)
            return httpx.Response(200, json=provider_response(["view-east"]), request=request)

    budget_path = tmp_path / "slow-budget.json"
    result = asyncio.run(OpenRouterVisionAdapter(
        api_key="test", transport=SlowTransport(),
        budget=AttemptBudget(budget_path, now=lambda: NOW), now=lambda: NOW,
    ).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "timeout"
    assert calls == 1
    assert len(json.loads(budget_path.read_text())["attempts"]) == 1


def test_provider_reported_output_above_ceiling_is_rejected(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    response = provider_response(["view-east"])
    response["usage"]["completion_tokens"] = 1025
    result = asyncio.run(OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.failure_code == "invalid_model_output"


def test_concurrent_identical_calls_share_one_inflight_request(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=provider_response(["view-east"]))

    adapter = OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(handler), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW)

    async def execute():
        return await asyncio.gather(
            adapter.analyze_selected_intersection(selection, catalogue, store),
            adapter.analyze_selected_intersection(selection, catalogue, store),
        )

    first, second = asyncio.run(execute())
    assert calls == 1
    assert first.observation == second.observation


def test_budget_rolls_hour_and_day_and_corrupt_state_fails_closed(tmp_path):
    now = [NOW]
    budget = AttemptBudget(tmp_path / "budget.json", now=lambda: now[0])
    assert all(budget.reserve() for _ in range(50))
    assert not budget.reserve()
    now[0] += timedelta(hours=1, seconds=1)
    assert not budget.reserve()  # Soft daily estimate is tighter than the hard daily attempt ceiling.
    now[0] += timedelta(days=1)
    assert budget.reserve()
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("not json")
    assert not AttemptBudget(corrupt, now=lambda: now[0]).reserve()
    corrupt.write_text('{"attempts": [], "estimated_project_usd": NaN, "estimated_daily": {}}')
    assert not AttemptBudget(corrupt, now=lambda: now[0]).reserve()


def test_utc_daily_attempt_ceiling_is_independent_of_hourly_ceiling(tmp_path, monkeypatch):
    monkeypatch.setattr("app.openrouter_vision.ESTIMATED_USD_PER_ATTEMPT", 0.0)
    now = [NOW]
    budget = AttemptBudget(tmp_path / "budget.json", now=lambda: now[0])
    for _ in range(50):
        assert budget.reserve()
    now[0] += timedelta(hours=1, seconds=1)
    for _ in range(50):
        assert budget.reserve()
    assert not budget.reserve()


def test_single_eligible_frame_retains_provenance(tmp_path):
    _, catalogue, store, selection = setup_snapshot(tmp_path)
    image_path, metadata_path = images._frame_paths(store.cache_dir, "intersection-1", "view-west")
    image_path.unlink()
    metadata_path.unlink()
    result = asyncio.run(OpenRouterVisionAdapter(api_key="test", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=provider_response(["view-east"]))), budget=AttemptBudget(tmp_path / "budget.json", now=lambda: NOW), now=lambda: NOW).analyze_selected_intersection(selection, catalogue, store))
    assert result.observation.status == "available"
    assert [view.view_id for view in result.observation.included_views] == ["view-east"]
    assert [view.view_id for view in result.observation.views] == ["view-east"]
    assert result.observation.excluded_views == []
