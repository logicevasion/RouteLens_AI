# End-to-End Camera Vision Integration — Assignment 8D

**Status:** Implemented — pending human acceptance
**Scope:** Explicit Analyze Journey orchestration and internal evidence retention. Phase 9 and Phase 10 are not implemented here.

## Analyze Journey lifecycle

The existing `analyzeJourney()` handler constructs one canonical `Trip` with `buildAnalysisRequest()` from the selected origin, validated destination, and explicitly selected route. That same captured object is sent once to each of the existing road analysis and camera vision APIs. Vision uses `POST /api/cameras/observe`; it is not called by Find Routes, page load, typing, map movement, nearby marker selection, gallery actions, or image retrieval.

The vision request starts alongside `POST /api/trips/analyze` and the existing Phase 7 camera/gallery requests. It has a dedicated `AbortController` and a 70-second browser timeout. `JourneyCameraEvidence.camera_vision` records `pending` immediately, then a complete validated result or bounded unavailable result. Vision completion is independent of the visible road/weather and gallery requests, and a vision failure does not replace or clear their results.

## Typed internal handoff

`App.tsx` holds one `JourneyEvidenceState` containing the current ordinary analysis state and one `camera_vision` evidence field. `JourneyCameraEvidence` carries the exact canonical `trip`, monotonically increasing `attempt_id`, and `camera_vision` pending/completed state. `CameraVisionResult` mirrors the accepted backend `AdapterResult` with a validated `CameraVisionObservation`, bounded provider diagnostic, semantic code, and optional integer-only view mismatch counts/position.

The observation retains two separate groups of fields:

- **Backend provenance:** selected intersection ID/name and streets, approximate destination distance, official source metadata, included/excluded directional view IDs and labels, retrieval time, source capture time only when verified, SHA-256 digest, snapshot identity, validated image metadata, requested model and reported provider/endpoint, inference time, and bounded usage.
- **Validated model observations:** per-view road-surface appearance, visibility, vehicle activity, controlled visual conditions, uncertainty, optional note, and optional evidence-linked intersection summary.

Phase 9 can consume the current value through `journeyEvidenceState.camera_vision.camera_vision.result`. It can also distinguish a still-pending result from an unavailable or error result and retain unknown fields as unknown. No raw images, encoded image data, complete provider body, or secrets are copied into application state. The result is not rendered in a new UI component.

## Stale-result protection

The app gives each Analyze Journey attempt a monotonically increasing vision ID and a key containing the captured Trip and analysis generation. A result is retained only if both still match the active attempt, and the state update verifies the ID again before replacing evidence. A new Analyze Journey attempt aborts and supersedes the earlier request. Destination/origin edits, Find Routes, selected-route changes, and component unmount invalidate the attempt and clear its camera telemetry.

Aborting the browser request only stops local waiting where possible. It does not guarantee already-started upstream inference stops or avoids billing. The backend attempt ledger remains the enforcement boundary for spending limits.

## Server-side selection and validation

The frontend sends only the canonical Trip. The existing `POST /api/cameras/observe` endpoint selects the destination intersection server-side and calls the accepted 8B adapter with the existing Phase 7 catalogue and validated current-frame cache. The adapter continues to enforce current-frame freshness and digest consistency, one selected intersection, image and aggregate size limits, ordered view identity, attempt and cost ceilings, `google/gemma-4-31b-it` with accepted automatic OpenRouter routing, strict JSON Schema, semantic validation, and no corrective inference retry. Those responsibilities are not duplicated in the browser.

## Single-image MVP inference policy

The human developer has superseded the earlier multi-image inference requirement for the one-week datathon MVP. Each vision attempt analyzes **exactly one image**, chosen as the first eligible directional view in canonical Phase 7 catalogue order at the already selected destination intersection. The adapter walks the catalogue sequence without ranking by retrieval timestamp; it reuses the accepted Phase 7/8B checks for currentness, content type, decoding, dimensions, pixels, integrity/digest, and size, then performs its accepted digest/snapshot recheck before encoding. Missing, stale, malformed, oversized, or otherwise ineligible earlier entries are recorded with bounded exclusion reasons and skipped; a later eligible view may be selected. The adapter never substitutes a second intersection and does not invoke OpenRouter when no eligible view remains.

