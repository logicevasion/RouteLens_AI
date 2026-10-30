# RouteLens AI — Active Build Plan

## SDD authority and workflow

- `AGENTS.md` and `APP_SPEC.md` are the governing operating and product documents.
This file defines the currently selected bounded assignment. Planning approval does not authorize implementation; each implementation requires a separate human-approved prompt.
- `PROJECT_STATE.md` records repository implementation reality, accepted status, limitations, and current verification.
- Historical decisions and detailed evidence remain available in the exact pre-QAR-1 archives and accepted integration notes linked below.
- Codex may implement an assignment only after separate human authorization. Human developers control staging, commits, pushes, and all Git history.
- Future accepted assignments should be summarized in `PROJECT_STATE.md`, not appended as full implementation transcripts.

## Next prepared assignment: Alpha-UX-1 — Stage transitions and primary summary

**Status:** Prepared for human review only. This documentation task authorizes no implementation. A separate human implementation prompt is required for Alpha-UX-1; Alpha-UX-2 is not included in that authorization.

**Objective:** Implement Stage 1/Stage 2 and the deterministic primary summary specified in [Alpha UX v1](docs/alpha-ux-spec.md).

### Scope and expected components

- `frontend/src/App.tsx`: retain header/controls and existing route selection; add presentation stages, Stage 1 guidance and approximately 65/35 map/route layout; remove the pre-analysis AI placeholder.
- `frontend/src/DestinationCameraPanel.tsx`: one-view navigation across the actual returned usable views with complete provenance and failure states.
- `frontend/src/DestinationWeatherPanel.tsx`, existing weather helpers/types, and a small summary component/helper if needed: current weather, timestamp-based next-hour subset, nearest eligible ECCC station, and qualified Road Ahead overlap count from existing normalized data.
- `frontend/src/styles.css` and relevant tests under `frontend/tests/`: full-width responsive summary, approximately equal desktop camera/weather columns and deterministic regression coverage. Expected paths are guidance, not a refactor mandate.
- Retain existing supporting information below the new summary during this intermediate slice. Do not implement Alpha-UX-2's final map/events arrangement, Experimental placement, or collapse organization yet.

### Acceptance criteria

1. Stage 1 retains header/controls, guidance before routes, and explicit Choose Your Route UI after routes. Route candidates, selection and highlighting, validation, and errors remain functional.
2. Find Routes returns immediately from Stage 2 to Stage 1; valid Analyze enters Stage 2 immediately and brings the section beginning into view once, without moving keyboard focus. Later result updates do not repeat the viewport adjustment or disrupt user scrolling. Input/route invalidation suppresses prior results and cancels matching work. Invalid Analyze creates no attempt.
3. Summary spans available width; camera and weather are approximately equal columns on desktop and stack readably. Camera and deterministic evidence render independently of AI loading/failure; no extra data fetch or inference is introduced. Inputs remain editable and Find Routes remains available during analysis. Repeated Analyze clicks during the active analysis do not create duplicate logical attempts; existing loading, disabled, cancellation and validation behavior is preserved. Camera navigation and map interaction remain usable while AI is pending.
4. Camera navigation handles zero, one, and more than four views, partial/stale results, changed results, and image failure. Only one image is displayed; provenance, official link and timestamps remain accessible. Navigation does not change inference image selection or dispatch.
5. Current weather preserves all requested available fields and unknowns. The next-hour selection starts from current analysis time, excludes elapsed forecast timestamps, uses only actual upcoming timestamps, retains gaps, and preserves provider evaluation/freshness metadata; the complete series remains accessible. No data sent to the briefing is changed. Select one closest non-stale useful ECCC observation using normalized flags/measurements; preserve measured/source distinctions and cache warnings. No eligible station yields an explicit empty state.
6. Road count includes only Road Ahead direct overlaps and qualifies partial/stale/unavailable/zero data. No all-clear wording or DriveBC Point/nearby inflation.
7. USER-001 UUID behavior, USER-002 inclusive cutoff/settlement behavior, existing deadlines, cancellation, stale guards, and at most one briefing dispatch per attempt remain unchanged. Display subsets never alter briefing evidence.

### Verification and human approval boundary

Run focused fixture-based stage/summary/camera/weather regressions, plus existing camera, briefing, and evidence lifecycle tests. Exercise deterministic completion orders (camera before/after analysis, AI pending/failing), Find Routes during pending work, invalidation, missing intervals/fields, station eligibility and ties, road status/count variants, and no dispatch from navigation. Run the full frontend suite (`cd frontend && npm test`), production build (`npm run build`), and `git diff --check`. Use mocked transports with no external requests or paid inference. Backend checks are not required when backend files remain unchanged.

