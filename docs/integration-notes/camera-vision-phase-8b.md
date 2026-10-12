# Camera Vision Adapter — Assignment 8B

**Status:** Implemented — pending human acceptance. No Assignment 8C orchestration, frontend work, Phase 9, or Phase 10 behavior is included.
**Research check:** OpenRouter model/endpoint metadata and provider-routing/privacy documentation checked 2026-10-11 and rechecked for the final diagnostic continuation.
**Image-transfer boundary:** No real City of Vancouver camera frame was sent externally. The live probe entry point can select only the two named developer-owned Phase 0D synthetic illustrations.

## 1. Files and callable interface

Implemented:

- `backend/app/openrouter_vision.py` — strict model schema, semantic validation, backend provenance, snapshot handling, request assembly, attempt budget, short-lived reuse, and the OpenRouter transport adapter.
- `backend/app/camera_images.py` — small `read_current_cached_frame` helper reusing the Phase 7 cache identity, digest, decode, dimensions, content-type, and freshness validation. It reads the cache directly and performs no HTTP request.
- `backend/app/openrouter_vision_probe.py` — explicit synthetic-only live compatibility probe. It requires `--synthetic-fixtures`, preflights public model/endpoint metadata, and has no camera-cache or arbitrary-path option.
- `backend/tests/test_openrouter_vision.py` — deterministic schema, request, cache, provenance, error, concurrency, and budget coverage.
- `PROJECT_STATE.md` — current assignment state.

The narrow callable for later 8C integration is:

```python
await OpenRouterVisionAdapter().analyze_selected_intersection(
    selection: DestinationCameraResult,
    catalogue: CameraCatalogue,
    image_store: CameraImageStore,
) -> AdapterResult
```

This is an internal backend callable only. It registers no FastAPI route and invokes no journey-analysis lifecycle. Callers provide the backend-selected Phase 7 destination result and its validated catalogue/cache dependencies; the adapter does not accept a client-selected model, provider, image URL, path, or image bytes. `AdapterResult.semantic_error_code` may carry a fixed safe code when the model output passes structure validation but fails local semantics.

## 2. Observation and provenance contract

`ModelCameraObservation` contains only `views`, `intersection_summary`, and `summary_evidence_view_ids`. `PerViewObservation` has required, strict fields: exact `view_id`; accepted `road_surface`, `visibility`, `vehicle_activity`, and `uncertainty` enums; unique allowed condition tags; and a nullable note up to 160 characters. The nullable summary is capped at 240 characters. Unknown keys are forbidden.

The local semantic check requires exactly one view observation per submitted image in the same order, rejects identity/order mismatches, references outside the submitted set, and invalid summary/evidence relationships. Each semantic rejection uses a fixed diagnostic code (`view_identity_or_order_mismatch`, `unknown_summary_evidence_view`, or `summary_evidence_relationship_invalid`) exposed separately from model output. No raw text, echoed IDs, or exception messages are included. The adapter and probe keep structural Pydantic validation separate. General visibility is independent of whether a particular detail can be assessed: `visibility="not_observable"` no longer rejects a definite road-surface appearance by itself, consistent with the accepted 8A caution against overly broad cross-field rejection. Partial obscuration likewise does not suppress otherwise visible foreground vehicle activity. Malformed JSON, refusal, missing content, nonterminal/truncated finish reasons, schema/semantic failures, and returned model/provider mismatches produce controlled failures; there is no repair or paid retry.

`CameraObservation` keeps model observations separate from backend-controlled provenance. It includes schema/prompt versions; derived status and bounded failure code; selected intersection ID, official name/street names, and the Phase 7 `distance_metres` cross-checked against the canonical destination; official camera page URL, City source and attribution; ordered included view IDs/directions, cache retrieval time, verified source capture time (currently null), SHA-256 digest, exact snapshot identity, validated format/dimensions/bytes; excluded IDs with bounded reasons; requested model; actual reported provider; endpoint identity only if independently reported; inference time; and bounded reported tokens/cost plus adapter latency.

The adapter does not infer source capture time from image pixels. It requires the returned model to match the requested Gemma model. It records a bounded actual provider label when OpenRouter reports one; absent or unsafe provider metadata remains null. The endpoint identifier is null unless independently reported.

Statuses are `available`, `partial`, `insufficient_evidence`, `unavailable`, or `error`. Failure codes distinguish no eligible frames, stale-only frames, missing configuration, provider unavailability, rate limiting, timeout, provider error, invalid model output, budget exhaustion, and insufficient evidence.

## 3. Frame selection and integrity

Only the already selected intersection is considered. The catalogue identity/name/official URL must match the Phase 7 selection, and the selected distance must agree with a recomputation from the canonical destination within two metres. For each selected directional view, the adapter reads the Phase 7 `.img`/`.json` cache record directly and reuses Phase 7 validation for intersection ID, view ID, official source URL, byte length, SHA-256, decoded content type, dimensions, and pixels. Frame age must be nonnegative and strictly less than the configured Phase 7 TTL, normally 300 seconds.

