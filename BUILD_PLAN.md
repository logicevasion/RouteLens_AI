# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 3 — Drive Route Candidates + Selection
**Status:** Planned — authorized for implementation through separately approved bounded assignments; not yet verified
**Source:** `docs/implementation-plan.md`, Phase 3
**Previous phase:** Phase 2 — Journey Input + Geocoding, accepted by the human developer on 2026-10-10

### Objective

Enable users to generate, inspect, and explicitly select real driving-route alternatives between validated origin and destination locations.

Use openrouteservice (ORS) to retrieve route candidates, normalize their geographic and summary information, and display them interactively on the existing MapLibre map.

Phase 3 must deliver:

- working ORS driving-route integration through the FastAPI backend;
- normalized route candidates consistent with the approved application models;
- usable route geometry, provider-reported distance, and estimated duration;
- a functional Find Routes action;
- multiple driving-route alternatives where available;
- clear route visualization and differentiation on MapLibre;
- explicit user-controlled selection of an intended route;
- canonical selected-route state available to later phases;
- appropriate loading, no-route, error, and invalidation behavior;
- successful end-to-end verification using representative Metro Vancouver journeys.

The application should support this interaction:

**Select valid origin → select valid destination → Find Routes → inspect alternatives → select intended route → retain selected route.**

The origin may be within the supported Metro Vancouver / Lower Mainland scope.

The destination must remain inside the **City of Vancouver municipal boundary**.

Phase 3 establishes the selected geographic journey path.

It does not gather journey telemetry, determine traffic conditions, or generate AI analysis.

The user remains responsible for choosing the route most closely matching their intended journey. RouteLens is a journey-intelligence companion, not a replacement for Google Maps navigation.

---

## 2. Execution Scope

This document defines the complete Phase 3 acceptance boundary.

Phase 3 may be implemented through multiple smaller Codex assignments. Each assignment receives a bounded prompt specifying its immediate objective, expected artifacts, and verification requirements.

- Do not interpret this document as authorization to implement every Phase 3 component in one assignment.
- Implement only the work explicitly authorized by the current assignment prompt.
- Preserve the completed Phase 1 and Phase 2 functionality.
- Update `PROJECT_STATE.md` with factual implementation progress.
- Do not begin Phase 4 until Phase 3 has been accepted by the human developer.

### Planned Assignments

**Assignment 3A — Routing Backend**

Implement the ORS driving-route adapter, approved route normalization, focused routing API, provider error handling, and deterministic automated tests.

Perform targeted live ORS verification using the existing Phase 0 evidence.

Do not modify frontend route controls or MapLibre presentation.

**Assignment 3B — Route Visualization and Selection**

Integrate the routing API into the existing journey controls.

Implement the Find Routes action, display real alternatives on MapLibre, show factual route summaries, and allow the user to explicitly select a candidate.

Preserve canonical route-selection state and invalidate outdated routes when location inputs change.

Do not implement telemetry or journey analysis.

**Assignment 3C — End-to-End Routing Integration**

Complete integrated verification of route generation, candidate visualization, selection, state invalidation, provider errors, and map behavior.

Apply narrowly scoped corrections where needed.

Perform the full Phase 3 acceptance assessment.

Assignment boundaries are organizational, not independent architectural layers.

Avoid creating elaborate abstractions merely to accommodate separate assignments.

Each assignment should produce directly verifiable behavior appropriate to its scope.

---

## 3. Established Implementation and Integration Baseline

### 3.1 Accepted Phase 1 Foundation

Phase 1 established:

- a runnable FastAPI backend;
- `GET /api/health`;
- React/Vite/TypeScript frontend;
- Tailwind-based dark desktop shell;
- frontend/backend communication through Vite's `/api` proxy;
- interactive MapLibre map using MapTiler's `streets-v4-dark` style;
- fixed approximately 65/35 map-to-intelligence-panel layout;
- top journey-controls region;
- right-side intelligence placeholders;
- established frontend and backend regression checks.

Preserve the existing MapLibre lifecycle, worker configuration, attribution, error handling, and resizing behavior.

The VMware/Chromium WebGL compatibility workaround is documented in `PROJECT_STATE.md`.

Do not redesign the mapping stack.

### 3.2 Accepted Phase 2 Journey Inputs

