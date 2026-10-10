# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 2 — Journey Input + Geocoding
**Status:** Planned — authorized for implementation; not yet verified
**Source:** `docs/implementation-plan.md`, Phase 2
**Previous phase:** Phase 1 — Application Shell + Map, accepted by the human developer on 2026-10-10

### Objective

Enable users to search for, select, and validate real journey origin and destination locations using MapTiler geocoding/autocomplete.

Phase 2 must deliver:

- working MapTiler location search through the FastAPI backend;
- normalized location results consistent with the approved `Location` model;
- functional origin and destination autocomplete controls;
- deterministic validation of City of Vancouver destinations;
- frontend state that preserves selected canonical locations;
- clear validation, loading, empty-result, and failure states;
- successful end-to-end verification using real representative locations.

The application should support this interaction:

**Search origin → select location → search destination → select location → validate destination → retain selected journey inputs.**

The origin must be within the supported Metro Vancouver / Lower Mainland geographic scope.

The destination must be within the **City of Vancouver municipal boundary**.

Phase 2 establishes validated journey inputs. It does not calculate routes, choose route alternatives, or analyze journey conditions.

---

## 2. Execution Scope

This document defines the complete Phase 2 acceptance boundary.

Phase 2 may be completed through smaller bounded Codex assignments. Each assignment receives a separate implementation prompt defining its immediate objective, expected artifacts, and verification.

- Do not interpret this document as authorization to implement all Phase 2 work in one assignment.
- Implement only the work explicitly authorized by the current assignment prompt.
- Preserve the completed Phase 1 application and its established behavior.
- Update `PROJECT_STATE.md` with factual implementation progress.
- Do not begin Phase 3 until Phase 2 has been accepted by the human developer.

### Planned Assignments

**Assignment 2A — Geocoding and Location Validation**

Implement the backend MapTiler geocoding capability, approved location normalization, deterministic geographic validation, and appropriate automated tests.

**Assignment 2B — Journey Input Interface**

Replace the inactive origin/destination placeholders with working autocomplete components and canonical location-selection state.

Preserve the existing application shell and inactive later-phase actions.

**Assignment 2C — End-to-End Journey Input Integration**

Complete and verify the frontend/backend interaction, destination-validation UX, selection persistence, error handling, and full Phase 2 acceptance assessment.

Assignment boundaries are organizational, not independent architecture layers.

Avoid creating unnecessary abstraction solely to accommodate separate assignments.

Each assignment should produce directly verifiable behavior appropriate to its scope.

---

## 3. Established Implementation and Integration Baseline

### 3.1 Accepted Phase 1 Foundation

Phase 1 established:

- minimal FastAPI backend;
- working `GET /api/health`;
- React/Vite/TypeScript frontend;
- Tailwind-based dark desktop shell;
- functional frontend/backend communication through Vite's `/api` proxy;
- interactive MapLibre map using MapTiler's `streets-v4-dark` style;
- fixed approximately 65/35 map-to-intelligence-panel desktop layout;
- top journey-controls region;
- right-side intelligence placeholders;
- frontend loading and failure-state conventions;
- basic backend tests, Ruff checks, and frontend build verification.

Phase 2 must extend this foundation, not rebuild it.

Preserve existing map initialization, worker configuration, resizing, attribution, and browser-visible MapTiler configuration.

The local VMware/Chromium WebGL compatibility issue was resolved through development-environment configuration and is documented in `PROJECT_STATE.md`.

Do not redesign the mapping stack or graphics configuration.

### 3.2 Phase 0 MapTiler Readiness

Phase 0C established:

- authenticated MapTiler geocoding/autocomplete access;
- representative Metro Vancouver search results;
- GeoJSON response structure;
- longitude/latitude coordinate ordering;
- useful administrative and contextual metadata;
- potentially ambiguous broad search results.

The existing evidence is recorded in:

- `docs/integration-notes/geographic-services-readiness.md`
- `fixtures/maptiler/`
- `PROJECT_STATE.md`

Review representative fixtures and documented findings before implementing the geocoding adapter.

Do not repeat broad provider discovery.

Targeted live testing of the actual new backend integration is authorized and required where appropriate.

### 3.3 Existing Configuration

The ignored project-root `.env` contains the configured MapTiler API key.

Phase 1 selectively exposed a browser-usable MapTiler key for basemap rendering.

For Phase 2:

- Preserve the existing basemap configuration.
- Access backend geocoding credentials through server-side configuration.
- Do not expose unrelated backend-only provider credentials.
- Do not duplicate actual credential values in tracked source files.
- Preserve `.env.example` and `.gitignore` behavior.

Do not introduce a general secrets-management system.

---

## 4. Required Phase 2 Workstreams

### 4.1 Backend — MapTiler Geocoding Integration

Implement a narrow backend integration with MapTiler's approved geocoding/autocomplete service.

Required behavior:

- Accept a user-provided search query.
- Call the appropriate MapTiler endpoint using configured credentials.
- Receive and validate the provider response.
- Extract relevant location candidates.
- Normalize candidates into the approved application location representation.
- Return structured results to the frontend.
- Handle empty results and upstream failures without crashing.
- Avoid exposing MapTiler credentials in responses or error messages.

Use asynchronous HTTP where consistent with the approved FastAPI/httpx architecture.

The backend should own location normalization and geographic validity rules.

### Search behavior

Implement practical search behavior suitable for:

- Metro Vancouver / Lower Mainland origins;
- City of Vancouver destinations.

Use relevant MapTiler query parameters and geographic context where helpful.

However:

- Do not assume bounding-box relevance means a result is geographically valid.
- Do not assume every returned result belongs to the City of Vancouver.
- Do not silently transform ambiguous provider results into certain locations.
- Do not fabricate autocomplete suggestions.

Define search limits and reasonable timeout behavior.

Avoid premature provider-independent geocoding frameworks or multi-provider fallback systems.

### Backend API

Expose a small, predictable application API for location search.

Use the API organization established in the approved technical design, where specified.

The bounded implementation prompt may establish exact endpoint paths and request/response details consistent with that design.

Prefer a simple query-oriented contract over multiple speculative APIs.

Do not expose raw MapTiler response bodies as the application's permanent public contract.

---

### 4.2 Location Normalization

Normalize geocoding results into the approved `Location` representation from `APP_SPEC.md` and `docs/technical-design.md`.

Preserve the location attributes actually required by the approved model.

These may include, as defined by the authoritative contract:

- canonical provider identifier;
- human-readable place label;
- geographic coordinates;
- relevant administrative or place context;
- source/provider identification.

Do not invent required fields without consulting the approved location model.

### Coordinate handling

MapTiler GeoJSON coordinates use:

`[longitude, latitude]`

Preserve correct coordinate ordering throughout backend responses and frontend state.

Ensure coordinates are numerically valid.

Do not silently reverse latitude and longitude.

### Data integrity

- Preserve meaningful source information.
- Distinguish absent provider fields from known values.
- Do not invent place details.
- Do not classify a location as valid solely because a display string appears plausible.
- Avoid committing unnecessary raw provider fields to long-lived application contracts.

Implement normalization tests using representative sanitized fixtures.

---

### 4.3 Destination Validation — City of Vancouver

Implement deterministic validation that selected destinations are inside the **City of Vancouver municipal boundary**.

This requirement is fundamental to the RouteLens MVP scope.

### Requirements

- Validate selected destinations using their canonical geographic coordinates.
- Follow the geographic validation approach defined in the authoritative technical design.
- Use an authoritative municipal boundary representation where that design requires one.
- Distinguish the City of Vancouver from Metro Vancouver and neighboring municipalities.
- Reject destinations outside the supported city boundary.
- Return a clear, machine-readable validation outcome.
- Provide an understandable rejection reason for frontend presentation.

Do not rely exclusively on:

- the word "Vancouver" in a place label;
- postal address formatting;
- broad administrative search hints;
- MapTiler search ranking;
- a generic rectangular approximation of the city.

### Boundary behavior

Handle boundary cases deterministically.

Tests should include representative locations inside Vancouver and outside Vancouver, including nearby municipalities.

Examples of relevant comparisons include:

- Downtown Vancouver — expected valid.
- Richmond — expected invalid.
- Burnaby — expected invalid.
- North Vancouver — expected invalid.

Use actual coordinates and the approved boundary model in tests.

Boundary-edge behavior should be explicitly defined rather than left to accidental implementation details.

If the necessary authoritative boundary dataset or exact inclusion rule is not established by the existing design, raise that material dependency for human review rather than silently inventing a replacement.

No LLM should participate in destination validation.

---

### 4.4 Origin Geographic Scope

Support origin selection within the approved Metro Vancouver / Lower Mainland geographic scope.

The origin does not need to be inside the City of Vancouver.

Requirements:

- Search should return useful candidate locations from the supported origin region.
- Origin and destination must remain distinct application concepts.
- Do not incorrectly apply the destination-only city boundary rule to origins.
- Follow any explicit origin-scope validation rules already defined in `APP_SPEC.md` or `docs/technical-design.md`.
- Avoid making the search globally unrestricted merely because MapTiler can return worldwide locations.

If the approved geographic scope does not provide an exact enforceable origin boundary, preserve its documented interpretation and avoid inventing a new municipal or regional polygon requirement.

Clearly distinguish search-context biasing from deterministic acceptance validation.

---

### 4.5 Frontend — Location Autocomplete

Turn the existing origin and destination placeholders into actual search controls.

Required behavior:

- User can type an origin query.
- Matching real location suggestions appear.
- User can select a suggestion.
- User can type a destination query.
- Matching real location suggestions appear.
- User can select a suggestion.
- Selected places are retained as canonical location objects.
- Appropriate status is displayed while requests are in progress.
- Empty results are handled clearly.
- Upstream errors are understandable and nonfatal.

### Interaction requirements

- Debounce input to avoid excessive provider requests.
- Avoid issuing meaningful search requests for empty or trivially short input.
- Prevent stale or out-of-order responses from replacing newer search results.
- Permit keyboard interaction appropriate for a basic accessible autocomplete.
- Clearly identify the active suggestion and selected result.
- Maintain reasonable focus and selection behavior.
- Distinguish free-typed text from a confirmed location selection.

Typing a place name is not equivalent to selecting a canonical location.

If the user changes the text after selecting a location, invalidate the stale selection appropriately.

Do not silently retain coordinates that no longer correspond to the visible input.

### Component scope

Prefer focused reusable components where justified, such as an `AddressAutocomplete` component.

Avoid introducing large form libraries, UI frameworks, global state managers, or generalized search infrastructure.

Use the existing React/TypeScript/Tailwind patterns.

---

### 4.6 Frontend — Journey Input State

Maintain selected origin and destination locations in appropriate React application state.

Required behavior:

- Origin selection persists during normal component interaction.
- Destination selection persists during normal component interaction.
- Changing one field does not unintentionally erase the other.
- Editing a previously selected location invalidates only the affected selection when appropriate.
- Selected locations remain available for eventual Phase 3 route requests.
- Validation status is represented separately from display labels.

For this phase, **persistence means frontend application state across normal UI interactions**, not database persistence or automatic survival across browser reloads.

Do not introduce browser storage, database storage, user accounts, or saved journeys.

Do not implement the complete `Trip`, `RouteCandidate`, or `SelectedRoute` workflow yet.

---

### 4.7 Travel Mode Controls

Preserve the approved Drive / Transit product direction.

For Phase 2:

- Drive is the primary active mode.
- Transit may remain visible but does not require service or direction selection.
- Do not implement TransLink integration.
- Do not imply that functional transit journey planning is available.

Use honest UI state and labels.

If the approved technical design specifies a more precise initial mode-control behavior, follow it rather than inventing new product functionality.

Avoid implementing mode-specific route calculation.

---

### 4.8 Destination Validation UX

A destination outside the City of Vancouver must produce a clear user-facing rejection.

Requirements:

- Explain that destinations must be within the City of Vancouver.
- Keep the error close to the destination control.
- Do not misrepresent an invalid location as accepted.
- Preserve the user's ability to search again.
- Distinguish geographic rejection from network failure.
- Avoid confusing an empty search result with an invalid selected location.

A geographically invalid destination must not become the application's accepted destination selection.

The frontend should consume backend validation outcomes rather than independently creating contradictory validation rules.

---

### 4.9 Journey Action and Phase 3 Handoff

Phase 2 prepares the location inputs for later route calculation.

Do not implement route calculation yet.

The user should be able to see when valid location selections have been established.

The Analyze Journey action may remain inactive or explicitly indicate that routing/analysis is forthcoming.

Do not:

- call openrouteservice;
- draw driving-route candidates;
- select routes;
- submit a journey for analysis;
- show fabricated results.

Keep the selected location state suitable for later Phase 3 use.

Do not prematurely introduce a complete journey orchestration layer.

---

### 4.10 Existing Map and Intelligence Panel

Preserve the Phase 1 visual foundation.

Requirements:

- Keep the MapLibre Vancouver basemap functional.
- Preserve navigation, zoom, attribution, lifecycle cleanup, and responsive sizing.
- Preserve the fixed approximately 65/35 desktop layout.
- Preserve the right-side intelligence panel and its honest empty states.
- Preserve backend connectivity status.
- Integrate real location controls without materially degrading the interface.

