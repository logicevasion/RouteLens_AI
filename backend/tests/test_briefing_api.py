from __future__ import annotations

import asyncio
import copy
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from app.briefing_contracts import BriefingEvidenceRequestV1, ModelBriefingOutputV1
from app.main import app
from app.openrouter_briefing import (
    CHAT_COMPLETIONS_URL,
    ESTIMATED_USD_PER_ATTEMPT,
    MODEL_ID,
    SYSTEM_PROMPT,
    BriefingAttemptBudget,
    OpenRouterBriefingAdapter,
    _select_topics,
    wire_schema,
)

NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)


def request_payload() -> dict:
    timestamp = NOW.isoformat()
    return {
        "request_schema_version": "journey-briefing-request-v1",
        "bundle_schema_version": "journey-evidence-v1",
        "attempt_id": 17,
        "assembled_at": timestamp,
        "analyzed_at": timestamp,
        "analysis_status": "success",
        "journey": {
            "mode": "drive",
            "origin": {"name": "Richmond", "latitude": 49.163168, "longitude": -123.137414},
            "destination": {"name": "Downtown Vancouver", "latitude": 49.2827, "longitude": -123.1207},
            "route": {"candidate_id": "route-2", "label": "Alternative 2", "distance_meters": 7100.0},
        },
        "sources": {
            "road_ahead": {"availability": "available", "statuses": [{"source": "Road Ahead", "dataset_id": "road-ahead", "success": True, "available": True, "fetched_at": timestamp, "stale": False, "cache_stale": False}], "findings": [{
                "source_id": "event-7", "event_type": "construction", "title": "Road work", "description": "Lane work reported.",
                "classification": "nearby", "distance_meters": 90.0, "location": "Main Street",
                "severity": None, "status": "active", "schedule_text": None, "restriction_text": None,
                "observed_at": None, "updated_at": timestamp, "direction_assessment": None,
                "temporal_applicability": None, "current_impact": None, "geometry_basis": None,
            }], "omitted_count": 0},
            "drivebc_open511": {"availability": "empty", "status": {"source": "DriveBC Open511", "dataset_id": "open511", "success": True, "available": True, "fetched_at": timestamp, "stale": False, "cache_stale": False}, "findings": [], "omitted_count": 0},
            "openweather_current": {"availability": "unknown", "status": None, "observation": None},
            "openweather_forecast": {"availability": "unknown", "status": None, "coverage": None, "intervals": [], "omitted_count": 0},
            "eccc_swob": {"availability": "unknown", "status": None, "attribution": None, "observations": [], "omitted_count": 0},
            "camera_vision": {"availability": "pending", "observation_status": "pending", "observation": None},
        },
    }


def add_camera(payload: dict, *, captured_at: datetime = NOW, uncertainty: str = "low", note: str | None = None,
               distance: float = 50.0, road_surface: str = "dry_looking") -> dict:
    payload["sources"]["camera_vision"].update(availability="available", observation_status="available", observation={
        "status": "available", "intersection_name": "Richards and Helmcken", "street_names": ["Richards", "Helmcken"],
        "distance_from_destination_meters": distance, "source_name": "City of Vancouver",
        "direction_view": {"view_id": "view:e700a502c4ccdff685e9", "direction_label": "East", "retrieved_at": captured_at.isoformat(),
                           "source_capture_at": captured_at.isoformat(), "road_surface": road_surface, "visibility": "adequate",
                           "vehicle_activity": "some_visible", "conditions": [], "uncertainty": uncertainty, "note": note},
        "summary": None, "summary_evidence_view_ids": [],
    })
    return payload


def add_current_weather(payload: dict, *, observed_at: datetime = NOW, group: str = "clear", stale: bool = False) -> dict:
    payload["sources"]["openweather_current"].update(
        availability="available", status={"source": "OpenWeather", "dataset_id": "onecall4_current", "success": True,
        "available": True, "fetched_at": NOW.isoformat(), "stale": stale, "cache_stale": False},
        observation={"source": "OpenWeather", "product": "onecall4_current", "observed_at": observed_at.isoformat(), "fetched_at": NOW.isoformat(),
                     "condition": {"code": 800, "group": group, "description": group}, "temperature_c": None,
                     "feels_like_c": None, "humidity_pct": None, "wind_speed_m_s": None, "wind_direction_deg": None,
                     "wind_gust_m_s": None, "visibility_m": None, "rain_1h_mm": 0.0, "snow_1h_mm": 0.0},
    )
    return payload


