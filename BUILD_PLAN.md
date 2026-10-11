# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 8 — Multi-View Camera AI Analysis
**Phase status:** Planned; not yet implemented. Each assignment requires separate human authorization and acceptance.
**Source:** `docs/implementation-plan.md` Phase 8; `docs/prd.md`; `docs/technical-design.md`; accepted Phase 7 camera contracts and `docs/data-licensing-and-commercialization.md`. Where documents differ, inspect the repository and report the discrepancy rather than silently rewriting accepted authority.
**Previous phase:** Phase 7 — Vancouver Camera Pipeline, Assignments 7A–7E complete and human accepted on 2026-10-11; final Git checkpoint committed and pushed by the developer.

### Objective

Convert the **currently retrieved directional images from the one selected destination camera intersection** into **one conservative, structured, source-attributed `CameraObservation`**, through a controlled OpenRouter multimodal request.

**Accepted Phase 7 current frames → bounded image eligibility/snapshot → one multi-image vision call → strict schema and provenance validation → internal `CameraObservation` evidence → Phase 9 evidence organization → Phase 10 AI Journey Briefing.**

The phase must deliver:

- verified OpenRouter multimodal model and provider capabilities, with actual image payload and structured-output contract evidence;
- a small, controlled visual-observation schema and task prompt that distinguish visible facts, tentative interpretations and unknowns;
- exactly **one logical model assessment per explicit journey-analysis operation for the selected intersection**, containing all eligible current directional frames from that intersection; no per-direction model calls;
- strict grounding in the supplied pixels: no invented conditions, unsupported traffic severity, route-specific conclusions or extrapolation beyond what is visible;
- deterministic Pydantic validation, provenance, status and failure/degraded states;
- bounded model request time, input size, output size, upstream attempts and cost, plus intentional handling of repeat Analyze Journey actions;
- reuse of the accepted latest-frame camera cache, with no historical image archive or persisted image prompt payloads;
- a narrow backend observation/status contract for downstream evidence consumers, without a separate camera-AI frontend card;
- offline regression, small permitted live validation, human review of source frames against normalized telemetry, and acceptance of the internal handoff contract.

**Phase 8 extracts internal camera telemetry only.** It must not display raw observations or a new AI interpretation card. Phase 9 later organizes relevance/timeline evidence; Phase 10 creates a single prominent, user-facing AI Journey Briefing at the top of Journey Intelligence. That briefing should be the primary summary, with road events, weather, images, and the map as supporting evidence. Neither downstream phase is authorized here.

### Locked product boundaries

- **Driving only**, City of Vancouver canonical destination, selected route and manual **Analyze Journey** remain authoritative.
- **One selected camera intersection** per analyzed destination. Use the already-selected intersection, not a second nearest-camera search invented by the AI layer. Do not analyze nearby map-marker cameras.
- Use **all eligible fresh directional views** from that selected intersection in **one logical OpenRouter request**. Support variable view counts (including one and five); preserve each original source direction label. Do not stitch images into misleading panoramas.
- Observation describes what is **visually discernible near the camera intersection**, not the exact destination or the entire driving route.
- **No automated weather verification, traffic speeds, crash detection, road closure declaration, pedestrian identification or license-plate interpretation.** No inference of precipitation or congestion merely because a scene looks dark/wet/occupied.
- **No archive or time series** of submitted images, prompts containing image bytes, or raw model responses. No background inference, polling or automatic repeat calls.
- **No user-facing camera AI observations subsection.** The accepted Phase 7 directional gallery remains unchanged. Only the later journey briefing will synthesize camera evidence for users; no raw observation JSON or independent vision narrative is presented.
- Keep camera-image licensing uncertainty accurately documented. The user has accepted a private, noncommercial hobby MVP development posture but this is **not legal permission**. Phase 8A separately reviews the real transfer of image bytes to OpenRouter and its downstream provider before any live-image submission; use synthetic or explicitly licensed test images until the human authorizes that transfer.

---

## 2. Execution Scope and Authorization

Phase 8 consists of four separately authorized assignments. Completing one does not authorize the next. Human acceptance and Git operations remain separate, manual checkpoints.

### Assignment 8A — Vision Contract, Model and Provider Validation