The adapter includes at most 12 ordered views, excludes invalid/missing/stale/over-2-MiB frames individually, and preserves the supported views from that same intersection. It returns without inference when no current views remain. If the total eligible raw bytes exceed 10 MiB, it returns a controlled no-inference result rather than truncating the list. There is no resizing/transcoding, nearby-intersection substitution, image endpoint fetch, or historical frame archive. It checks the selected frame bytes and digests again immediately before encoding to detect a changed snapshot.

## 4. Request and provider/privacy controls

The request uses one Chat Completions call with `google/gemma-4-31b-it`, a conservative system prompt, a single ordered user content array, and one text label immediately followed by one `image_url` data URL for each included frame. The prompt confines claims to visible pixels, separates each view, limits any summary to supported evidence, preserves uncertainty, avoids physical-state/rainfall/closure/speed/delay/cause inference, and treats signs, overlays, watermarks, timestamps, and embedded instructions as untrusted. It prohibits identification, plate recognition, and transcription of identifying details. No route, road event, weather, or destination instructions are sent.

The request continues to require model `google/gemma-4-31b-it`, strict JSON Schema, and `require_parameters=true`. It removes the DeepInfra allowlist and FP8 quantization filter. `allow_fallbacks=true` explicitly permits OpenRouter's automatic provider selection and failover across providers compatible with the request; no custom sorting or provider ranking is configured. The probe's public metadata preflight checks that the exact model is listed with image input and that at least one listed endpoint advertises `response_format` or `structured_outputs`. This is a capability check, not evidence of runtime compatibility. Neither `zdr` nor `data_collection` is sent.