def add_forecast(payload: dict, forecast_at: datetime, *, group: str = "rain") -> dict:
    interval = {"source": "OpenWeather", "product": "onecall4_timeline_15min", "forecast_at": forecast_at.isoformat(),
                "fetched_at": NOW.isoformat(), "condition": {"code": 500, "group": group, "description": group},
                "precipitation_probability_pct": 70.0, "temperature_c": None, "feels_like_c": None,
                "humidity_pct": None, "wind_speed_m_s": None, "wind_direction_deg": None, "wind_gust_m_s": None,
                "visibility_m": None, "rain_1h_mm": 0.2, "rain_3h_mm": None, "snow_1h_mm": None, "snow_3h_mm": None}
    payload["sources"]["openweather_forecast"].update(
        availability="available", status={"source": "OpenWeather", "dataset_id": "onecall4_timeline_15min", "success": True,
        "available": True, "fetched_at": NOW.isoformat(), "stale": False, "cache_stale": False},
        coverage={"continuous": True, "expected_interval_count": 1, "returned_interval_count": 1,
                  "first_interval_at": forecast_at.isoformat(), "last_interval_at": forecast_at.isoformat()},
        intervals=[interval], omitted_count=0,
    )
    return payload


def valid_request(payload: dict | None = None) -> BriefingEvidenceRequestV1:
    return BriefingEvidenceRequestV1.model_validate_json(json.dumps(payload or request_payload()))


def completion(*, status: int = 200, content: str | None = None,
               finish_reason: str | None = "stop", output_tokens: int = 30) -> httpx.Response:
    if content is None:
        content = json.dumps({"status": "available", "overview": "Road work is reported nearby.",
                              "camera_text": "", "weather_text": "",
                              "construction_text": "Construction is reported nearby."})
    body = {"model": MODEL_ID, "provider": "TestProvider", "choices": [{
        "finish_reason": finish_reason, "message": {"content": content}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": output_tokens,
                  "total_tokens": 120 + output_tokens, "cost": 0.0001}}
    return httpx.Response(status, json=body)


def api_post(body: bytes) -> httpx.Response:
    async def call():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/briefings/generate", content=body, headers={"content-type": "application/json"})
    return asyncio.run(call())


def too_many_road_records(payload: dict) -> None:
    template = payload["sources"]["road_ahead"]["findings"][0]
    payload["sources"]["road_ahead"]["findings"] = [
        {**copy.deepcopy(template), "source_id": f"event-{index}"} for index in range(13)
    ]


def duplicate_road_identity(payload: dict) -> None:
    finding = copy.deepcopy(payload["sources"]["road_ahead"]["findings"][0])
    payload["sources"]["road_ahead"]["findings"].append(finding)


def test_valid_request_generates_typed_result_and_fixed_provider_request(tmp_path):
    seen: list[httpx.Request] = []
    def handler(request: httpx.Request):
        seen.append(request)
        return completion()
    adapter = OpenRouterBriefingAdapter(api_key="test-secret", transport=httpx.MockTransport(handler),
                                        budget=BriefingAttemptBudget(tmp_path / "budget.json", vision_path=tmp_path / "missing.json", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request()))
    sent = json.loads(seen[0].content)
    assert result.status == "available"
    assert result.overview_evidence_refs == ["ra-event-7"]
    assert result.requested_model == MODEL_ID and result.returned_model == MODEL_ID
    assert result.provider == "TestProvider" and result.usage.cost_usd == 0.0001
    assert str(seen[0].url) == CHAT_COMPLETIONS_URL
    assert sent["model"] == MODEL_ID and sent["stream"] is False and sent["max_tokens"] == 1024
    assert sent["provider"] == {"require_parameters": True}
    assert sent["response_format"]["type"] == "json_schema"
    assert "additionalProperties" not in str(wire_schema()) or wire_schema()["additionalProperties"] is False
    assert len(seen) == 1


def test_completed_json_with_usage_above_old_limit_is_accepted_once(tmp_path):
    seen: list[httpx.Request] = []
    adapter = OpenRouterBriefingAdapter(
        api_key="test-secret",
        transport=httpx.MockTransport(lambda request: (seen.append(request), completion(output_tokens=900))[1]),
        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "missing.json", now=lambda: NOW),
        now=lambda: NOW,
    )

    result = asyncio.run(adapter.generate(valid_request()))

    assert result.status == "available"
    assert result.usage.output_tokens == 900
    assert len(seen) == 1


def test_valid_partial_empty_sources_and_pending_camera_are_accepted():
    payload = request_payload()
    payload["sources"]["road_ahead"]["availability"] = "empty"
    payload["sources"]["road_ahead"]["findings"] = []
    payload["sources"]["drivebc_open511"]["availability"] = "empty"
    request = valid_request(payload)
    assert request.has_usable_evidence()
    assert "ra-status" in request.allowed_evidence_refs()
    assert request.sources.camera_vision.observation_status == "pending"