- Inspect actual Phase 7 current-frame, opaque-reference, cache, API and frontend contracts and any existing OpenRouter/client infrastructure.
- Verify current OpenRouter image-input format, supported image counts/sizes, model endpoint vision capability, JSON-schema or JSON-mode support, routing/retention settings, error shapes, pricing and billing limits. **Do not hardcode a model based only on historical documentation.**
- Compare a small number of plausible currently available models for **multi-image vision, structured output, reliability, cost and latency**. Recommend **one primary model** and at most one fallback for human selection; do not automatically invoke multiple models.
- Define a minimal `CameraObservation` schema, prompt contract, clear field semantics, allowed unknown values, per-view evidence references and refusal/insufficient-visibility behavior.
- Establish the input eligibility policy (fresh vs stale, image dimensions, maximum views/bytes, image ordering and labels) and request budget policy.
- Inspect OpenRouter/provider data-handling and third-party image-sharing implications; preserve existing City rights findings and distinguish private development from third-party transmission. Record the human decision needed before sending real City frames.
- Make at most a **small, explicitly authorized and budgeted** contract probe using synthetic/developer-owned test images; no real Vancouver camera frames are transmitted during 8A unless the human separately authorizes it after review.
- Produce source evidence, tiny nonsecret fixtures, draft schema/prompt and a recommendation for 8B. No production vision adapter or UI.

**8A exit gate:** Human approves the actual primary model/provider route, vision/schema contract, explicit upstream call budget and real-frame transfer posture (or a synthetic-only implementation path). If unsupported, report a focused alternative without guessing.

### Assignment 8B — Bounded OpenRouter Vision Adapter

- Implement a narrow backend OpenRouter client/adapter for **one request containing multiple labeled images**. Reuse existing HTTP/config conventions and the 8A-accepted schema and prompt.
- Source frames only from the validated current-frame cache/selection contract; reject arbitrary client image URLs, user-supplied local files or off-host imagery.
- Validate image and metadata eligibility before invoking the model; skip or mark stale/invalid frames according to the 8A policy. Never silently substitute views from another intersection.
- Enforce backend-held API key, selected model/provider settings, fixed endpoint, timeouts, response/output limits, budget/attempt limits and safe error handling. Avoid uncontrolled retries or fallback cascades; billable attempts must count even when transport/parse fails.
- Parse the provider response and validate all `CameraObservation` fields with typed Pydantic models and cross-checks for source view IDs, unsupported categories and impossible references.
- Return typed available/partial/insufficient-evidence/unavailable/error outcomes, retaining accurate model, intersection, frame-retrieval and inference timestamps.
- Prevent duplicate simultaneous inferences for the same requested snapshot where feasible. Do **not** build a historical observation database or persist raw image-filled prompts/responses.
- Use mocked HTTP and synthetic/test-owned images for routine tests. If one bounded real-frame live call was separately authorized after 8A, test once within the recorded budget.

**8B boundary:** Adapter and offline tests only, with a narrowly scoped CLI/test harness if helpful. No journey API or frontend integration, no Phase 9 synthesis.

### Assignment 8C — Journey-Triggered Vision Orchestration and API

- Connect the accepted Phase 7 selected-intersection current frames to the 8B adapter through a **narrow backend operation** tied to the canonical destination and explicit journey analysis lifecycle.
- Prefer a **separate typed camera-observation API** from `POST /api/trips/analyze` so road/weather results and the image gallery are not blocked by model latency. Inspect existing route and camera contracts before finalizing endpoint and request schema.
- Prevent user-provided arbitrary image references or unrelated intersection IDs from inducing model processing. Define a short-lived, server-validated selection/snapshot identity or equally narrow correlation mechanism appropriate to the existing code.
- Require one logical model call for all eligible views from the **one selected intersection**, not a call per frame; handle zero qualifying views without calling OpenRouter.
- Respect request cancellation and stale-response identities; return source-specific statuses and metadata, not raw frames or unvalidated model prose.
- Bound repeated clicks and concurrency: no implicit inference on page load, destination typing, marker hover/click or camera image GET requests. Any inference cache, if needed, is short-lived and bounded by frame identities and model/prompt/schema versions; no historical accumulation.
- Preserve existing camera image delivery, nearby metadata markers, Road Ahead/DriveBC findings, weather and selected-route behavior.
- Add focused API/transport/duplicate-request tests and full backend regression. Perform a small authorized live probe only if the 8A transfer gate permits it.

**8C boundary:** Backend orchestration/API plus only the minimum manual-journey request wiring needed to initiate/retain an internal result safely; no camera-AI presentation or general journey briefing. Do not begin 8D.

### Assignment 8D — Internal Vision Pipeline Integration and Human Acceptance

