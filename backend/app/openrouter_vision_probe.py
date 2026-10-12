"""Explicit synthetic-only OpenRouter compatibility probe for Assignment 8B."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from pydantic import ValidationError

from app.camera_images import StoredFrame
from app.openrouter_vision import (
    CHAT_COMPLETIONS_URL,
    MODEL_ID,
    ModelCameraObservation,
    OpenRouterVisionAdapter,
    SemanticValidationError,
    _json_content,
    _provider_error_diagnostic,
    _reported_provider,
    _semantic_validate,
)
from app.vancouver_cameras import CameraView

FIXTURE_DIRECTORY = Path(__file__).resolve().parents[2] / "fixtures" / "openrouter"
MODEL_ENDPOINTS_URL = f"https://openrouter.ai/api/v1/models/{MODEL_ID}/endpoints"
SYNTHETIC_FIXTURES = (
    ("illustrative_camera_view_1.png", "probe-view-one", "Synthetic illustration one"),
    ("illustrative_camera_view_2.png", "probe-view-two", "Synthetic illustration two"),
)


def _payload() -> tuple[dict, list[str]]:
    included = []
    ids = []
    for filename, view_id, direction in SYNTHETIC_FIXTURES:
        path = FIXTURE_DIRECTORY / filename
        body = path.read_bytes()
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            content_type = Image.MIME.get(image.format or "")
        if content_type != "image/png":
            raise ValueError("synthetic fixture format did not match PNG")
        view = CameraView(
            view_id=view_id,
            direction_label=direction,
            image_url=None,
            image_host=None,
            discovery_status="url_validated",
        )
        frame = StoredFrame(
            intersection_id="synthetic-probe-only",
            view_id=view_id,
            source_url="https://synthetic.invalid/developer-owned-fixture.png",
            retrieved_at=datetime.now(timezone.utc),
            content_type=content_type,
            width=width,
            height=height,
            byte_length=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
        )
        included.append((view, frame, body))
        ids.append(view_id)
    return OpenRouterVisionAdapter._payload(included), ids


async def run_probe() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print(json.dumps({"result": "not_run", "reason": "configuration_missing"}))
        return 2
    # Confirm model-level image input and at least one potential structured-output endpoint.
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            metadata_response = await client.get(MODEL_ENDPOINTS_URL)
        model_metadata = metadata_response.json() if metadata_response.status_code == 200 else None
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError):
        model_metadata = None
    model_data = model_metadata.get("data") if isinstance(model_metadata, dict) else None
    architecture = model_data.get("architecture") if isinstance(model_data, dict) else None
    input_modalities = architecture.get("input_modalities") if isinstance(architecture, dict) else None
    endpoint_list = model_data.get("endpoints") if isinstance(model_data, dict) else None
    eligible = (
        isinstance(model_data, dict)
        and model_data.get("id") == MODEL_ID
        and isinstance(input_modalities, list)
        and "image" in input_modalities
        and isinstance(endpoint_list, list)
        and any(
            isinstance(endpoint, dict)
            and endpoint.get("model_id") == MODEL_ID
            and isinstance(endpoint.get("supported_parameters"), list)
            and bool({"response_format", "structured_outputs"}.intersection(endpoint["supported_parameters"]))
            for endpoint in endpoint_list
        )
    )
    if not eligible:
        print(json.dumps({"result": "not_run", "reason": "model_capability_metadata_not_confirmed"}))
        return 2
    payload, expected_ids = _payload()
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await asyncio.wait_for(
                client.post(
                    CHAT_COMPLETIONS_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                ),
                timeout=30.0,
            )
    except (httpx.HTTPError, asyncio.TimeoutError):
        print(json.dumps({"result": "failed", "reason": "transport_or_timeout", "latency_ms": int((time.monotonic() - started) * 1000)}))
        return 1
    latency_ms = int((time.monotonic() - started) * 1000)
    if response.status_code != 200:
        diagnostic = _provider_error_diagnostic(response).model_dump(mode="json")
        print(json.dumps({"result": "failed", "requested_model": MODEL_ID, "diagnostic": diagnostic, "latency_ms": latency_ms}, separators=(",", ":")))
        return 1
    if len(response.content) > 2 * 1024 * 1024:
        print(json.dumps({"result": "failed", "reason": "response_size_exceeded", "http_status": response.status_code, "latency_ms": latency_ms}))
        return 1
    envelope = {}
    failure_stage = "response_envelope"
    schema_valid: bool | None = None
    semantic_valid: bool | None = None
    semantic_failure_code = None
    try:
        envelope = response.json()
        if not isinstance(envelope, dict):
            raise TypeError("invalid_response_envelope")
        failure_stage = "model_identity"
        content, finish_reason = _json_content(envelope)
        if envelope.get("model") != MODEL_ID:
            raise ValueError("model_mismatch")
        failure_stage = "completion"
        if finish_reason not in {"stop", "end_turn"} or content is None:
            raise ValueError("incomplete_or_refused_response")
        failure_stage = "json_schema_validation"
        schema_valid = False
        parsed = ModelCameraObservation.model_validate_json(content)
        schema_valid = True
        failure_stage = "semantic_validation"
        semantic_valid = False
        try:
            _semantic_validate(parsed, expected_ids)
        except SemanticValidationError as exc:
            semantic_failure_code = exc.code
            raise
        semantic_valid = True
        actual_provider = _reported_provider(envelope)
        usage = envelope.get("usage") if isinstance(envelope.get("usage"), dict) else {}
        failure_stage = "output_token_ceiling"
        output_tokens = usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None
        if output_tokens is not None and output_tokens > 1024:
            raise ValueError("output_token_ceiling_exceeded")
        report = {
            "result": "passed",
            "requested_model": MODEL_ID,
            "actual_model": envelope.get("model"),
            "actual_provider": actual_provider,
            "actual_endpoint": None,
            "endpoint_identity_limitation": "OpenRouter response did not report an endpoint identifier",
            "images_in_single_request": 2,
            "strict_json_schema": True,
            "provider_controls_sent": {"automatic_selection": True, "fallbacks_enabled": True, "require_parameters": True},
            "optional_privacy_filters_omitted": ["data_collection", "zdr"],
            "finish_reason": finish_reason,
            "schema_and_semantics_valid": True,
            "input_tokens": usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int else None,
            "output_tokens": output_tokens,
            "reported_cost_usd": usage.get("cost") if type(usage.get("cost")) in {int, float} else None,
            "latency_ms": latency_ms,
        }
        print(json.dumps(report, separators=(",", ":")))
        return 0
    except (ValueError, TypeError, json.JSONDecodeError, httpx.DecodingError, ValidationError):
        choices = envelope.get("choices") if isinstance(envelope, dict) else None
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        raw_finish = choice.get("finish_reason")
        known_finish_reasons = {"stop", "end_turn", "length", "content_filter", "tool_calls", "refusal"}
        finish_reason = raw_finish if isinstance(raw_finish, str) and raw_finish in known_finish_reasons else None
        usage = envelope.get("usage") if isinstance(envelope, dict) and isinstance(envelope.get("usage"), dict) else {}
        cost = usage.get("cost")
        reported_cost = cost if type(cost) in {int, float} and math.isfinite(cost) and 0 <= cost <= 100 else None
        report = {
            "result": "failed",
            "reason": failure_stage,
            "http_status": response.status_code,
            "actual_model_matches_requested": isinstance(envelope, dict) and envelope.get("model") == MODEL_ID,
            "actual_model": MODEL_ID if isinstance(envelope, dict) and envelope.get("model") == MODEL_ID else None,
            "actual_provider": _reported_provider(envelope) if isinstance(envelope, dict) else None,
            "finish_reason": finish_reason,
            "schema_valid": schema_valid,
            "semantic_valid": semantic_valid,
            "semantic_failure_code": semantic_failure_code,
            "input_tokens": usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int and 0 <= usage.get("prompt_tokens") <= 10_000_000 else None,
            "output_tokens": usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int and 0 <= usage.get("completion_tokens") <= 10_000_000 else None,
            "reported_cost_usd": reported_cost,
            "latency_ms": latency_ms,
        }
        print(json.dumps(report, separators=(",", ":")))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--synthetic-fixtures",
        action="store_true",
        required=True,
        help="Explicitly select only the two developer-owned Phase 0D illustrative PNG files.",
    )
    parser.parse_args()
    return asyncio.run(run_probe())


if __name__ == "__main__":
    raise SystemExit(main())