def test_empty_road_sources_do_not_become_false_all_clear(tmp_path):
    payload = request_payload()
    payload["sources"]["road_ahead"]["availability"] = "empty"
    payload["sources"]["road_ahead"]["findings"] = []
    payload["sources"]["drivebc_open511"]["availability"] = "empty"
    payload["sources"]["drivebc_open511"]["findings"] = []
    empty_report = json.dumps({"status": "available", "overview": "Both official road sources returned empty findings in this snapshot.",
                               "camera_text": "", "weather_text": "", "construction_text": ""})
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: completion(content=empty_report)),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request(payload)))
    assert result.status == "available"
    assert "clear" not in result.overview.casefold()
    assert result.overview_evidence_refs


def test_no_usable_evidence_skips_provider(tmp_path):
    payload = request_payload()
    for section in payload["sources"].values():
        section["availability"] = "unknown"
        if "findings" in section:
            section["findings"] = []
    payload["sources"]["camera_vision"]["observation_status"] = "unknown"
    request = valid_request(payload)
    calls = []
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda req: calls.append(req)),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW))
    assert asyncio.run(adapter.generate(request)).status == "insufficient_evidence"
    assert calls == []


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(bundle_schema_version="journey-evidence-v9"),
    lambda p: p["sources"].update(unexpected={}),
    too_many_road_records,
    duplicate_road_identity,
    lambda p: p["sources"]["road_ahead"]["findings"][0].update(title="x" * 161),
    lambda p: p.update(model=MODEL_ID),
    lambda p: p.update(prompt="override"),
])
def test_invalid_versions_fields_counts_and_text_are_rejected(mutation):
    payload = request_payload()
    mutation(payload)
    with pytest.raises(ValidationError):
        valid_request(payload)


def test_camera_rejects_multiple_or_untrusted_image_fields():
    payload = request_payload()
    payload["sources"]["camera_vision"].update(availability="available", observation_status="available", observation={
        "status": "available", "intersection_name": "Main & Broadway", "street_names": ["Main", "Broadway"],
        "distance_from_destination_meters": 20.0, "source_name": "City of Vancouver",
        "direction_view": {"view_id": "v1", "direction_label": "East", "retrieved_at": NOW.isoformat(),
                            "source_capture_at": None, "road_surface": "dry_looking", "visibility": "adequate",
                            "vehicle_activity": "some_visible", "conditions": [], "uncertainty": "low", "note": None},
        "views": [], "image_url": "data:image/jpeg;base64,abc", "image_bytes": "abc", "summary": None,
        "summary_evidence_view_ids": [],
    })
    with pytest.raises(ValidationError):
        valid_request(payload)
    payload["sources"]["camera_vision"]["observation"].pop("views")
    payload["sources"]["camera_vision"]["observation"].pop("image_url")
    payload["sources"]["camera_vision"]["observation"].pop("image_bytes")
    assert valid_request(payload).sources.camera_vision.observation.direction_view.view_id == "v1"