- Complete and verify the end-to-end **CameraObservation telemetry pipeline**. Eligible directional camera frames from the already-selected intersection produce one schema-validated, provenance-bearing result from the approved OpenRouter adapter.
- Treat `CameraObservation` as **internal machine-readable evidence** for Phases 9–10, not a standalone user-facing report. Do not create a Camera AI Observation card, expose raw JSON in Journey Intelligence, or add a new map layer/dashboard.
- Preserve backend-controlled intersection/view identities, original direction labels, source attribution, frame retrieval and verified source-capture times if available, observation generation time, selected model/provider, coverage, and status. Never trust the model to invent provenance.
- Support honest **available**, **partial**, **insufficient evidence**, **stale imagery**, **unavailable** and **error** outcomes with explicit unknown/not-observable values. Structural validation is required but does not establish the truth of image claims.
- Make a small, documented, typed and validated result contract usable by a later evidence-assembly stage. Do not implement Phase 9 relevance reconciliation or Phase 10 briefing.
- Preserve the Phase 7 Destination Cameras gallery unchanged. Users may inspect original images, but they do not see standalone AI camera interpretation or telemetry JSON.
- Tie inference to **at most one logical assessment per explicit manual Analyze Journey cycle**, within approved cost and request constraints. Do not call OpenRouter on render, image GET/reload, page mount, marker interactions, or unrelated UI changes.
- Guard against obsolete results after origin, destination, route-selection, or journey-analysis changes. Slow/failed/invalid vision outcomes must not delay or replace camera images, Road Ahead, DriveBC, weather, or routing results. Already-started provider requests may be billable even when the browser abandons the result.
- Reject malformed, unsupported or unverifiable model output rather than passing it to downstream reasoning. Use a typed unavailable/degraded state instead of invented fallback evidence.
- Test model output validation, API contract, current-frame/selection binding, duplicate-call and budget controls, stale results, partial/failed provider outcomes, and independent road/weather/gallery behavior. Run relevant backend/frontend suites, Ruff, TypeScript/build, and repository hygiene checks according to changed scope.
- Conduct only previously authorized and budgeted real-provider assessments. Human acceptance must include comparing representative structured observations to their corresponding source frames and examining unknown/insufficient-evidence handling. Synthetic-only verification must not be reported as actual City-image inference.
- Record the schema/version, model/provider route, request/cost evidence, verification results, nonblocking limitations, and internal handoff details in `docs/integration-notes/` and `PROJECT_STATE.md`.

**8D boundary:** No camera AI frontend card, raw JSON UI, Phase 9 camera/weather/road reconciliation, Phase 10 AI Journey Briefing, route scoring, rerouting, image archival, or inference on nearby map-marker intersections.

**Assignment rule:** Codex receives authority for only the currently approved assignment; stop and report before starting another. No Git staging, commits, pushes, merges, rebases, tags or history operations.

---

## 3. Established Accepted Baseline

### 3.1 Core application and road evidence

- FastAPI backend; React/Vite/TypeScript; MapLibre/MapTiler dark map; Vite `/api` proxy; backend-only credentials.
- Canonical origin/destination and City of Vancouver destination validation; ORS driving candidate routes with explicit selection.
- User-driven `POST /api/trips/analyze` with original route geometry and stale-request invalidation.
- Road Ahead municipal construction/closure route findings with existing map/panel interactions and caching.
- DriveBC Open511 regional events, separately mapped and route-relevant findings, with conservative source-status handling.

### 3.2 Destination weather (Phase 6)

- OpenWeather One Call 4.0 current and 15-minute forecasts with 600-second caches and an existing persistent **100 upstream attempts per UTC day** application budget; provider account limit separately set to 500/day.
- ECCC GeoMet/SWOB actual station observations with 600-second cache and conservative station-level provenance.
- `destination_weather` remains independently attributed; AI camera observations are **not** a weather forecast or measured station observation.

### 3.3 Cameras (Phase 7A–7E)