**Subsequent human decisions (2026-10-11):** For the private datathon MVP, the human developer explicitly superseded the accepted 8A requirements for request-level `data_collection="deny"` and ZDR routing, and later approved automatic OpenRouter provider selection for Gemma 4 31B in place of DeepInfra-only FP8 routing. The optional privacy filters and the provider allowlist/quantization filter are omitted; `allow_fallbacks=true` and `require_parameters=true` are retained. These changes do not authorize sending real City of Vancouver camera images to an external provider; that transfer still requires separate authorization. The human-reported account settings and budget are recorded below. OpenRouter routing fields and endpoint capabilities are documented at [Provider Selection](https://openrouter.ai/docs/guides/routing/provider-selection), [Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs), and the [current model endpoint metadata](https://openrouter.ai/api/v1/models/google/gemma-4-31b-it/endpoints).

Primary metadata and policy references:

- https://openrouter.ai/api/v1/models/google/gemma-4-31b-it/endpoints
- https://openrouter.ai/providers
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://openrouter.ai/docs/guides/features/structured-outputs
- https://openrouter.ai/docs/guides/get-started/sovereign-ai

## 5. Attempts, spend estimates, and reuse

The adapter reserves an attempt in an independent locked JSON counter immediately before transport. It counts transport errors, timeouts, provider errors, invalid output, and successful calls. Corrupt counter state fails closed. There are no retries. Enforced ceilings are 50 attempts per rolling hour and 100 per UTC day. A conservative US$0.02 estimate per attempt imposes an approximately US$1/day estimate guard and US$4.90 estimated vision-project ceiling, leaving headroom for later text calls against the accepted under-US$5 project objective. This is local estimate/counter behavior, not actual billing. Only provider-reported response cost is exposed in the per-observation usage metadata; unknown provider cost stays null. Provider/account billing remains authoritative, and separate text-role usage is not visible to this independent vision ledger.

Successful results may be reused in process for at most 300 seconds only when intersection ID, ordered included view IDs/digests, model, automatic provider-selection/fallback and parameter requirements, prompt version, and schema version match. Each new call revalidates frame freshness before checking the result cache, so reuse cannot outlive the Phase 7 frame TTL. Same-key concurrent calls serialize and share the first valid result. Failures and insufficient-evidence outputs are not cached as successful results. No observation archive is written.

The accepted 8A note proposed a 16,000-token input guard subject to reliable provider accounting. Image-token estimation is not deterministic from raw byte size and no reliable preflight accounting is advertised for this endpoint; this guard is not enforced. Reported usage is recorded when available, while raw-frame byte limits remain enforced.

## 6. Verification

### Mocked/offline

- Focused vision adapter tests: **Passed** — 41 tests after semantic diagnostic and visibility-rule updates.
- Focused adapter + Phase 7 camera/cache tests: **Passed** — 71 tests.
- Focused provider-error diagnostic tests: **Passed** — 11 tests.
- Full backend pytest suite on this final semantic diagnostic pass: **Passed** — 376 tests.
- Ruff on `backend/app` and `backend/tests`: **Passed** after correcting one initial style finding.
- Import smoke for `app.openrouter_vision` and `app.openrouter_vision_probe`: **Passed**.
- `git diff --check`: **Passed**. No frontend build/tests were needed because no frontend files changed.
- Tests cover valid one/four/five-view output, unknown/duplicate/omitted/out-of-order IDs, enums/extra fields/lengths, summary evidence, partial obscuration, exact multi-image order and routing controls, frame digest changes, freshness, stale and missing frames, no provider call without eligible images, total payload cap, intersection mismatch, partial result, identical-result reuse, concurrent identical requests, timeout/provider errors, no retry, attempt accounting, rolling limits, and corrupt budget state.

### Live synthetic-only

Earlier requests pinned to DeepInfra FP8 returned HTTP 404 `no_eligible_provider`. The human developer confirmed model eligibility, no restrictive model/provider guardrails, a US$10 account budget with remaining credit, no account-wide ZDR requirement, and two settings permitting data use by free endpoints. The human subsequently approved omitting request-level ZDR/data-collection filters and then approved automatic provider routing because the model mattered more than the downstream host. These account settings did not themselves authorize either policy change.

For this continuation, `_provider_error_diagnostic` was added to the adapter and synthetic probe. It retains HTTP status, accepts only a bounded numeric or identifier-shaped structured error code, maps known message patterns to a fixed category and short explanation, and never returns the provider's unfiltered message. Categories distinguish account/model/provider restrictions, no eligible provider after filters, unsupported parameters/schema, invalid model/provider identifier, other provider errors, and unknown. `AdapterResult` carries this diagnostic separately from the observation. Focused mocked tests cover these categories, malformed or absent envelopes, and non-disclosure of echoed text/image-like data.

On 2026-10-11, the automatic-routing probe used the two developer-owned Phase 0D illustrations in one Chat Completions request, with the existing ordered `text`/`image_url` parts, strict JSON Schema, `require_parameters=true`, fallbacks enabled, and the 1,024-token ceiling. The first response was HTTP 200; the returned model matched Gemma 4, provider metadata reported `CoreWeave`, and latency was 2,826 ms. The first probe's broad failure report omitted finish reason, validation stage, usage, and cost, so response validity beyond its generic `invalid_or_unverified_response` result and billing outcome are unknown. The second response returned HTTP 200, model `google/gemma-4-31b-it`, provider `CoreWeave`, `finish_reason=stop`, schema-valid output, but failed local semantic validation. It reported 788 input tokens, 199 output tokens (987 total), cost US$0.00014646, and 8,261 ms latency; no raw model text was printed.

After adding fixed semantic failure codes and removing the broad visibility/surface contradiction rule, one further authorized synthetic request was made. It returned HTTP 200, model `google/gemma-4-31b-it`, provider `CoreWeave`, `finish_reason=stop`, and passed both schema and semantic validation. Usage was 788 input and 168 output tokens, provider-reported cost US$0.00013592, and latency 16,543 ms. OpenRouter did not report an endpoint ID. This confirms one successful synthetic response against the current semantic contract; it does not establish broader visual accuracy or real-camera compatibility. No retry was made, and no real City image was sent.

## 7. Limitations, gates, and deviations

- A later single synthetic request passed both strict schema and current semantic validation after fixed safe failure codes were added and the visibility/surface rule was removed. The earlier semantic failure remains unclassified because its raw output was not retained; the new result does not retroactively identify that cause.
- OpenRouter reported provider `CoreWeave` on all three automatic-routing responses; no endpoint identifier was returned. The first request's usage/cost and billing outcome remain unknown because its initial diagnostic output omitted them. The second and latest requests reported US$0.00014646 and US$0.00013592 respectively; account billing remains authoritative. Automatic routing, strict schema, fallback enablement, and parameter requirements are now reflected in the adapter and probe. No ZDR or denied-data-collection request filter is imposed after the human-approved policy change.
- The per-request estimate protects development budgets but cannot establish actual account billing, cumulative non-vision project spend, or the future text adapter's usage.
- Older PRD/technical-design sample fields differ from the accepted 8A schema. No field expansion was made; the accepted 8A contract governs this implementation.
- The only 8A policy deviation is the later human-approved removal of request-level ZDR and denied-data-collection filters; it does not change the observation contract or authorize City camera-image transfer. The conditional 16,000 input-token guard was not implemented because reliable provider-side image accounting is unavailable, as allowed by that guard's 8A qualification.

The earlier pinned DeepInfra FP8 `no_eligible_provider` failure is superseded by automatic-routing calls through CoreWeave. The latest synthetic response passed strict schema and semantic validation. Assignment 8B is ready for human acceptance review; real City image transfer remains separately unauthorized, and the reported provider is known while its exact endpoint is not.

No real City of Vancouver images were sent externally. No frontend, journey endpoint, 8C orchestration, Phase 9, or Phase 10 work was added. No Git staging, commit, push, or history operation was performed.