def test_api_accepts_canonical_camera_view_id_with_mocked_provider(monkeypatch, tmp_path):
    payload = request_payload()
    view_id = "view:e700a502c4ccdff685e9"
    payload["sources"]["camera_vision"].update(availability="available", observation_status="available", observation={
        "status": "available", "intersection_name": "Main & Broadway", "street_names": ["Main", "Broadway"],
        "distance_from_destination_meters": 20.0, "source_name": "City of Vancouver",
        "direction_view": {"view_id": view_id, "direction_label": "East", "retrieved_at": NOW.isoformat(),
                            "source_capture_at": None, "road_surface": "dry_looking", "visibility": "adequate",
                            "vehicle_activity": "some_visible", "conditions": [], "uncertainty": "low", "note": None},
        "summary": None, "summary_evidence_view_ids": [],
    })
    for invalid_view_id in ("camera:e700a502c4ccdff685e9", "view:", "view:e700a502c4ccdff685e9/extra"):
        invalid_payload = copy.deepcopy(payload)
        invalid_payload["sources"]["camera_vision"]["observation"]["direction_view"]["view_id"] = invalid_view_id
        with pytest.raises(ValidationError):
            valid_request(invalid_payload)

    seen: list[httpx.Request] = []
    camera_content = json.dumps({"status": "available", "overview": "A camera view is available near the destination.",
                                 "camera_text": "The east-facing view shows dry-looking pavement.",
                                 "weather_text": "", "construction_text": "Construction is reported nearby."})
    adapter = OpenRouterBriefingAdapter(api_key="test-secret", transport=httpx.MockTransport(lambda request: (seen.append(request), completion(content=camera_content))[1]),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    monkeypatch.setattr("app.routes.briefing_adapter", adapter)

    response = api_post(json.dumps(payload).encode())

    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert len(seen) == 1
    request = valid_request(payload)
    assert request.sources.camera_vision.observation.direction_view.view_id == view_id


def test_road_finding_accepts_verified_drivebc_source_id_format():
    payload = request_payload()
    finding = copy.deepcopy(payload["sources"]["road_ahead"]["findings"][0])
    finding["source_id"] = "drivebc.ca/OBSERVED-POINT-001"
    payload["sources"]["drivebc_open511"].update(availability="available", findings=[finding])

    request = valid_request(payload)

    assert request.sources.drivebc_open511.findings[0].source_id == "drivebc.ca/OBSERVED-POINT-001"
    assert "bc-drivebc.ca/OBSERVED-POINT-001" in request.allowed_evidence_refs()


def test_provider_cannot_supply_reference_arrays_and_length_truncation_is_rejected(tmp_path):
    async def run(response):
        adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: response),
                                            budget=BriefingAttemptBudget(tmp_path / f"budget-{id(response)}", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
        return await adapter.generate(valid_request())
    extra_refs = asyncio.run(run(completion(content=json.dumps({
        "status": "available", "overview": "Road work is reported nearby.", "camera_text": "",
        "weather_text": "", "construction_text": "Construction is reported nearby.",
        "evidence_refs": ["invented"],
    }))))
    malformed = asyncio.run(run(completion(content="{}")))
    truncated = asyncio.run(run(completion(finish_reason="length")))
    assert extra_refs.failure_code == malformed.failure_code == truncated.failure_code == "invalid_model_output"


def test_model_output_is_three_fixed_slots_and_maps_to_fixed_categories(tmp_path):
    camera_payload = request_payload()
    camera_payload["sources"]["camera_vision"].update(availability="available", observation_status="available", observation={
        "status": "available", "intersection_name": "Richards and Helmcken", "street_names": ["Richards", "Helmcken"],
        "distance_from_destination_meters": 50.0, "source_name": "City of Vancouver",
        "direction_view": {"view_id": "view:e700a502c4ccdff685e9", "direction_label": "East", "retrieved_at": NOW.isoformat(),
                           "source_capture_at": NOW.isoformat(), "road_surface": "dry_looking", "visibility": "adequate",
                           "vehicle_activity": "some_visible", "conditions": [], "uncertainty": "low", "note": None},
        "summary": None, "summary_evidence_view_ids": [],
    })
    camera_payload["sources"]["openweather_current"].update(
        availability="available", status={"source": "OpenWeather", "dataset_id": "onecall4_current", "success": True,
        "available": True, "fetched_at": NOW.isoformat(), "stale": False, "cache_stale": False},
        observation={"source": "OpenWeather", "product": "onecall4_current", "observed_at": NOW.isoformat(), "fetched_at": NOW.isoformat(),
                     "condition": {"code": 800, "group": "clear", "description": "clear sky"}, "temperature_c": None,
                     "feels_like_c": None, "humidity_pct": None, "wind_speed_m_s": None, "wind_direction_deg": None,
                     "wind_gust_m_s": None, "visibility_m": None, "rain_1h_mm": 0.0, "snow_1h_mm": 0.0},
    )
    selected_refs = ["camera-view-1", "ow-current"]
    content = json.dumps({
        "status": "available", "overview": "Conditions are reported for the selected journey.",
        "camera_text": "The east-facing view looks dry, consistent with current clear destination conditions.",
        "weather_text": "OpenWeather reports clear destination conditions.",
        "construction_text": "A construction project is reported nearby.",
    })
    seen: list[httpx.Request] = []
    adapter = OpenRouterBriefingAdapter(
        api_key="key", transport=httpx.MockTransport(lambda request: (seen.append(request), completion(content=content))[1]),
        budget=BriefingAttemptBudget(tmp_path / "fixed-slots", vision_path=tmp_path / "vision", now=lambda: NOW), now=lambda: NOW,
    )

    result = asyncio.run(adapter.generate(valid_request(camera_payload)))
    sent = json.loads(seen[0].content)
    model_evidence = json.loads(sent["messages"][1]["content"].split("\n", 1)[1])

    assert [item.category for item in result.highlights] == ["camera", "weather", "road"]
    assert [item.evidence_refs for item in result.highlights] == [selected_refs, ["ow-current"], ["ra-event-7"]]
    assert result.overview_evidence_refs == ["camera-view-1", "ow-current", "ra-event-7"]
    assert len(result.highlights) == 3
    assert model_evidence["topic_selection"]["camera"]["comparison_weather"]["evidence_ref"] == "ow-current"
    assert model_evidence["topic_selection"]["construction"]["route_relevance"] == "nearby"


def test_camera_topic_is_camera_only_when_usable_weather_is_absent():
    request = valid_request(add_camera(request_payload()))

    selected, refs, missing = _select_topics(request)

    assert refs["camera"] == ["camera-view-1"]
    assert "comparison_weather" not in selected["camera"]
    assert refs["weather"] == []
    assert missing["weather"] == "Destination weather data unavailable."


def test_camera_topic_uses_time_matching_forecast_when_current_is_not_usable():
    payload = add_forecast(add_camera(request_payload()), NOW + timedelta(minutes=15))
    request = valid_request(payload)

    selected, refs, _ = _select_topics(request)

    forecast_ref = f"ow-fc-{(NOW + timedelta(minutes=15)).isoformat()}"
    assert refs["camera"] == ["camera-view-1", forecast_ref]
    assert selected["camera"]["comparison_weather"]["kind"] == "forecast"
    assert refs["weather"] == [forecast_ref]


@pytest.mark.parametrize(
    ("camera_options", "weather_options", "expected_camera_refs", "expected_stale_message"),
    [
        ({"captured_at": NOW - timedelta(minutes=20)}, {"current": True}, [], True),
        ({"uncertainty": "high"}, {"current": True}, ["camera-view-1"], False),
        ({"note": "The structured surface label may be inconsistent."}, {"current": True}, ["camera-view-1"], False),
        ({}, {"current": True, "observed_at": NOW - timedelta(hours=2)}, ["camera-view-1"], False),
        ({}, {"forecast_at": NOW + timedelta(hours=2)}, ["camera-view-1"], False),
    ],
)
def test_camera_weather_comparison_is_suppressed_for_stale_uncertain_or_mismatched_evidence(
    camera_options, weather_options, expected_camera_refs, expected_stale_message
):
    payload = request_payload()
    payload = add_camera(payload, **camera_options)
    if weather_options.get("current"):
        payload = add_current_weather(payload, observed_at=weather_options.get("observed_at", NOW))
    if weather_options.get("forecast_at"):
        payload = add_forecast(payload, weather_options["forecast_at"])
    selected, refs, missing = _select_topics(valid_request(payload))

    assert refs["camera"] == expected_camera_refs
    assert "comparison_weather" not in selected.get("camera", {})
    if expected_stale_message:
        assert missing["camera"] == "Camera interpretation is stale and was not used for this briefing."


def test_construction_selection_prefers_overlap_then_distance_then_stable_id():
    payload = request_payload()
    template = payload["sources"]["road_ahead"]["findings"][0]
    payload["sources"]["road_ahead"]["findings"] = [
        {**copy.deepcopy(template), "source_id": "nearby-short", "event_type": "construction", "classification": "nearby", "distance_meters": 1.0},
        {**copy.deepcopy(template), "source_id": "overlap-far", "event_type": "construction", "classification": "direct_overlap", "distance_meters": 500.0},
        {**copy.deepcopy(template), "source_id": "overlap-z", "event_type": "construction", "classification": "direct_overlap", "distance_meters": 100.0},
        {**copy.deepcopy(template), "source_id": "overlap-a", "event_type": "construction", "classification": "direct_overlap", "distance_meters": 100.0},
        {**copy.deepcopy(template), "source_id": "closure", "event_type": "road_closure", "classification": "direct_overlap", "distance_meters": 0.0},
    ]

    selected, refs, _ = _select_topics(valid_request(payload))

    assert refs["construction"] == ["ra-overlap-a"]
    assert selected["construction"]["route_relevance"] == "direct_overlap"
    assert len(selected["construction"]["event"]) > 0


def test_nearby_construction_selection_preserves_off_route_meaning_and_missing_slots_are_truthful():
    payload = request_payload()
    payload["sources"]["road_ahead"]["findings"][0].update(classification="nearby", event_type="construction")
    payload["sources"]["camera_vision"].update(availability="failed", observation_status="error", observation=None)
    selected, refs, missing = _select_topics(valid_request(payload))
    assert selected["construction"]["route_relevance"] == "nearby"
    assert "nearby" in SYSTEM_PROMPT and "do not imply route overlap, blockage, or impact" in SYSTEM_PROMPT
    assert refs["camera"] == []
    assert missing["camera"] == "Camera interpretation unavailable for this journey."

    payload["sources"]["road_ahead"]["findings"][0]["event_type"] = "road_closure"
    _, refs, missing = _select_topics(valid_request(payload))
    assert refs["construction"] == []
    assert missing["construction"] == "No qualifying construction report is available in the current Road Ahead evidence."


def test_nearby_construction_cannot_be_returned_as_route_blocking(tmp_path):
    content = json.dumps({"status": "available", "overview": "Construction is reported nearby.",
                          "camera_text": "", "weather_text": "",
                          "construction_text": "The project blocks the selected route."})
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: completion(content=content)),
                                        budget=BriefingAttemptBudget(tmp_path / "nearby", vision_path=tmp_path / "vision", now=lambda: NOW), now=lambda: NOW)

    result = asyncio.run(adapter.generate(valid_request()))

    assert result.status == "error" and result.failure_code == "invalid_model_output"
    assert result.highlights == []


