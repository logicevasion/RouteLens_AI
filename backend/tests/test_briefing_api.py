from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from app.briefing_contracts import BriefingEvidenceRequestV1, ModelBriefingV1
from app.main import app
from app.openrouter_briefing import (
    CHAT_COMPLETIONS_URL,
    ESTIMATED_USD_PER_ATTEMPT,
    MODEL_ID,
    BriefingAttemptBudget,
    OpenRouterBriefingAdapter,
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
                "source_id": "event-7", "title": "Road work", "description": "Lane work reported.",
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


def valid_request(payload: dict | None = None) -> BriefingEvidenceRequestV1:
    return BriefingEvidenceRequestV1.model_validate_json(json.dumps(payload or request_payload()))


def completion(*, refs: list[str] | None = None, status: int = 200, content: str | None = None,
               finish_reason: str = "stop") -> httpx.Response:
    if content is None:
        content = json.dumps({"status": "available", "overview": "Road work is reported nearby.",
                              "overview_evidence_refs": refs or ["ra-event-7"],
                              "highlights": [{"category": "road", "text": "Work is reported near Main Street.",
                                              "evidence_refs": refs or ["ra-event-7"]}]})
    body = {"model": MODEL_ID, "provider": "TestProvider", "choices": [{
        "finish_reason": finish_reason, "message": {"content": content}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150, "cost": 0.0001}}
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
    assert sent["model"] == MODEL_ID and sent["stream"] is False and sent["max_tokens"] == 512
    assert sent["provider"] == {"require_parameters": True}
    assert sent["response_format"]["type"] == "json_schema"
    assert "additionalProperties" not in str(wire_schema()) or wire_schema()["additionalProperties"] is False
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
                               "overview_evidence_refs": ["ra-status", "bc-status"], "highlights": []})
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


def test_invalid_model_refs_empty_completion_and_nonterminal_rejected(tmp_path):
    async def run(response):
        adapter = OpenRouterBriefingAdapter(api_key="key", transport=httpx.MockTransport(lambda _: response),
                                            budget=BriefingAttemptBudget(tmp_path / f"budget-{id(response)}", vision_path=tmp_path / "v", now=lambda: NOW), now=lambda: NOW)
        return await adapter.generate(valid_request())
    invalid_ref = asyncio.run(run(completion(refs=["invented"])))
    malformed = asyncio.run(run(completion(content="{}")))
    unfinished = asyncio.run(run(completion(finish_reason="length")))
    assert invalid_ref.failure_code == malformed.failure_code == unfinished.failure_code == "invalid_model_output"


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


def test_model_response_status_constraints_and_wire_schema_shape():
    with pytest.raises(ValidationError):
        ModelBriefingV1.model_validate({"status": "available", "overview": "", "overview_evidence_refs": [], "highlights": []})
    with pytest.raises(ValidationError):
        ModelBriefingV1.model_validate({"status": "insufficient_evidence", "overview": "No issues", "overview_evidence_refs": [], "highlights": []})
    schema_text = json.dumps(wire_schema())
    for forbidden in ("$defs", "$ref", "anyOf", "minLength", "maxLength", "minimum", "maximum", "pattern"):
        assert forbidden not in schema_text
