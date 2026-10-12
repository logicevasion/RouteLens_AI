# Camera Vision Journey Contract — Assignment 8C

**Status:** Implemented, pending human acceptance
**Scope:** Typed backend camera-vision operation and journey-context binding. No frontend integration or live provider request.

## 1. Journey-facing operation

`POST /api/cameras/observe` accepts the same strict `Trip` request shape as `POST /api/trips/analyze`: canonical origin and destination, driving mode, and the explicitly selected route. The backend uses only `trip.destination` to run the existing Phase 7 `DestinationCameraService.nearest` selection. The caller cannot supply an intersection ID, camera URL, image bytes, local path, model, or provider.

The operation passes that server-selected result, its validated camera catalogue snapshot, and the existing current-frame store to `OpenRouterVisionAdapter.analyze_selected_intersection`. The adapter remains responsible for Phase 7 cache freshness and digest checks, one-intersection enforcement, ordered directional views, snapshot identity, request limits, strict schema and semantic validation, and short-lived identical-snapshot reuse. No additional frame fetch or alternate-intersection fallback is implemented in the vision operation.

The response is the existing typed `AdapterResult`, containing one `CameraObservation` and only its accepted bounded diagnostics (`provider_error`, `semantic_error_code`, and `cache_reused`). No parallel observation DTO or repeated observation section was added. Existing `POST /api/trips/analyze` response fields and semantics are unchanged; the operation is a separate explicit API request and is not called by Analyze Journey, camera gallery selection, or image retrieval.

## 2. Trust boundary and provenance

Backend-owned provenance stays in `CameraObservation`: selected intersection identity/name and street names; approximate destination distance; City source attribution and official camera page; exact included view IDs and direction labels; frame retrieval timestamps, content digests, validated image metadata and snapshot identities; requested model, reported provider/endpoint when available, inference time, and reported usage. `source_capture_at` stays null when the source does not supply a verified capture timestamp.

Model-generated data remains limited to the accepted 8B contract: per-view road-surface appearance, visibility, qualitative vehicle activity, controlled condition labels, uncertainty and optional note, plus optional summary and evidence view references. The existing strict schema and semantic validation remain authoritative. Model prose never supplies or replaces backend provenance.

The request destination is compared to the destination returned by camera selection before reading the catalogue or invoking the adapter. A mismatch returns a fixed `journey_context_mismatch` error without selected provenance. The adapter independently checks the selected intersection against the catalogue and cache snapshot. It rejects mismatches without provider calls. The endpoint does not persist a result or attach one to an analysis from another request; stale response correlation and end-to-end Analyze Journey lifecycle wiring remain 8D work.

## 3. Status and failure representation

Successful observations use the adapter's `available`, `partial`, or `insufficient_evidence` status. Unavailable/error outcomes retain the accepted bounded failure codes for configuration, provider availability, timeout, rate limit, request budget, invalid model output, and frame eligibility. `no_selected_intersection` and `journey_context_mismatch` were added to the existing failure-code vocabulary because 8C must distinguish absence of a selected camera from a selected camera whose current frames are unusable, and must reject destination-context mismatch.

Failure results contain no provider response body, model response text, image data, secret, or model-echoed identifiers. Provider errors use the existing fixed diagnostic categories and bounded metadata. Vision failure is isolated from journey analysis because the existing analysis endpoint does not await or depend on the camera-vision endpoint.

## 4. Compatibility and phase boundary

The existing Analyze Journey response, road-event fields, weather fields, route geometry, and Phase 7 camera endpoints are unchanged. Clients that do not call `/api/cameras/observe` behave as before. No frontend component or user-visible observation card was added.

The 8C operation is an explicit backend call; it does not run on page load, route calculation, map panning, marker interaction, gallery display, or camera image GET. Automated tests use generated in-memory JPEGs, a temporary attempt budget, and mocked OpenRouter transport. No test sent City imagery or made a paid request.

Assignment 8D remains responsible for manual Analyze Journey request wiring, request cancellation and stale-response identity across journey changes, end-to-end lifecycle orchestration and handoff, and the broader internal pipeline acceptance. Phase 9 evidence reasoning, Phase 10 briefing, frontend presentation, and live City-image inference are outside this implementation.

## 5. Verification

Verification passed: the focused camera-vision API, 8B adapter, and Phase 7 camera suites passed **71 tests**; the full backend suite passed **383 tests**; Ruff passed across `backend/app` and `backend/tests`; import smoke passed for the API and vision adapter; and `git diff --check` passed. All camera and vision integration evidence is mocked/offline; synthetic JPEGs are generated locally by the test suite. No real City camera image was submitted and no paid inference request occurred.

## 6. Deviations

No material deviations from the accepted 8C journey-facing API boundary. The two fixed failure codes extend the accepted result's existing failure vocabulary to represent 8C selection and context conditions without adding a wrapper result type.