Phase 2 established:

- backend MapTiler geocoding;
- normalized canonical `Location` objects;
- functional origin and destination autocomplete;
- independent frontend location-selection state;
- deterministic City of Vancouver destination validation;
- frontend/backend destination-validation integration;
- asynchronous request cancellation and stale-response protection;
- keyboard and pointer selection;
- loading, failure, and geographic rejection feedback.

The accepted canonical location fields are:

- `name`: required;
- `latitude`: required;
- `longitude`: required;
- `address`: optional;
- `provider_id`: optional.

Phase 3 must consume these existing canonical locations.

Do not create a second location-selection contract.

Do not allow routing requests to bypass the existing destination-validation requirement.

### 3.3 Phase 0 ORS Integration Readiness

Assignment 0C previously validated live ORS driving-route requests.

Relevant evidence is recorded in:

- `docs/integration-notes/geographic-services-readiness.md`
- `fixtures/openrouteservice/`
- `docs/integration-notes/phase-0-readiness-summary.md`
- `PROJECT_STATE.md`

Phase 0 established:

- authenticated ORS access;
- working `driving-car` requests;
- origin/destination coordinate handling;
- GeoJSON LineString route geometries;
- provider-reported distance and duration;
- successful alternative-route retrieval for three representative journeys;
- three candidates returned for each sampled journey.

However, the Phase 0 sample does **not** establish that ORS always returns three alternatives.

Phase 3 must support fewer alternatives and legitimate no-route results.

Review the existing fixtures and integration notes before implementing the ORS adapter.

Do not repeat broad provider discovery.

Targeted live verification of the actual Phase 3 integration is permitted and required where appropriate.

### 3.4 Existing Configuration

The ignored root `.env` contains the existing ORS credential:

`OPENROUTESERVICE_API_KEY`

The frontend must not receive this credential.

All ORS API requests must originate from the FastAPI backend.

Preserve:

- existing environment-loading conventions;
- `.env` ignore behavior;
- `.env.example`;
- the intentional browser-visible MapTiler key configuration;
- backend-only handling of other provider credentials.

Do not introduce a general secrets-management platform or unnecessary configuration infrastructure.

---

## 4. Required Phase 3 Workstreams

### 4.1 Backend — ORS Driving-Routes Adapter

Implement a focused ORS integration consistent with the approved technical design.

Required behavior:

- Accept canonical origin and destination locations.
- Construct valid ORS `driving-car` requests.
- Convert canonical coordinates into the required provider coordinate ordering.
- Request driving-route alternatives using the validated Phase 0 approach.
- Receive and validate provider responses.
- Normalize usable routes into application-owned candidates.
- Return a predictable result through FastAPI.
- Handle provider errors and missing routes safely.
- Keep ORS credentials server-side.

Use `httpx` and asynchronous HTTP where consistent with the existing backend architecture.

Apply reasonable request timeouts.

Avoid unnecessary provider calls.

### Provider coordinate ordering

The canonical application model uses explicit:

- `latitude`
- `longitude`

ORS and GeoJSON geographic coordinates use:

`[longitude, latitude]`

Convert explicitly when constructing requests and normalizing responses.

Do not silently invert coordinates.

### Provider behavior

ORS may return:

- multiple alternatives;
- fewer alternatives than requested;
- one usable route;
- no route for a journey;
- an upstream error.

Do not treat fewer-than-requested alternatives as an automatic failure.

Do not fabricate route candidates to satisfy a desired count.

Do not silently alter coordinates to obtain additional routes.

Do not create a provider-independent routing framework.

---

### 4.2 Route Candidate Normalization

Normalize ORS route responses into the approved `RouteCandidate` representation defined by `APP_SPEC.md` and `docs/technical-design.md`.

Consult these documents before establishing fields.

The application-owned contract must preserve the information needed for:

- presenting alternatives;
- selecting an individual candidate;
- drawing the route on MapLibre;
- retaining the selected route;
- supporting later geospatial relevance calculations.

### Required route information

Subject to the authoritative contract, normalized candidates must preserve:

- a distinct route-candidate identifier;
- route geometry;
- provider-reported distance;
- provider-reported duration;
- relevant approved route metadata.

Do not invent additional required fields unless necessary to fulfill the approved contract.

### Candidate identity