def test_missing_camera_weather_and_construction_have_fixed_source_availability_slots(tmp_path):
    payload = request_payload()
    payload["sources"]["road_ahead"]["availability"] = "empty"
    payload["sources"]["road_ahead"]["findings"] = []
    payload["sources"]["drivebc_open511"]["availability"] = "unknown"
    payload["sources"]["drivebc_open511"]["status"] = None
    content = json.dumps({"status": "available", "overview": "Road Ahead returned an empty construction result.",
                          "camera_text": "The model's unsupported camera guess is ignored.",
                          "weather_text": "The model's unsupported weather guess is ignored.",
                          "construction_text": "The model's unsupported construction guess is ignored."})
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: completion(content=content)),
                                        budget=BriefingAttemptBudget(tmp_path / "missing-slots", vision_path=tmp_path / "vision", now=lambda: NOW), now=lambda: NOW)

    result = asyncio.run(adapter.generate(valid_request(payload)))

    assert [item.category for item in result.highlights] == ["camera", "weather", "road"]
    assert [item.text for item in result.highlights] == [
        "Camera interpretation was pending and was not included.",
        "Destination weather data unavailable.",
        "No qualifying construction report is available in the current Road Ahead evidence.",
    ]
    assert all(not item.evidence_refs for item in result.highlights)