- `backend/app/vancouver_cameras.py`: validated official catalogue and directional URL enrichment; approximately 24-hour schema-validated cache, last-good fallback. Live Phase 7B observation: 219 intersections, 844 discovered directional URLs; source counts are not immutable product constants.
- `backend/app/camera_images.py`: canonical destination selection, nearest usable intersection, complete available directions from that intersection; initial 2 km / 12 candidate / 24 request bounds.
- Accepted 7C image pipeline: source-host restrictions, Pillow validation, latest-frame-only ephemeral cache, **300-second default freshness TTL**, maximum **900-second stale age**, no image history or background polling.
- `POST /api/cameras/nearest` and opaque `GET /api/cameras/images/{reference}` for destination selection and validated current-frame delivery.
- Phase 7D gallery integrated with explicit Analyze Journey and request identity; one intersection with its variable number of directional views.
- Phase 7E `POST /api/cameras/nearby` metadata-only, up to four nearby marker locations; marker click opens official City webpage; marker images are **not** collected for inference.
- Bottom-left map legend removed, MapLibre attribution compact. Accepted MVP limitation: selected Road Ahead line emphasis may persist across input change/Find Routes but clears on Analyze Journey. Do not reopen as part of Phase 8.
- Manual camera failure-isolation case and exhaustive narrow-screen review were deferred; existing automated coverage exists.

### 3.4 Existing contracts must remain authoritative

Before changing any camera-frame metadata, response shape, cache identity, frontend request lifecycle, image headers, or OpenRouter configuration, **inspect current code** and record any discrepancy with this summary. Do not duplicate already working source adapters, caches or typed models. Preserve the accepted Phase 7 frontend and camera presentation.

---

## 4. Vision Evidence Contract and Observation Semantics

### 4.1 Scope of interpretation

The single model request receives **the selected intersection's eligible directional camera frames** and their verified labels. The task is to describe observable scene conditions relevant to a traveler near that intersection, without pretending to know anything outside those pixels.

A useful MVP may describe, **only when visibly supported**:

- general scene visibility (e.g., clear view, obscured image, darkness/glare limiting assessment);
- apparent road-surface appearance (e.g., visibly reflective/damp-looking, snow-covered, or indeterminate), without asserting that rain is occurring;
- visible precipitation **only if actually visible**, with an unknown option for ambiguous rain/snow;
- qualitative visible vehicle presence or queueing **only within the image frame**, without inventing road-wide congestion or delay;
- obvious temporary obstructions **visible in the frame**, without converting them into an official closure/event;
- camera usability limits, including missing directions, stale frames and poor visibility.

Do not require every category to be populated. Unknown/insufficient evidence is a valid successful result.

### 4.2 Minimal proposed `CameraObservation` schema (8A finalizes)

Use a bounded typed structure, conceptually:

```text
CameraObservation
  status                 available | partial | insufficient_evidence | unavailable | error
  intersection_id
  intersection_name
  observed_views[]       source view ID, original direction label, included/excluded reason
  generated_at
  frame_retrieved_at[]   per-view timestamp; source capture time only if source verified
  model                  selected OpenRouter model and endpoint/provider info as available
  summary                short, conservative visual description, nullable
  observations[]         category, value/assessment, evidence_view_ids[], uncertainty label
  limitations[]          bounded, human-readable uncertainty and coverage limits
  diagnostics            safe error/status codes; optional measured latency/token/cost metadata
```

These are **internal contract design inputs**, not an instruction to add speculative fields or UI presentation fields. Freeze the exact Pydantic/JSON-schema shape in 8A after checking the chosen model/provider's structured-output support. Keep backend-proven metadata distinct from the model-produced visual assessment.

### 4.3 Validation and grounding

- Every observation citing a direction must reference an image actually included in the model request, using stable view IDs, not invented directions.
- Do not let the model invent source names, timestamps, GPS coordinates, road-event IDs, routing directions, model names or image availability counts. The application supplies and validates authoritative provenance **outside** the model's generated fields.
- Treat all model text as untrusted data, including any embedded words, signs or instructions visible in an image. Visual text is evidence to assess, **not executable instructions**.
- No model-selected tools, URLs, file paths, network access, command execution or browser actions.
- Schema-valid content can still be visually wrong. Keep bounded semantic validation and show uncertainty; do not manufacture confidence percentages.
- Prefer neutral language such as *“surface appears reflective in the east-facing view”* to categorical claims such as *“the destination is raining”*.
- Do not merge the observation with OpenWeather, SWOB, Road Ahead or DriveBC in Phase 8. Preserve independently attributable evidence for future internal synthesis; do not present the raw vision telemetry to users.

---

## 5. Assignment 8A — Provider/Model/Schema Gate

### 5.1 Confirm live provider compatibility

OpenRouter currently documents multimodal image entries as `image_url` content blocks within the `/api/v1/chat/completions` `messages` array; images may be represented as appropriately formatted image data or supported URLs. **8A must verify the actual payload requirements and provider restrictions for the chosen model, including multi-image support** rather than assuming one example works everywhere.