A candidate identifier must uniquely identify an alternative within the current route-result set.

Do not assume that ORS supplies a globally stable route identifier.

Request-scoped identifiers are acceptable when consistent with the approved design.

Do not create persistent route identities or database records.

### Geometry

Preserve actual provider route geometry.

The approved design's representation takes precedence.

Where GeoJSON LineString geometry is specified:

- preserve valid GeoJSON structure;
- preserve longitude/latitude ordering;
- ensure coordinates are usable by MapLibre;
- retain sufficient geographic detail for later relevance checks.

Do not simplify away important geographic detail without an approved reason.

Do not generate synthetic line segments to repair malformed routing results.

### Distance and duration

Preserve the actual provider values with explicit units.

ORS-reported distance and duration must not be misrepresented as measured real-world journey conditions.

Do not:

- invent travel times;
- apply traffic adjustments;
- claim live congestion awareness;
- calculate weather-adjusted ETAs;
- infer traffic incidents from duration values.

The UI may format factual provider estimates for readability.

---

### 4.3 Backend Routing API

Expose a focused FastAPI endpoint for requesting driving-route candidates.

Follow the API organization and approved models established by the technical design and existing backend.

### Request

Accept:

- canonical origin location;
- canonical destination location.

Required behavior:

- validate request structure using Pydantic;
- preserve coordinate validity;
- reject missing or malformed locations;
- reuse existing destination geographic validation;
- enforce City of Vancouver destination eligibility;
- permit supported origins outside Vancouver;
- avoid accepting arbitrary display strings in place of coordinates.

### Response

Return a predictable application-owned routing result containing the normalized candidate collection.

The response must support zero, one, or multiple usable candidates.

It must preserve actual route geometry, identity, distance, and duration.

Do not expose the full raw ORS response as the permanent frontend contract.

### API failures

Handle:

- invalid requests;
- unsupported destinations;
- missing ORS credentials;
- provider authentication failures;
- provider timeouts;
- rate-limit responses where distinguishable;
- upstream service errors;
- malformed provider responses;
- legitimate no-route conditions.

Use safe, meaningful error responses.

Do not expose API keys, raw request URLs containing credentials, or provider stack traces.

Do not introduce journey orchestration or telemetry APIs.

---

### 4.4 Find Routes Action

Activate a dedicated **Find Routes** action in the existing journey-controls region.

This action is distinct from the later Analyze Journey workflow.

### Enabled state

Find Routes becomes available only when:

- a canonical origin is selected;
- a canonical destination is selected;
- the destination has passed backend validation;
- the application is not already performing the same routing request.

Typed but unselected text must not qualify as a valid location.

A pending or rejected destination must not enable route generation.

### User interaction

When the user activates Find Routes:

1. Read the accepted canonical origin and destination.
2. Submit a routing request through the FastAPI `/api` interface.
3. Display a clear loading state.
4. Receive normalized route candidates.
5. Display available alternatives.
6. Allow explicit candidate selection.

Do not automatically submit routing requests on every autocomplete change.

Keep route generation a user-initiated action.

### Analyze Journey

The existing Analyze Journey action must remain inactive.

Do not enable it merely because route candidates have been retrieved or selected.

Actual journey intelligence belongs to later phases.

---

### 4.5 Frontend Routing State

Introduce focused React state for the route-generation workflow.

Required concepts include:

- current routing request status;
- returned route candidates;
- selected route candidate;
- relevant error or no-route feedback.

Use the approved frontend architecture and models.

Avoid global state-management libraries.

### Route request lifecycle

The frontend must handle:

- no route request yet;
- routing in progress;
- candidates available;
- no usable routes;
- routing request failure;
- selected candidate available.

These may be represented through a minimal discriminated state or equivalent structure.

Do not introduce a generic application workflow engine.

### Canonical selected route

A route becomes the canonical selected route only through explicit user selection.

Receiving multiple routes does not imply that the first candidate is the user's intended journey.

Do not silently select the fastest or shortest route.

The selected candidate must remain associated with the exact origin and destination pair used for its routing request.

Retain the selected route in frontend application state for later phases.

Do not introduce database or browser-storage persistence.

---

### 4.6 Route Invalidation and Asynchronous Correctness

Route results are only valid for the location pair that generated them.

This is a critical Phase 3 requirement.