def test_insufficient_status_does_not_require_model_to_blank_cross_field_content(tmp_path):
    content = json.dumps({
        "status": "insufficient_evidence", "overview": "Model generated text is not exposed.",
        "camera_text": "Unselected camera text.", "weather_text": "Unselected weather text.",
        "construction_text": "Unselected construction text.",
    })
    adapter = OpenRouterBriefingAdapter(
        api_key="key", transport=httpx.MockTransport(lambda _: completion(content=content)),
        budget=BriefingAttemptBudget(tmp_path / "insufficient-text", vision_path=tmp_path / "vision", now=lambda: NOW),
        now=lambda: NOW,
    )

    result = asyncio.run(adapter.generate(valid_request()))

    assert result.status == "insufficient_evidence"
    assert result.overview == "" and result.overview_evidence_refs == [] and result.highlights == []


def test_unavailable_road_source_has_distinct_construction_message():
    payload = request_payload()
    payload["sources"]["road_ahead"].update(availability="failed", findings=[], statuses=[
        {"source": "Road Ahead", "dataset_id": "road-ahead", "success": False, "available": False,
         "fetched_at": None, "stale": False, "cache_stale": None},
    ])
    _selected, refs, missing = _select_topics(valid_request(payload))
    assert refs["construction"] == []
    assert missing["construction"] == "Road Ahead construction evidence is unavailable for this journey."


def test_provider_reference_arrays_cannot_override_backend_selection(tmp_path):
    for index, refs in enumerate((["ra-event-7", "unknown-ref"], ["camera-view-1", "ow-current", "ra-event-7", "bc-other"])):
        content = json.dumps({
            "status": "available", "overview": "Supported overview.", "camera_text": "",
            "weather_text": "", "construction_text": "Construction is reported nearby.",
            "highlights": [{"category": "camera", "text": "Claim", "evidence_refs": refs}],
        })
        adapter = OpenRouterBriefingAdapter(
            api_key="key", transport=httpx.MockTransport(lambda _, content=content: completion(content=content)),
            budget=BriefingAttemptBudget(tmp_path / f"bad-topic-{index}", vision_path=tmp_path / f"v-{index}", now=lambda: NOW),
            now=lambda: NOW,
        )
        result = asyncio.run(adapter.generate(valid_request()))
        assert result.status == "error" and result.failure_code == "invalid_model_output"
        assert result.highlights == []


def test_extra_model_topic_or_reference_fields_are_rejected_by_fixed_schema(tmp_path):
    output = json.loads(completion().json()["choices"][0]["message"]["content"])
    output["highlights"] = [{"category": "general", "text": "An extra topic", "evidence_refs": ["ra-event-7"]}]
    adapter = OpenRouterBriefingAdapter(
        api_key="key", transport=httpx.MockTransport(lambda _: completion(content=json.dumps(output))),
        budget=BriefingAttemptBudget(tmp_path / "extra-topic", vision_path=tmp_path / "vision", now=lambda: NOW), now=lambda: NOW,
    )

    result = asyncio.run(adapter.generate(valid_request()))

    assert result.status == "error" and result.failure_code == "invalid_model_output"
    assert result.highlights == []