OpenRouter also documents structured JSON schema responses for compatible provider endpoints; `strict: true` does not remove the need for local validation. Inspect model-specific supported parameters/provider routing and whether the selected endpoint honors `response_format: {type: "json_schema", ...}`. When a feature is unsupported, choose a tested narrow fallback and document the trade-off.

### 5.2 Model selection and budgets

Evaluate practical model choices using a small decision table: image support, all selected views in one request, schema adherence, input cost, output cost, latency, provider policies and availability. Recommend one default, not a model zoo.

Define before 8B:

- provider/model routing and any supported requirement-filtering flags;
- backend API key/config names and nonsecret `.env.example` entries;
- maximum frames per assessment (must support the accepted current five-view source example if the chosen model permits);
- maximum total image bytes/pixels and whether downscaling is needed, without storing derivative archives;
- output/token limit sufficient for the schema;
- network timeout, retry policy and maximum billable attempts per requested analysis;
- small, durable application-level upstream request budget and optional configurable monetary cap, following accepted OpenWeather guard principles where appropriate but **not sharing the weather quota**;
- whether cancelled/dropped requests count against budget (if initiated, they do);
- precise status when key/model/provider is missing or budget exhausted.

Do **not** predeclare a numeric OpenRouter budget or hardcode a specific model before 8A research and the developer's approval.

### 5.3 Privacy and data-transfer gate

Review OpenRouter's current prompt logging controls, provider-specific data-retention/training rules, and supported privacy routing constraints (where available). Confirm that using data URLs/image bytes in a request transmits the frames to OpenRouter and potentially the selected downstream model provider.

Retain the documented distinction: *private, noncommercial MVP development* is the user's scope choice, not a third-party transmission permission. Record the user's explicit go/no-go decision before the first real Vancouver frame is sent to OpenRouter. Continue synthetic/developer-owned image adapter work if this gate is not cleared; do not mislabel such tests as live City imagery.

### 5.4 8A deliverables

- `docs/integration-notes/camera-vision-phase-8a.md` or equivalent with dated official API/provider sources;
- selected model/provider proposal, pricing/support evidence and test results;
- locked `CameraObservation` field semantics plus JSON schema/prompt draft;
- explicit image selection/freshness, source-label and request-budget recommendations;
- rights/privacy status and human go/no-go decision needed for real-frame transfer;
- tiny safe fixtures and concrete 8B implementation requirements.

No production adapter or frontend code in 8A.

---

## 6. Assignment 8B — Vision Adapter Contract

### 6.1 Request assembly

- Server-only OpenRouter calls with a backend-held key; do not expose key or frame bytes to browser or logs.
- Use the eligible current frames already validated and stored by Phase 7; encode/transmit in the provider-supported format.
- One user message may contain introductory task instructions, per-view original direction labels and each corresponding image; **one request** processes all eligible images.
- Do not submit camera marker locations, unrelated City frames or saved historical versions.
- Reject zero frames, invalid/stale-only frames according to the 8A policy, oversized requests and mixed-intersection snapshots before upstream transmission.
- No arbitrary model or prompt selection by the frontend.

### 6.2 Response validation

- Use a schema-mode response where verified supported; treat the provider output as untrusted JSON/text.
- Enforce expected enums, length bounds, required/optional fields, allowed view IDs, absent-field handling and explicit uncertainty.
- Validate that observation evidence refers only to included views. Do not silently fix fabricated observations into asserted facts.
- Keep only minimal normalized observation and non-sensitive request metadata for the current journey; avoid disk-persisting full raw completions or data-URL payloads.
- Provide typed states for rate-limit, timeout, no eligible images, unsupported provider features, invalid JSON/schema, safety refusal and other controlled failures.

### 6.3 Reliability and request accounting

- Limit upstream attempts per operation; avoid multiple models, cascading fallbacks or unlimited JSON repair loops.
- Count provider-attempted calls against the approved cap even if HTTP fails or returns unusable output.
- Protect concurrent requests from exceeding the budget, and avoid accidental duplicate bills caused by double-clicks.
- When inference fails, keep the camera gallery functional and leave internal observation status explicitly unavailable; do not retry automatically merely to populate a report.

---

## 7. Assignment 8C — Camera Vision API and Journey Lifecycle

### 7.1 Request identity and trust boundary