### Location changes

Immediately invalidate existing route candidates and the selected route when:

- the selected origin changes;
- the selected destination changes;
- either selected location is cleared;
- either input is edited so its canonical selection becomes invalid;
- destination validation becomes pending or fails.

Do not retain a selected route whose coordinates no longer correspond to the visible journey inputs.

### Pending routing requests

If location inputs change while routing is in progress:

- invalidate the pending request;
- prevent obsolete responses from restoring old candidates;
- prevent obsolete responses from selecting a route;
- preserve unrelated valid location state.

Use `AbortController`, request identity checks, or equivalent React lifecycle mechanisms.

Do not display canceled requests as genuine provider errors.

### Repeated requests

If a new route request supersedes an earlier request, only the current response may update the application's routing state.

Do not mix candidates returned for different location pairs.

### Failed requests

A routing failure must not leave previously generated candidates appearing to apply to a newer journey.

The user should be able to retry safely.

Do not silently fall back to fabricated routes.

---

### 4.7 MapLibre Route Visualization

Display real driving-route candidates on the existing interactive MapLibre map.

### Requirements

- Use actual normalized route geometry.
- Preserve the validated MapTiler dark basemap.
- Display alternative routes clearly.
- Distinguish selected and unselected candidates.
- Keep the basemap visually usable.
- Preserve map pan, zoom, controls, and attribution.
- Keep route layers synchronized with current routing state.
- Remove stale route geometry when candidates are invalidated.

### Route styling

Use a restrained visual system consistent with the dark RouteLens interface.

For example:

- unselected candidates may use subdued line treatments;
- a selected candidate may use a stronger accent;
- overlapping alternatives should remain distinguishable where practical.

Exact colors and stroke widths are routine implementation decisions.

Do not introduce decorative route animations or excessive visual effects.

### Map interaction

Support route selection through the approved user interface.

A route list or card control must permit explicit candidate selection.

Clickable map geometry may provide a complementary selection method if straightforward and consistent with the technical design.

Do not make map-line clicking the only route-selection mechanism.

### Viewport behavior

When routes become available, adjust the map viewport so that the relevant route geometry is reasonably visible.

Preserve usable padding and avoid clipping the route beneath interface controls.

Do not implement continuous camera tracking or navigation guidance.

### Route markers

Simple origin/destination markers are permitted when useful for interpreting the displayed journey.

They must derive from actual canonical coordinates.

Do not introduce unrelated map overlays or location layers.

### Lifecycle

Use MapLibre source/layer management consistent with the existing `VancouverMap` architecture.

Avoid recreating the entire map when routes or selection state change.

Ensure route layers clean up appropriately.

Do not break existing map initialization or resize behavior.

---

### 4.8 Route Alternatives and User Selection

Allow the user to inspect and choose from actual returned candidates.

### Candidate presentation

Display enough factual information to distinguish alternatives.

Useful information includes:

- route label or ordinal;
- distance;
- estimated duration;
- selected/unselected state.

The exact display should follow the approved product design.

Do not invent road names, congestion scores, reliability ratings, or comparative recommendations.

If the provider does not supply a meaningful route name, use a neutral identifier such as:

- Route 1;
- Route 2;
- Route 3.

These labels identify candidates, not rankings of route quality.

### Explicit selection

The user must be able to select a candidate through an accessible control.

Requirements:

- selected route is visually distinct;
- selected route remains identifiable in the interface;
- selecting a different candidate updates canonical selected-route state;
- selection updates the map presentation;
- the chosen candidate belongs to the current route-result set.

Do not automatically choose the first route.

### Alternative counts

Support:

- one valid candidate;
- two candidates;
- three candidates where supplied;
- a different valid count if supported by the approved adapter;
- no valid candidate.

The absence of three alternatives is not by itself a defect.

Do not create duplicate routes to fill the list.

---

### 4.9 Route Summary and Intelligence Panel Integration

Use existing interface regions where appropriate.

The right-side intelligence panel may display factual route-selection information, such as:

- selected route label;
- distance;
- provider-estimated duration;
- indication that journey intelligence is not yet available.

Keep route-selection information visually distinct from future AI or telemetry findings.

Requirements:

- Do not fabricate road incidents.
- Do not display live traffic claims.
- Do not imply camera or weather analysis has occurred.
- Do not generate an AI briefing.
- Preserve honest placeholders for unimplemented capabilities.
- Avoid materially redesigning the existing 65/35 shell.

The interface should communicate that route selection is complete while journey intelligence remains a later step.

---

### 4.10 Travel Mode

Phase 3 supports driving routes only.

Requirements:

- Drive remains the active mode.
- ORS requests use `driving-car`.
- Transit remains inactive or clearly unavailable.
- Do not request transit itineraries.
- Do not integrate TransLink data.
- Do not imply driving and transit routes are interchangeable.

Preserve the approved future Drive / Transit product direction without introducing Phase 10 functionality.

---

### 4.11 No-Route and Failure UX

Provide understandable user feedback for:

- route request in progress;
- provider unavailable;
- provider timeout;
- rate limiting where distinguishable;
- invalid routing request;
- no usable route candidates;
- successful route retrieval.

### No-route behavior

If the provider legitimately returns no usable candidate:

- show an appropriate message;
- retain the valid origin and destination;
- leave selected-route state empty;
- permit retry or location changes.

Do not fabricate a direct-line route as a replacement.

### Provider errors

A provider failure must be distinguishable from a legitimate no-route result.

Do not present an upstream timeout as evidence that the requested journey has no route.

Keep errors concise and actionable.

Do not expose raw provider error details or credentials.

---

## 5. Expected Scope and Artifacts

Phase 3 may create or modify:

- `backend/app/` — focused ORS adapter, route models, and routing API;
- `backend/tests/` — route normalization, API, error, and regression tests;
- `frontend/src/` — route request state, route controls, candidate presentation, and MapLibre layers;
- relevant TypeScript route contracts;
- narrowly scoped styles and visual integration;
- sanitized routing fixtures where useful;
- dependency manifests only if justified;
- `README.md`, where startup or API instructions require updates;
- `PROJECT_STATE.md`.

These are anticipated areas, not a strict filesystem allowlist.

Keep implementation consistent with the approved technical design.

Create only what the current bounded assignment requires.

Avoid speculative abstractions for future data sources, route intelligence, journey persistence, or transit routing.

---

## 6. Non-Goals

Phase 3 must not implement:

- Road Ahead construction or closure ingestion;
- DriveBC Open511 incidents;
- Vancouver webcam selection or image ingestion;
- ECCC SWOB observations;
- OpenWeather conditions or forecasts;
- TransLink integration or transit routing;
- OpenRouter inference;
- AI-generated journey briefings;
- live congestion detection;
- traffic-aware route optimization;
- traffic-adjusted duration estimates;
- route-by-route telemetry relevance analysis;
- route timeline or segment intelligence beyond provider route geometry;
- navigation guidance or turn-by-turn directions;
- automatic route selection based on traffic or AI judgment;
- database persistence or saved journeys;
- user accounts or authentication;
- background routing jobs;
- continuous location tracking;
- mobile-specific navigation functionality;
- additional routing providers;
- new major frontend frameworks;
- unrelated infrastructure.

Do not fabricate alternate routes, travel times, incidents, or conditions.

Do not implement the intelligence-gathering workflow merely because a route has been selected.

Do not redesign the approved application architecture without authorization.

---

## 7. Verification Requirements

Each bounded assignment must perform the checks relevant to its authorized scope.

### Backend Verification

Verify:

- FastAPI imports and starts.
- Existing `/api/health` behavior remains available.
- ORS requests use the approved driving profile.
- Canonical coordinates are converted correctly.
- Routing API accepts valid canonical origin/destination inputs.
- Invalid input is rejected.
- Destinations outside Vancouver are rejected.
- Valid ORS responses normalize correctly.
- Route identifiers are distinct.
- Route geometry is valid and preserves longitude/latitude ordering.
- Distance and duration values use correct units.
- Fewer-than-requested alternatives are supported.
- Legitimate no-route responses are handled.
- Provider authentication, timeout, and service errors are handled safely.
- Existing geocoding and destination-validation tests remain passing.
- Ruff and relevant pytest checks pass.

Use mocked provider responses for deterministic automated testing.

Do not make the default test suite depend on live ORS access.

### Targeted Live Integration Verification

Use a small number of authenticated ORS requests.

Suggested representative journeys:

1. Richmond → Downtown Vancouver.
2. Burnaby → Downtown Vancouver.
3. A shorter journey within Vancouver.

For each observed response, verify:

- successful ORS authentication;
- valid normalized candidates;
- accurate alternative count;
- distinct candidate identifiers;
- usable route geometry;
- actual distance and duration values;
- safe backend API representation.

Do not require exactly three alternatives.

Do not fabricate live results or repeat calls solely to obtain a preferred candidate count.

Record provider-specific limitations.

### Frontend Verification

Verify:

- TypeScript checks pass.
- Production build succeeds.
- Vite starts.
- Find Routes is enabled only for accepted canonical locations.
- Routing requests use the existing `/api` proxy.
- Loading and failure states are visible and recoverable.
- Real route candidates appear.
- Alternative route summaries are readable.
- The user can explicitly select a route.
- Selection changes update canonical selected-route state.
- Changing origin/destination invalidates old route results.
- Out-of-order routing responses cannot restore stale candidates.
- Analyze Journey remains inactive.

### Map Verification

Verify:

- the MapTiler basemap renders;
- actual route geometries display correctly;
- route alternatives are distinguishable;
- the selected route is highlighted;
- candidate changes update route layers;
- route invalidation removes stale geometry;
- map viewport fits relevant route geometry appropriately;
- existing pan and zoom remain functional;
- attribution remains visible;
- resizing does not break map dimensions;
- no major overlapping or clipped interface regions appear.

A successful ORS response alone does not prove that route rendering works.

Actual browser verification must be recorded separately.

### End-to-End Verification

Test representative flows.

**Valid journey**

Select Richmond as origin and Downtown Vancouver as destination, retrieve routes, and explicitly select a candidate.

**Alternative selection**

Select one route, then another, and confirm the selected state and map emphasis change.

**Location edit**

Change either input after generating routes and verify old routes disappear.

**Pending request invalidation**

Begin route retrieval, then edit a location before the request completes. Verify the stale response is ignored.

**Single candidate**

Verify a one-route response remains usable and selectable.

**No route**

Verify an empty legitimate result produces no-route feedback without fabricated geometry.

**Provider failure**

Verify an upstream failure does not crash the interface or preserve stale selected-route state.

**Regression**

Verify Phase 2 autocomplete, destination validation, backend health, map interactions, and desktop layout remain functional.

### Security and Repository Verification

- Confirm `.env` remains ignored.
- Confirm the ORS credential stays backend-only.
- Ensure backend-only provider credentials are absent from frontend assets.
- Confirm no secret values enter source files, fixtures, or logs.
- Run `git diff --check`.
- Review final Git status.
- Confirm changed files remain within the authorized assignment boundary.
- Check that no unrequested dependencies or runtime services were added.

### Reporting Standard

Classify checks as:

- **Passed** — performed successfully.
- **Failed** — performed but did not satisfy expectations.
- **Not run** — not executed, with a reason.

Do not report browser interactions or live provider results as successful unless they actually occurred.

Preserve the distinction between mocked tests, live observations, and historical Phase 0 evidence.

---

## 8. Phase 3 Acceptance Criteria

Phase 3 is ready for human acceptance when:

- [ ] A backend ORS driving-route adapter exists.
- [ ] The adapter uses the approved `driving-car` profile.
- [ ] Real authenticated ORS routing works.
- [ ] Canonical origin and destination coordinates are handled correctly.
- [ ] Invalid or unsupported destinations are rejected.
- [ ] Route results normalize into the approved `RouteCandidate` contract.
- [ ] Route geometry remains valid and MapLibre-compatible.
- [ ] Provider distance and duration are preserved with correct units.
- [ ] Route-candidate identities distinguish alternatives.
- [ ] A focused FastAPI routing endpoint exists.
- [ ] Multiple driving alternatives are supported.
- [ ] Fewer-than-requested alternatives are handled.
- [ ] Single-route results are supported.
- [ ] Legitimate no-route results are handled.
- [ ] Malformed routes and provider failures are handled safely.
- [ ] Find Routes is available only when valid canonical origin and destination selections exist.
- [ ] Users can explicitly request driving routes.
- [ ] Actual returned alternatives appear on MapLibre.
- [ ] Alternative routes are visually distinguishable.
- [ ] Available alternatives have factual distance and duration summaries.
- [ ] Users can explicitly select a route.
- [ ] The selected route is visually identifiable.
- [ ] Canonical selected-route state is retained for later phases.
- [ ] No route is silently selected as the intended journey.
- [ ] Changing origin/destination invalidates old routes.
- [ ] Stale routing responses cannot restore obsolete routes.
- [ ] Route selection can be changed without requesting a new journey.
- [ ] Appropriate routing loading, error, and no-route states are displayed.
- [ ] Existing MapLibre pan, zoom, attribution, and resizing remain functional.
- [ ] The fixed approximately 65/35 desktop layout remains usable.
- [ ] Existing location autocomplete and destination validation remain functional.
- [ ] Drive remains the active mode without premature transit behavior.
- [ ] Analyze Journey remains inactive.
- [ ] No fabricated traffic, telemetry, or AI findings are presented.
- [ ] Relevant backend pytest and Ruff checks pass.
- [ ] Frontend TypeScript checks and production build pass.
- [ ] Representative end-to-end route selection is manually verified.
- [ ] No backend-only API credentials are exposed in the frontend.
- [ ] `PROJECT_STATE.md` records actual verification, limitations, and acceptance readiness.
- [ ] Codex provides the required completion report and confirms no Git staging, commit, or push occurred.

Passing these checks makes Phase 3 eligible for human review.

It does not constitute automatic acceptance.

---

## 9. Blockers and Escalation

Stop affected work and report when:

- ORS credentials are missing or rejected after ordinary troubleshooting;
- actual ORS responses materially contradict approved Phase 0 assumptions;
- the approved route-candidate contract cannot represent real provider results;
- the required geometry representation is unresolved or incompatible with MapLibre;
- the existing destination-validation contract would need to be weakened;
- route selection cannot be represented without a material architectural change;
- a major new dependency or infrastructure component is required;
- existing Phase 2 location state cannot be preserved safely;
- map rendering or lifecycle behavior cannot be maintained;
- completion requires unauthorized later-phase functionality;
- destructive or unrelated repository changes appear necessary;
- an important product policy must be invented to satisfy the acceptance criteria.

For each material blocker, report:

- observed issue;
- affected requirement;
- available evidence;
- reasonable options, where apparent.

Continue independent in-scope implementation work when safe.

Routine ORS parsing, error handling, candidate labeling, React state organization, MapLibre layer styling, and focused test corrections may be resolved autonomously.

Do not silently replace approved architectural contracts.

Do not weaken deterministic geographic validation for convenience.

---

## 10. Phase Completion and Handoff

After each bounded assignment:

- Run relevant verification.
- Update `PROJECT_STATE.md` with factual implementation progress.
- Record actual route API behavior and provider observations.
- Preserve completed functionality.
- Report files created or modified.
- Identify failures, limitations, and material decisions.
- Provide the standard completion report required by `AGENTS.md`.
- Do not claim the entire phase is complete until all applicable acceptance criteria have been assessed.

Phase 3 is accepted only after human review of:

- real driving-route generation;
- alternate route presentation;
- explicit user route selection;
- selected-route state consistency;
- invalidation after location changes;
- routing failure and no-route behavior;
- MapLibre route visualization;
- existing map and journey-input regression;
- relevant tests and production build results;
- material limitations and deviations.

Git checkpoints remain human-controlled.

Codex must not stage, commit, push, amend, merge, rebase, tag, or rewrite Git history.

After acceptance:

1. Record human acceptance in `PROJECT_STATE.md`.
2. Perform the human-controlled Git checkpoint.
3. Prepare the next phase's `BUILD_PLAN.md`.
4. Do not begin subsequent implementation until separately authorized.

---

## 11. Next Phase

**Phase 4 — See `docs/implementation-plan.md` for the authoritative phase name and scope.**

After Phase 3 acceptance, the selected driving-route geometry and associated canonical journey locations become available to subsequent RouteLens data-integration and intelligence work.

The selected route will provide geographic context for determining which real-world information is relevant to a journey.

The exact Phase 4 requirements must be taken from the approved implementation roadmap when preparing its build plan.

Do not assume that all telemetry sources or AI features belong to Phase 4.

**Phase 4 work is not authorized by this document.**