Do not redesign the entire application shell to accommodate autocomplete.

Small layout adjustments are permitted where required for usable suggestions and validation messages.

Do not implement route drawing, real telemetry markers, or intelligence summaries.

---

## 5. Expected Scope and Artifacts

Phase 2 may create or modify:

- `backend/` — MapTiler geocoding adapter, location normalization, validation, API routes, and relevant tests;
- `frontend/src/` — autocomplete components, journey-input state, API interaction, and limited layout integration;
- appropriate geographic boundary data or validation helpers where required by the approved design;
- sanitized test fixtures where needed;
- dependency specifications and lockfiles for justified additions;
- `README.md`, if local setup or configuration instructions change;
- `PROJECT_STATE.md`.

The expected structure should remain consistent with `docs/technical-design.md`.

These are anticipated areas, not a strict filesystem allowlist.

Create only the modules necessary for Phase 2 functionality.

Do not pre-create Phase 3 routing services, telemetry models, database infrastructure, or future feature directories.

---

## 6. Non-Goals

Phase 2 must not implement:

- openrouteservice routing;
- route alternatives or route selection;
- route overlays or route optimization;
- journey condition analysis;
- Road Ahead or DriveBC Open511 adapters;
- weather integration;
- camera ingestion or inference;
- OpenRouter briefing generation;
- TransLink data ingestion or transit-service matching;
- route timeline calculations;
- database persistence or saved journeys;
- browser location permissions or automatic current-location selection;
- authentication or user accounts;
- realtime monitoring or push notifications;
- new basemap providers;
- redesign of the established desktop shell;
- full mobile-specific product functionality;
- speculative generic location-provider frameworks.

Do not generate fabricated suggestions or locations to conceal provider failures.

Do not replace deterministic geographic validation with AI inference.

Do not introduce infrastructure or additional runtime services without a demonstrated Phase 2 need.

---

## 7. Verification Requirements

Each bounded assignment must perform the checks relevant to its scope.

### Backend Verification

Verify:

- FastAPI imports and starts.
- Existing `/api/health` behavior remains functional.
- Geocoding API returns normalized results for representative searches.
- Location normalization preserves expected fields and coordinate ordering.
- Invalid or incomplete upstream responses are handled safely.
- Missing credentials and provider errors produce appropriate failures.
- City of Vancouver destination validation behaves deterministically.
- Valid and invalid representative destinations are covered by tests.
- Ruff and relevant pytest checks pass.

Prefer deterministic unit tests and mocked external HTTP requests for normal regression testing.

Targeted authenticated live requests may be used to validate new integration behavior, but the automated test suite should not require live network access or consume provider quotas.

### Frontend Verification

Verify:

- TypeScript checks pass.
- Production frontend build succeeds.
- Vite starts.
- Real suggestions appear for representative user queries.
- Selection creates canonical frontend location state.
- Edits after selection invalidate outdated state.
- Loading, empty-result, and network-failure states work.
- Stale autocomplete responses do not overwrite newer searches.
- Keyboard selection and basic accessibility behavior are usable.
- Invalid destinations display understandable validation feedback.

### End-to-End Verification

Test representative real user flows.

Examples:

1. Richmond origin → Downtown Vancouver destination: accepted location selections.
2. Burnaby origin → Vancouver destination: accepted location selections.
3. Vancouver origin → Richmond destination: destination rejected.
4. Vancouver origin → Burnaby destination: destination rejected.
5. Selected origin edited afterward: stale origin selection invalidated.
6. Geocoding unavailable: clear error without application crash.

Use actual geocoding results for live user-flow verification.

Do not manufacture successful external-service behavior.

### Regression Verification

Confirm:

- MapLibre basemap still renders.
- Pan and zoom still work.
- Attribution remains visible.
- Fixed desktop layout remains usable.
- Right-side intelligence placeholders remain honest.
- Backend health indicator still works.
- No unrelated telemetry or AI calls were introduced.

### Repository Verification

- Check `.env` remains ignored.
- Ensure real credentials are absent from tracked fixtures and source.
- Confirm backend-only secrets are not leaked into browser assets.
- Run `git diff --check`.
- Inspect final Git status.
- Confirm expected dependency changes only.

### Reporting Standard

Classify checks as:

- **Passed** — performed successfully.
- **Failed** — performed but did not satisfy expectations.
- **Not run** — not performed, with a reason.

Do not report browser or live API validation as passed unless actually performed.

---

## 8. Phase 2 Acceptance Criteria

Phase 2 is ready for human acceptance when:

- [ ] A backend MapTiler geocoding integration exists.
- [ ] Real authenticated location search works.
- [ ] Search results are normalized into the approved `Location` contract.
- [ ] Canonical coordinates preserve longitude/latitude ordering.
- [ ] Geocoding errors, missing fields, and empty results are handled.
- [ ] Destination geographic validation is deterministic.
- [ ] Valid City of Vancouver destinations are accepted.
- [ ] Nearby non-Vancouver destinations are rejected.
- [ ] Destination boundary tests pass.
- [ ] Origin locations within the approved region can be selected.
- [ ] Origin and destination autocomplete work in the frontend.
- [ ] Users can select actual geocoding suggestions.
- [ ] Selected locations persist in frontend state during normal interaction.
- [ ] Editing a selected field invalidates its outdated selection.
- [ ] Destination validation feedback is clear.
- [ ] Loading, empty-result, and provider-failure states are understandable.
- [ ] Stale autocomplete responses do not overwrite newer results.
- [ ] Basic keyboard interaction works.
- [ ] Drive remains the primary active mode without premature transit functionality.
- [ ] The app does not calculate or display routes.
- [ ] Existing MapLibre and FastAPI functionality remains working.
- [ ] The fixed 65/35 desktop layout remains usable.
- [ ] No fabricated telemetry or analysis appears.
- [ ] Relevant backend pytest and Ruff checks pass.
- [ ] TypeScript checks and frontend production build pass.
- [ ] Representative end-to-end searches are manually verified.
- [ ] No backend-only credentials are exposed in the frontend.
- [ ] `PROJECT_STATE.md` accurately records results, limitations, and outstanding work.
- [ ] Codex provides the required completion report and confirms no Git staging, commit, or push was performed.

Passing these checks makes Phase 2 eligible for human review.

It does not constitute automatic acceptance.

---

## 9. Blockers and Escalation

Stop affected work and report when:

- MapTiler geocoding credentials are unavailable or rejected;
- the approved location contract cannot represent actual provider results without material changes;
- provider behavior materially contradicts Phase 0 findings;
- the authoritative City of Vancouver boundary or agreed validation approach cannot be established;
- an exact geographic scope decision must be made that is not supported by the approved planning documents;
- reliable destination validation requires an unapproved approximation;
- a material backend API or architectural change becomes necessary;
- new infrastructure or major dependencies beyond the approved stack are required;
- existing map or shell functionality cannot be preserved;
- completion requires unauthorized Phase 3 behavior;
- destructive or unrelated repository operations appear necessary.

For each blocker, report:

- observed issue;
- affected requirement;
- available evidence;
- reasonable options, where apparent.

Continue independent in-scope work where safe.

Routine parser adjustments, component organization, HTTP error handling, and small test corrections may be resolved autonomously within the assignment.

Do not silently redesign the location model, geographic scope, or product workflow.

---

## 10. Phase Completion and Handoff

After each bounded assignment:

- Run applicable verification.
- Update `PROJECT_STATE.md` with factual implementation progress.
- Record actual service behavior and meaningful discoveries.
- Preserve completed functionality.
- Report relevant files and dependency changes.
- Identify failures, limitations, and deviations.
- Provide the standard completion report required by `AGENTS.md`.
- Do not claim the complete phase has been accepted before human review.

Phase 2 is accepted only after human review of:

- actual origin/destination autocomplete;
- valid location selection;
- City of Vancouver boundary enforcement;
- representative accepted and rejected destinations;
- state management after editing selections;
- provider failure behavior;
- existing map functionality and desktop layout;
- relevant tests and build results.

Git checkpoints remain human-controlled.

Codex must not stage, commit, push, amend, merge, rebase, tag, or rewrite Git history.

---

## 11. Next Phase

**Phase 3 — Drive Route Candidates + Selection**

After Phase 2 acceptance, Phase 3 will use valid selected locations to:

- request driving routes from openrouteservice;
- normalize route candidates;
- display route alternatives on the map;
- allow the user to select the route most closely matching their intended journey;
- preserve selected-route state for later journey intelligence.

The route-selection workflow will not imply that RouteLens replaces Google Maps or independently determines the optimal route.

Phase 3 work is not authorized by this document.