The backend must know **which validated selected intersection/current snapshot** is being analyzed. Browser-supplied arbitrary IDs or image URLs are not sufficient authorization. Reuse a previously validated camera-selection operation or establish a narrowly bounded server-owned snapshot/correlation token, consistent with Phase 7 architecture and cache lifetimes.

The 8C design must address:

- the selected intersection remains the same as the gallery;
- snapshot includes only current eligible views and source-labeled metadata;
- image cache could expire or be pruned while a vision call is pending;
- user changes destinations, selected routes or analysis identity;
- a manual Analyze Journey action is repeated;
- a vision call is already in flight or a recent identical current-frame observation exists.

Do not introduce a database or distributed job queue to solve local MVP request coordination unless the existing architecture truly requires it.

### 7.2 Typed API behavior

Prefer a camera-specific endpoint, e.g. **conceptually** `POST /api/cameras/observe`, with a server-validated request contract decided after inspecting current camera APIs. Provide result status, normalized `CameraObservation` and provenance, not encoded image bytes or raw model responses.

Keep the new AI call independent of weather/road analysis and camera gallery success. If the upstream is slow or unavailable, the user still sees the accepted journey results. The frontend may initiate the manually authorized request and maintain nonvisual status internally, but it must not display an independent camera-AI analysis card or raw telemetry.

Make inability to analyze a missing/poorly visible scene an honest `insufficient_evidence` or unavailable state; do not turn it into a weather or traffic fact.

### 7.3 Ephemeral result policy

A short-lived in-process/result cache may be useful to avoid duplicate paid calls for the **same exact set of current frame identities, prompt/schema/model version and selected intersection**. Decide this in 8C based on existing cache semantics; do not use a long-lived observation archive or hand cached results downstream as current when frames have changed.

Do not poll automatically to refresh an observation. Every external model call must originate from an authorized manual analysis lifecycle.

---

## 8. Assignment 8D — Internal Telemetry Handoff and Acceptance

### 8.1 Internal result ownership and handoff

Complete a documented, typed `CameraObservation` result that later phases can consume without parsing provider prose or assuming unavailable source context. Preserve one selected intersection, accepted directional-view IDs, backend-verified source labels, frame retrieval times, verified capture time only if the source supplies it, inference time, processing status, and model/provider attribution.

The observation should be available through the narrow internal/API boundary established in 8C, with validation occurring **before** any downstream use. The shape must make unknown and nonobservable conditions distinguishable from negative findings. Keep authoritative IDs and timestamps out of model-generated trust boundaries; avoid new persistence or cross-phase orchestration services.

**No new user-facing observations UI:** Retain the existing multi-view gallery, road-event panels, weather panel, map markers, and selected-route display. No raw JSON, individual camera-AI card, supplementary vision summary, or model-debug output appears in Journey Intelligence. The future **Phase 10 AI Journey Briefing** is the intended primary user-facing synthesis, positioned above the supporting evidence panels.

### 8.2 Manual request lifecycle and isolation

- Initiate at most one logical vision assessment from an explicit valid Analyze Journey cycle using the narrow 8C mechanism; the browser must never call OpenRouter directly.
- Do not invoke inference on image `<img>` retrieval, route typing, component remount, camera-marker click, page load, or background refresh.
- Abandon or invalidate old observation responses when journey location, selected route or analysis identity changes. Provider billing may still occur after local cancellation; enforce budgets at request initiation.
- Missing/expired images, incomplete view coverage, failed model validation, absent credentials, provider denial or exhausted budget yield a typed status without blocking ordinary journey evidence.
- Keep the final output available for future Phase 9/10 consumption **without** implementing those downstream stages yet.

### 8.3 Verification and human acceptance

Review the structured telemetry against corresponding test-owned images or expressly approved real current City frames. Exercise visible vs unknown scenarios, view-reference validation, provider/schema failures, selected-intersection identity, delayed responses, and budget enforcement. Verify the existing gallery and road/weather UI are unaffected; desktop/narrow regression checks are proportionate to actual UI changes. Report synthetic-only tests as synthetic-only, not as a live production vision demo.

---

## 9. Validation and Test Requirements

Each assignment reports **Passed / Failed / Not run**, and distinguishes synthetic fixtures, live source frames, real OpenRouter calls and mocked results.

### 8A — evidence/model gate

- Official current OpenRouter multi-image input/schema docs and chosen provider endpoint checked.
- One model and tested fallback strategy (if necessary) recommended with pricing/limits.
- Synthetic image probe, if authorized, uses a bounded API count and nonsecret fixtures.
- Locked schema semantics, prompt rules, image freshness/eligibility and budget presented for approval.
- External image-transfer posture and privacy/retention assumptions documented accurately.