def test_invalid_model_output_logs_safe_stage_categories(caplog, tmp_path):
    model_schema_error = json.dumps({"status": "available", "overview": "", "camera_text": "", "weather_text": ""})
    refusal = {"choices": [{"finish_reason": "stop", "message": {"refusal": "PRIVATE_PROVIDER_TEXT"}}]}
    missing_content = {"choices": [{"finish_reason": "stop", "message": {}}]}
    finish_reason_cases = [
        ("finish_reason_length", completion(finish_reason="length")),
        ("finish_reason_content_filter", completion(finish_reason="content_filter")),
        ("finish_reason_error", completion(finish_reason="error")),
        ("finish_reason_tool_calls", completion(finish_reason="tool_calls")),
        ("finish_reason_missing", completion(finish_reason=None)),
        ("finish_reason_missing", httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})),
        ("finish_reason_other", completion(finish_reason="provider_specific_private_value")),
    ]
    cases = [
        ("provider_envelope_invalid_json", httpx.Response(200, content=b"PRIVATE_RESPONSE_BODY")),
        ("provider_envelope_not_object", httpx.Response(200, json=[])),
        ("choice_shape_invalid", httpx.Response(200, json={"choices": []})),
        ("message_shape_invalid", httpx.Response(200, json={"choices": [{"message": None}]})),
        ("model_refusal", httpx.Response(200, json=refusal)),
        ("message_content_missing_or_invalid", httpx.Response(200, json=missing_content)),
        ("model_json_invalid", completion(content="PRIVATE_MALFORMED_JSON")),
        ("model_schema_invalid", completion(content=model_schema_error)),
        ("model_schema_invalid", completion(content=json.dumps({
            "status": "available", "overview": "PRIVATE_OVERVIEW", "camera_text": "",
            "weather_text": "", "construction_text": "", "evidence_refs": ["PRIVATE_EVIDENCE_REF"],
        }))),
        ("provider_response_too_large", httpx.Response(200, content=b" " * (64 * 1024 + 1))),
    ] + finish_reason_cases
    caplog.set_level(logging.WARNING, logger="app.openrouter_briefing")

    for index, (diagnostic_code, response) in enumerate(cases):
        caplog.clear()
        adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _, response=response: response),
                                            budget=BriefingAttemptBudget(tmp_path / f"budget-{index}", vision_path=tmp_path / f"v-{index}", now=lambda: NOW), now=lambda: NOW)
        result = asyncio.run(adapter.generate(valid_request()))

        assert result.status == "error" and result.failure_code == "invalid_model_output", diagnostic_code
        assert f"diagnostic_code={diagnostic_code}" in caplog.text
        assert "PRIVATE_" not in caplog.text
        assert "PRIVATE_" not in result.model_dump_json()
        assert "provider_specific_private_value" not in caplog.text


def test_model_schema_failures_log_bounded_safe_validation_details(caplog, tmp_path):
    cases = [
        (
            "missing_required_field",
            {"status": "available", "overview": "PRIVATE_OVERVIEW", "camera_text": "", "weather_text": ""},
            'validation_kind=field_validation errors=[{"loc":"construction_text","type":"missing"}',
        ),
        (
            "invalid_camera_topic_text",
            {"status": "available", "overview": "Supported overview", "camera_text": "PRIVATE_TEXT" * 40,
             "weather_text": "", "construction_text": ""},
            'validation_kind=field_validation errors=[{"loc":"camera_text","type":"string_too_long"}]',
        ),
    ]
    caplog.set_level(logging.WARNING, logger="app.openrouter_briefing")

    for index, (name, output, expected_details) in enumerate(cases):
        caplog.clear()
        adapter = OpenRouterBriefingAdapter(
            api_key="key",
            transport=httpx.MockTransport(lambda _, output=output: completion(content=json.dumps(output))),
            budget=BriefingAttemptBudget(tmp_path / f"budget-{index}", vision_path=tmp_path / f"v-{index}", now=lambda: NOW),
            now=lambda: NOW,
        )

        result = asyncio.run(adapter.generate(valid_request()))

        assert result.status == "error" and result.failure_code == "invalid_model_output", name
        assert expected_details in caplog.text, name
        assert "PRIVATE_" not in caplog.text
        assert "PRIVATE_" not in result.model_dump_json()


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
def test_provider_http_errors_are_safe(status, tmp_path):
    secret = "never-forward-this-upstream-body"
    adapter = OpenRouterBriefingAdapter(api_key="test-secret", transport=httpx.MockTransport(lambda _: httpx.Response(status, text=secret)),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request()))
    assert result.status == "unavailable" and result.failure_code == "provider_unavailable"
    assert secret not in result.model_dump_json()
    assert "test-secret" not in result.model_dump_json()


def test_timeout_transport_failure_and_attempt_reservation(tmp_path):
    path = tmp_path / "budget.json"
    def timeout(_):
        raise httpx.ReadTimeout("private diagnostic")
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(timeout),
                                        budget=BriefingAttemptBudget(path, vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request()))
    assert result.failure_code == "timeout"
    record = json.loads(path.read_text())
    assert len(record["attempts"]) == 1
    assert record["estimated_project_usd"] == ESTIMATED_USD_PER_ATTEMPT