Use mocked browser/manual review where available for immediate stage transitions, desktop proportions, keyboard camera navigation, responsive stacking, and retained map rendering/highlighting; report unavailable browser checks as Not run. Human review and explicit acceptance are required before the slice is accepted; passing checks do not authorize Alpha-UX-2 or Git history operations. Update `PROJECT_STATE.md` factually after implementation.

## Separately authorized future assignment: Alpha-UX-2 — Supporting layout and disclosures

**Status:** Future slice; requires its own human-approved implementation prompt after Alpha-UX-1 review. Not authorized by this preparation or by Alpha-UX-1 implementation approval.

**Objective:** Complete Stage 2's map/construction arrangement, Experimental briefing placement, and collapsible supporting data per [Alpha UX v1](docs/alpha-ux-spec.md).

### Scope and expected components

`App.tsx`, `VancouverMap.tsx` integration, `RoadAheadPanel.tsx`, `DestinationWeatherPanel.tsx`, briefing presentation extracted only as necessary, `styles.css`, and focused frontend tests. Reorganize existing data and callbacks without changing map relevance or inference orchestration.

### Acceptance criteria

1. Below the primary summary, the map sits beside route-intersecting Road Ahead events on desktop and stacks readably at narrower widths. Route/construction emphasis, source-scoped selection, event-to-map focus, existing overlays, and camera markers remain functional.
2. AI Journey Briefing appears below map/construction, labelled Experimental, with existing content and independent loading/error/insufficient-evidence states. Its position or mount lifecycle causes no new dispatch.
3. Complete three-hour forecast, additional returned ECCC observations, nearby construction, detailed statuses and secondary context are accessible in keyboard-operable sections collapsed by default. Primary source warnings remain visible. Preserve timestamps, units, attribution, unknowns, and event interactions when expanded.
4. Existing DriveBC findings remain accessible and distinct from Road Ahead; regional/Point context retains its semantics. Empty DriveBC and deferred Transit placeholders consume no large primary area; transit stays deferred.
5. Alpha-UX-1 transitions, primary summary and all accepted UUID/timing/cancellation/one-dispatch behavior remain intact; no content is lost through reorganization.

### Verification and human approval boundary

Run focused map/event and disclosure interaction regressions with deterministic fixtures, retained camera/weather/briefing/evidence tests, the full frontend suite, production build and `git diff --check`. Verify selected event focus and highlighting after layout resize, collapse/expand, repeated analysis and return to Stage 1. Use mocked browser/manual checks for section order, readable scrolling/stacking, keyboard disclosure controls and map rendering. No external requests or paid inference. Report checks precisely; human visual review and explicit acceptance remain required. No automatic next phase or Git operation is authorized.

## Shared exclusions

Both slices are frontend presentation work only: no backend/API/shared contract changes, new sources, additional LLM inference, model/prompt/provider/budget changes, dependencies, infrastructure, authentication, usage tracking, deployment, unrelated fixes or refactoring. Preserve QAR-1 budget controls and QAR-2 offline isolation. Material conflicts require escalation under `AGENTS.md`.

## Completed correction assignment

QAR-1 is accepted at `d1bbcd4`. Its prior active plan (only relative links adjusted for the archive location), including thresholds, persisted-state semantics and verification criteria, is preserved in [the pre-Alpha UX archive](docs/archive/BUILD_PLAN_pre-AlphaUX.md). QAR-2 (`45015aa`), USER-001 (`b5dd20b`) and USER-002 (`40df498`) are also human accepted. These checkpoints were confirmed in local Git history; acceptance is supplied by the human task prompt.

## Accepted baseline: Phases 0–10

The human-accepted datathon MVP is driving-only and serves journeys into Vancouver. Phases 0–3 established the SDD foundation, application shell, Vancouver map, canonical geocoding and destination validation, ORS route alternatives, and explicit route selection. Phases 4–6 added Road Ahead, DriveBC Open511, OpenWeather, and ECCC/SWOB evidence with source-specific provenance and failure handling. Phase 7 added the Vancouver camera catalogue, current-frame retrieval, gallery, and metadata-only nearby markers. Phase 8 added validated single-direction camera inference and provenance. Phase 9 added the internal journey evidence bundle and lifecycle handoff. Phase 10 added the source-grounded, three-topic AI Journey Briefing and completed the MVP. Accepted implementation details, caveats, and evidence remain in `PROJECT_STATE.md`'s archive and the integration notes.

## Historical records and accepted integration notes

- Exact original active documents, including their historical inconsistencies: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md).
- Phase 8B camera vision implementation and provider/budget evidence: [`docs/integration-notes/camera-vision-phase-8b.md`](docs/integration-notes/camera-vision-phase-8b.md).
- Phase 9A evidence inventory and accepted bundle/lifecycle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](docs/integration-notes/journey-evidence-phase-9a.md).
- Phase 10A briefing contract, model, limits, and accepted amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](docs/integration-notes/journey-briefing-phase-10a.md).