### 8B — adapter

- Multiple labeled images in one logical request; correct order and source-view mapping.
- One, two, four and five image cases where supported, zero images and mixed-intersection rejection.
- Valid JSON schema, missing/extra fields, malformed/truncated JSON, model refusal and unsupported parameter cases.
- Hallucinated view IDs, impossible enum values, excessive free text and inconsistent source fields rejected or degraded safely.
- Prompt-injection-like text embedded in fixture images cannot alter output contract or trigger actions.
- Timeout, 401/403, 429, 5xx, transport failure, unexpected response shape, cost/attempt cap and concurrency behavior.
- No raw image bytes or unredacted request payloads in persisted logs/fixtures.

### 8C — orchestration and API

- Only backend-validated selected intersection/current frames enter inference.
- Camera images are not fetched by arbitrary caller-supplied URLs or from additional map markers.
- Manual Analyze Journey triggers no more than the authorized logical inference; identical concurrent requests coalesce when implemented.
- Expired, missing, corrupt and mixed frames handled without model calls or false results.
- Repeated Analyze Journey and cancelled/outdated journeys do not show stale findings; budget accounting remains honest.
- Typed unavailable/partial/insufficient-evidence results; road/weather/image gallery unmodified.
- Full backend regression and Ruff pass.

### 8D — internal telemetry/human acceptance

- The pipeline returns a **strictly validated, provenance-bearing internal observation**, with explicit unknown/insufficient-evidence states and source-view references.
- The documented typed API/handoff contract can be consumed by future Phase 9/10 code without parsing raw OpenRouter response text; no downstream synthesis is implemented yet.
- Malformed/unsupported results never reach downstream consumers as valid evidence; provider failures do not block road, weather or camera images.
- No vision call before the authorized user action or from map markers/image rendering; request count and budget behavior are verified.
- Route/destination/selected-route changes invalidate or abandon old observations, and delayed results cannot become the active journey's evidence.
- No camera AI interpretation card or raw telemetry JSON is introduced. The existing gallery and other journey panels remain functional.
- Relevant backend/frontend tests, Ruff, TypeScript and production build pass; human review compares structured observations with source imagery and records whether real-frame transmission was authorized and actually tested.

### General hygiene

- `.env` and secrets ignored; no API keys in logs/browser.
- No tracked raw City frames or image-filled OpenRouter requests/responses.
- `git diff --check`, changed-file review and validated cache artifact ignore checks.
- No historical observation dataset, background polling or silent recurring model costs.
- Separate fact/evidence timestamps: catalogue discovery, image retrieval, source capture (if known), model generation.
- Appropriate provenance and accurate privacy/licensing limitations retained.

---

## 10. Phase 8 Non-Goals

Phase 8 does **not** authorize:

- model inference over multiple candidate intersections or the four map marker locations;
- route-wide traffic estimation, speed/delay prediction, blockage reporting as official fact or camera-based ETA changes;
- independent precipitation/weather forecasting or forcing agreement with OpenWeather/SWOB;
- combining camera observations with road events, weather/timelines or a final journey briefing (Phases 9–10);
- automated camera polling, scheduled vision calls, alert subscriptions, watch jobs or continuous monitoring;
- storing raw camera history, image datasets, vision request payloads or model responses as permanent archives;
- face recognition, person tracking, license-plate recognition or identification of individual people/vehicles;
- multiple-model ensembles, automatic benchmark sweeps over live imagery, recursive agents, tool use or autonomous decision loops;
- automatic route selection, rerouting, new travel modes, GTFS, DriveBC camera expansion or new map layer features;
- dedicated camera AI observation card, user-facing raw vision JSON, broad frontend redesign, unrelated Road Ahead highlighting repair, or speculative architecture frameworks;
- deployment/public commercialization permission claims based solely on hobbyist use.

---

## 11. Phase 8 Human Acceptance Criteria

Phase 8 is eligible for human acceptance only when:

- [ ] The actual selected OpenRouter model/provider supports the accepted multi-image input and response constraints, or the tested fallback is explicitly approved.
- [ ] `CameraObservation` schema and prompt semantics are documented, strict enough for **downstream validated telemetry consumption** and allow genuine uncertainty.
- [ ] Any transmission of real City frames to OpenRouter received a distinct human decision, with outstanding provider/source rights clearly recorded.
- [ ] Only current eligible directional frames from **one selected intersection** are submitted in **one logical request** per authorized analysis.
- [ ] Original direction labels, view IDs and times are preserved; the application, not model prose, owns authoritative provenance.
- [ ] Validated observations remain within image-visible evidence; no invented closure, exact rainfall or route-wide congestion claims.
- [ ] Malformed, incomplete, stale or source-incompatible observations are rejected/degraded instead of shown as reliable facts.
- [ ] Model credentials, image trust boundaries, request/response sizes, timeouts, attempts, cost and retries are bounded.
- [ ] Missing, stale-only or zero eligible images do not produce surprise model calls.
- [ ] Inference failure leaves the existing camera gallery and Road Ahead/DriveBC/weather/route results usable.
- [ ] No inference triggers from page load, route typing, marker click, image GET or background refresh.
- [ ] Journey request invalidation and delayed AI responses are handled correctly.
- [ ] The internal observation contract distinguishes model interpretation, source imagery identity, retrieval age, generation age and unknown capture time. No separate user-facing camera-AI observation card or raw JSON display is added.
- [ ] Offline tests, appropriate backend/frontend regressions, Ruff, TypeScript and production build pass.
- [ ] Bounded real-provider verification (when approved), human frame-to-observation review, and any proportionate browser regression checks accurately report what was and was not tested.
- [ ] No raw image archive, model-prompt cache containing bytes, source secrets or background observation history is introduced.
- [ ] Existing Phase 7 Road Ahead highlight limitation remains documented; no unrelated refactor is required for Phase 8 acceptance.
- [ ] `PROJECT_STATE.md` records the implemented contract, model/provider, cost/attempt behavior, verification and developer acceptance.
- [ ] Codex stops after the current authorized assignment and leaves all Git operations to the human.

These are human review conditions, not automatic acceptance by Codex.

---

## 12. Blockers and Escalation

Stop the affected assignment and report evidence if:

- no suitably priced and available OpenRouter model/provider can process the accepted number of images with a usable structured result;
- live City camera frame transfer to a third-party provider is not authorized for the proposed validation;
- the model repeatedly produces unsupported scene claims, unstable view references or unusable structured output;
- input size, provider routing or request cost cannot be reasonably bounded;
- current-frame selection/identity cannot safely ensure that only one accepted intersection is analyzed;
- implementation would need unrestricted image URLs, remote code execution, arbitrary model tool use or exposing API credentials;
- keeping the result consistent would require a historical frame archive, job queue or major redesign;
- vision errors would break accepted camera/road/weather features or compromise stale-response safety;
- the plan would require Phase 9/10 timeline synthesis or other unapproved work.

Report observed issue, affected requirement, minimal safe alternatives, and completed in-scope work. Continue independent safe fixture work if possible, but do not silently expand scope or bypass provider/access restrictions.

---

## 13. Phase Completion and Handoff

For each assignment:

1. Run proportionate offline verification, and bounded live checks only when authorized; distinguish mocks, synthetic images, actual City frames and real provider calls.
2. Update `PROJECT_STATE.md` factually if authorized; keep source evidence notes and explicit unresolved decisions.
3. Report files changed, exact model/provider/settings, request counts and budget consumed, tests, errors, limitations and candidate next steps.
4. Stop for human review. The next assignment requires its own explicit prompt and approval.
5. Leave all Git staging/commit/push and history operations to the human developer.

After human Phase 8 acceptance:

1. Confirm model outputs visually against the submitted source images and record limitations.
2. Record the approved model, schema version, cost/rate controls, tests and human acceptance in `PROJECT_STATE.md`.
3. Human commits and pushes the phase checkpoint.
4. Prepare a new phase-specific `BUILD_PLAN.md` before Phase 9 implementation.

This plan is authorization guidance, **not blanket permission** to execute 8A–8D at once.

---

## 14. Next Phase

**Phase 9 — Journey Relevance and Timeline Refinement**

Phase 9 may organize the accepted internal camera observations alongside independently sourced road, selected-route and destination-weather evidence, preserving source timestamps, uncertainty and geospatial relevance. It must not portray camera pixels as authoritative measured weather or official road closures.

Phase 10 will generate the primary user-facing **AI Journey Briefing** and position its card at the **top of Journey Intelligence**. A user should be able to understand the journey from the briefing alone; map, road events, weather and camera images remain optional supporting evidence. The briefing must distinguish reliable facts, uncertain visual interpretations and missing sources. No Phase 9+ work is authorized by this build plan.