def test_missing_key_does_not_dispatch_or_reserve(tmp_path):
    calls = []
    budget_path = tmp_path / "budget.json"
    adapter = OpenRouterBriefingAdapter(api_key="", transport=httpx.MockTransport(lambda req: calls.append(req)),
                                        budget=BriefingAttemptBudget(budget_path, vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request()))
    assert result.failure_code == "configuration_missing"
    assert calls == [] and not budget_path.exists()


def test_oversized_provider_response_is_rejected_before_parsing(tmp_path):
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b" " * (64 * 1024 + 1))),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    result = asyncio.run(adapter.generate(valid_request()))
    assert result.status == "error" and result.failure_code == "invalid_model_output"


def test_api_returns_typed_result_for_valid_raw_request(monkeypatch, tmp_path):
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: completion()),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    monkeypatch.setattr("app.routes.briefing_adapter", adapter)
    response = api_post(json.dumps(request_payload()).encode())
    assert response.status_code == 200
    result = response.json()
    assert result["contract_version"] == "journey-briefing-v1"
    assert result["attempt_id"] == 17 and result["status"] == "available"
    assert result["requested_model"] == MODEL_ID


def test_rolling_hour_daily_caps_corrupt_ledger_and_project_guard(tmp_path):
    path = tmp_path / "budget.json"
    budget = BriefingAttemptBudget(path, vision_path=tmp_path / "v", now=lambda: NOW)
    assert all(budget.reserve() for _ in range(50))
    assert not budget.reserve()
    path.write_text("corrupt")
    assert not budget.reserve()
    path.unlink()
    vision = tmp_path / "vision.json"
    vision.write_text(json.dumps({"estimated_project_usd": 4.989}))
    assert not BriefingAttemptBudget(path, vision_path=vision, now=lambda: NOW).reserve()
    current = [NOW]
    budget = BriefingAttemptBudget(path, vision_path=tmp_path / "v", now=lambda: current[0])
    reservations = []
    for index in range(100):
        current[0] = NOW + timedelta(hours=0 if index < 50 else 1)
        reservations.append(budget.reserve())
    assert all(reservations)
    assert not budget.reserve()


def test_duplicate_attempt_dispatches_only_once(tmp_path):
    calls = []
    adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: (calls.append(1), completion())[1]),
                                        budget=BriefingAttemptBudget(tmp_path / "budget", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
    async def execute():
        return await asyncio.gather(adapter.generate(valid_request()), adapter.generate(valid_request()))
    results = asyncio.run(execute())
    assert len(calls) == 1
    assert sorted(item.failure_code or "ok" for item in results) == ["duplicate_attempt", "ok"]


def test_api_rejects_raw_oversize_and_arbitrary_fields_before_adapter(monkeypatch):
    called = []
    monkeypatch.setattr("app.routes.briefing_adapter", type("Adapter", (), {"generate": lambda self, request: called.append(request)})())
    response = api_post(b"{" + b" " * (32 * 1024) + b"}")
    assert response.status_code == 413 and called == []
    payload = request_payload()
    payload["provider"] = "client-controlled"
    response = api_post(json.dumps(payload).encode())
    assert response.status_code == 422 and called == []


def test_minimal_model_output_contract_and_wire_schema_shape():
    assert "three supplied topic selections" in SYSTEM_PROMPT
    assert "240 characters or fewer" in SYSTEM_PROMPT
    assert "Do not generate categories, references, availability flags, topic ordering" in SYSTEM_PROMPT
    assert "do not imply route overlap, blockage, or impact" in SYSTEM_PROMPT
    valid = {"status": "available", "overview": "Supported summary", "camera_text": "Camera evidence.",
             "weather_text": "", "construction_text": "Construction reported nearby."}
    assert ModelBriefingOutputV1.model_validate(valid).camera_text == "Camera evidence."
    with pytest.raises(ValidationError):
        ModelBriefingOutputV1.model_validate({**valid, "camera_text": "x" * 301})
    # Status no longer imposes cross-field blanking rules; backend ignores text for an
    # insufficient-evidence result and owns all topic availability decisions.
    permissive_status_output = {**valid, "status": "insufficient_evidence", "overview": "ignored"}
    assert ModelBriefingOutputV1.model_validate(permissive_status_output).overview == "ignored"
    with pytest.raises(ValidationError):
        ModelBriefingOutputV1.model_validate({**valid, "evidence_refs": ["invented"]})
    schema_text = json.dumps(wire_schema())
    for forbidden in ("$defs", "$ref", "anyOf", "minLength", "maxLength", "minimum", "maximum", "pattern"):
        assert forbidden not in schema_text
    assert wire_schema()["required"] == ["status", "overview", "camera_text", "weather_text", "construction_text"]
    assert set(wire_schema()["properties"]) == set(wire_schema()["required"])