The OpenRouter content contains exactly one labeled image, and the semantic validator expects exactly that view's authoritative `view_id` in its original position. The `camera-observation-v1` schema remains multi-view capable for future use, and exact ID/order enforcement is unchanged. Backend-derived intersection, destination distance, selected view/direction, official camera-page URL and attribution, retrieval time, digest, snapshot identity, requested model/reported provider, usage, latency, and bounded diagnostics remain authoritative. The cache's image source URL remains backend-controlled for identity and integrity checks; a new raw image URL is not added to journey telemetry. Model observations and any optional summary are evidence only from that single directional view. The view's own capture time remains unknown unless independently verified. Snapshot reuse already hashes the actually included view identity/digest/retrieval time and model, provider configuration, prompt version, and schema version.

The Phase 7 camera gallery continues to retrieve and display all available directional images. Only the Phase 8 inference payload is single-image. Multi-image inference is deferred to reduce model workload, latency, output complexity, and view-identity compliance risk during the MVP; no gallery, camera-fetch, 8C endpoint, or frontend lifecycle change was needed.

Focused mocked adapter tests cover first-in-catalogue selection even when a later view is newer, fallback from missing/invalid/stale/oversized earlier frames, one eligible frame, zero eligible frames without provider invocation, one-image payload/expected IDs, one-view strict validation, mismatch rejection, and selected-frame/model/prompt/schema reuse-key identity. API fixtures now return one selected view. Historical multi-view schema and validator tests remain to preserve future contract coverage.

## Failure and loading states

Pending state is internal. The endpoint's bounded result is retained directly for statuses and failure codes such as no selected intersection, no eligible/current frames, stale-only frames, missing configuration, budget ceiling, provider failure/timeout, and invalid model output. Browser timeout resolves to `timeout`; transport failure resolves to `provider_unavailable`; an unparseable or malformed endpoint result resolves to `invalid_model_output`. No fallback observations are generated. No raw provider diagnostics or observation text are shown to the user.

The ordinary journey analysis and Phase 7 camera requests continue independently. A selected camera with no usable frames therefore produces the adapter's bounded unavailable result while leaving ordinary weather, road, route, and gallery state alone.

## Automated verification

Frontend tests mock `fetch` and use a sanitized synthetic AdapterResult; they verify one request with the canonical Trip, explicit-trigger source wiring, provenance retention, bounded failure states, rejection of data URLs, filtering of unexpected full-response fields, and stale/superseded identity handling. The repository has no React DOM lifecycle harness, so trigger coverage uses focused component-source assertions and directly exercises the typed request/state helpers. No test calls OpenRouter.

For the identity-compliance correction, focused backend adapter and camera-vision API tests passed (**50**); full backend pytest passed (**385**); backend Ruff and import smoke passed; frontend tests passed (**7 suites**); TypeScript and production build passed; and `git diff --check` passed. Timeout-adjustment verification is recorded below. Backend tests use generated in-memory JPEGs and mocked provider transport. No test calls OpenRouter or performs inference.

## First real-camera inference and read-only diagnosis

The first manual browser Analyze Journey test did call `POST /api/cameras/observe`. It returned HTTP 200 with `status=error`, `failure_code=invalid_model_output`, and `semantic_error_code=view_identity_or_order_mismatch`. The selected intersection was Richards St and Helmcken St, approximately 142 metres from the canonical destination. Existing road, weather, and camera UI continued working.

The read-only review found no backend ordering inconsistency: the adapter builds the included frames in Phase 7 directional-view order, assembles each text label immediately before its matching image in that same sequence, and constructs expected IDs from the same included-frame list. Four eligible directional frames were strongly indicated for the failed attempt; the successful synthetic verification used two. The actual provider-returned observation count, IDs, provider, latency, usage, and cost were not retained locally. The endpoint does not persist the provider response, failed output is not cached, and the adapter previously returned only the fixed semantic code. No raw model output or image data was recovered or printed.

The evidence therefore does not confirm a backend identity/order defect. Model identity/order noncompliance is the leading explanation, especially given the larger four-view set and the prompt's prior lack of explicit copy-every-ID and preserve-order instructions, but the exact deviation cannot be proven without the response. The existing strict exact identity/order validator remains unchanged.

The previously inspected local attempt ledger recorded one reserved attempt with the adapter's US$0.02 estimated request amount; this is not a provider-reported billed cost. No provider usage or actual cost for the browser attempt was retained. The key is not included in this note.

## Identity compliance correction

`INTRO_PROMPT` now explicitly requires one observation for every submitted image, character-for-character view ID copying, original order, identity association with the labeled image, and use of the schema's `unclear`/`not_observable` values instead of omitting unclear views. `PROMPT_VERSION` changed from `camera-visual-observer-v1` to `camera-visual-observer-v2`. The accepted schema version remains unchanged. Prompt version was already part of the identical-snapshot reuse key, so v1 successes cannot be reused under v2.

Identity/order rejection keeps `view_identity_or_order_mismatch` and now optionally returns `semantic_mismatch` with bounded integer `expected_view_count`, `actual_view_count`, and one-based `first_mismatched_position` (including the trailing missing/extra position when the common prefix matches). No returned IDs, model text, image content, or unrestricted exception details are included. This diagnostic describes only future rejection metadata; it does not recover details from the first browser failure.

No follow-up real-camera request or synthetic inference was made during the identity correction. A successful real-camera inference remains unverified; a separately authorized human browser test is still required to assess whether the clarified prompt improves compliance. No retry is performed automatically.

## Vision timeout adjustment

The second manual real-camera Analyze Journey test used prompt v2 and returned HTTP 200 with application-level `status=error` and `failure_code=timeout`. The existing road, weather, and camera workflow remained operational; the selected Richards St and Helmcken St intersection had previously been found to have four eligible directional frames.

At the time of that test, the backend adapter used both an HTTPX timeout and an outer `asyncio.wait_for` deadline of 30 seconds. The frontend used a vision-specific 35-second abort deadline. The backend maps an upstream timeout to the bounded `status=error`, `failure_code=timeout` result; a frontend-only abort instead creates a local `status=unavailable` result. Given the reported HTTP 200 application error status, the timeout was produced by the backend adapter path. The response does not distinguish an HTTPX phase timeout from the outer total deadline; both were 30 seconds. The Vite `/api` proxy has no explicit timeout configured, and no shorter proxy timeout was found in the repository. The separate developer probe retains its own 30-second timeout and is not used by the Analyze Journey endpoint. External infrastructure outside this local application was not measured.

The adapter HTTPX and outer deadlines are now both 60 seconds. The vision-only frontend deadline is now 70 seconds, leaving a 10-second response margin. No road, weather, route, camera catalogue, gallery, or image-retrieval timeout changed. The request still makes one upstream attempt with no automatic retry and keeps the accepted attempt/budget limits, automatic provider selection, strict schema, and exact view identity/order validation. The existing dedicated abort controller and attempt/trip identity checks remain in place, so the longer wait does not weaken supersession behavior or block independent evidence results.

Mocked tests verify timeout mapping/accounting, the 60-second HTTPX request timeout, the frontend's 70-second deadline, retention of a successful response after a simulated 65-second wait for the active journey, and rejection of an older response after a newer attempt owns evidence. No OpenRouter request or real-camera inference was made for this timeout adjustment.

**Timeout-adjustment verification:** Focused backend adapter and camera-vision API tests passed (**51**); full backend pytest passed (**386**); backend Ruff passed; frontend tests passed (**7 suites**); TypeScript and production build passed; and `git diff --check` passed. The production build retains its existing nonblocking large-bundle advisory.

**Single-image policy verification:** Focused adapter, API, and Phase 7 camera/cache tests passed (**79**); full backend pytest passed (**391**); backend Ruff passed; backend import smoke passed; frontend tests passed (**7 test files**); TypeScript and production build passed; and `git diff --check` passed. The build reports the existing nonblocking large-bundle advisory. Tests use mocked transport and local synthetic JPEGs; no OpenRouter request, synthetic provider inference, or real-camera inference was made. Successful real-camera inference remains unverified, and the human follow-up browser test is pending.

## Scope and acceptance handoff

No camera observations card, raw JSON view, map overlay, evidence reasoning, or AI Journey Briefing was added. The existing camera gallery and ordinary journey displays remain as before. Human review should compare any later approved live observation with its corresponding source frames and can verify normal browser interaction. Phase 8 remains in progress pending human acceptance; Phase 9 is the consumer of this typed internal evidence and remains unstarted.
