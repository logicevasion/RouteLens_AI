# RouteLens AI — Project State

## Current repository and SDD status

- **Implementation checkout:** Alpha-UX-1 is accepted at `ed955d1` on `main`. Alpha-UX-2 is human accepted and ready for commit; its changes remain uncommitted.
- **Accepted corrections:** QAR-1 `d1bbcd4`, QAR-2 `45015aa`, USER-001 `b5dd20b`, USER-002 `40df498`, and Alpha-UX-1 `ed955d1` are accepted checkpoints.
- **Current objective:** Prepare a small, access-protected friends-only alpha deployment. Authentication, usage tracking, and broader deployment planning remain deferred.
- **Git control:** Human developers retain staging and Git history control. No staging, commit, push, reset, or history change was performed for Alpha-UX-2.
- **Git control:** Human developers retain staging and Git history control. Alpha-UX-2 is ready for a human-controlled commit and push.

## Alpha UX implementation status

Alpha-UX-1 is the accepted baseline: Stage 1 retains the large map beside explicit route choice; Stage 2 enters immediately, preserves header and controls, scrolls once to the page top, and presents camera and deterministic weather/road summary evidence. The accepted stage transition, camera timing, UUID identity, cancellation and stale-response safeguards remain in the existing lifecycle.

Alpha-UX-2 keeps the map mounted beside the independently scrollable Stage 2 road panel, with responsive stacking. The panel is titled **ROAD EVENTS & DISRUPTIONS**; direct City of Vancouver Road Ahead intersections are visible first, followed by collapsed, counted disclosures for nearby Road Ahead events and DriveBC Open511. Source-scoped event selection still reaches the shared map callback, and regional overlays, construction highlighting, route highlighting, and camera markers remain connected. Nearby and DriveBC event lists have been removed from lower supporting information; detailed source freshness/statuses, analysis context, full forecast intervals, and additional ECCC observations remain available there. The existing source-grounded AI briefing follows the map section, is labelled Experimental, retains its state content, and does not trigger inference from presentation or mounting.

Changed for Alpha-UX-2: `frontend/src/App.tsx`, `frontend/src/RoadAheadPanel.tsx`, `frontend/src/DestinationWeatherPanel.tsx`, `frontend/src/styles.css`, and frontend layout/briefing regression tests. No backend, API, normalized data contract, provider, model, prompt, or inference orchestration changed.

**Verification:** Focused `node --test tests/alphaUx2Layout.test.mjs tests/roadAheadMap.test.mjs` passed (2 test files); `cd frontend && npm test` passed (13 test files, 0 failures); `cd frontend && npm run build` passed with the existing nonblocking large-chunk advisory; and `git diff --check` passed. Fixture-backed coverage checks panel order and labels, direct/nearby/DriveBC counts and qualified zero states, selection callback wiring, native closed disclosures, source-specific geometry/status semantics, no duplicated lower event lists, supporting forecast details, and retained lifecycle regressions. Headless Chrome with local representative HTML and application CSS confirmed map and panel side by side, keyboard-focusable closed disclosures, and 527 px of independent panel scroll range with a disclosure expanded. This was a CSS/layout fixture, not the React application or MapLibre; narrow-screen behavior and live-page proportions still require human review. No external requests or paid inference were used.

**Status:** Alpha-UX-1 and Alpha-UX-2 are human accepted. The Alpha UX v1 presentation reorganization is complete. Protected-alpha access controls, deployment, and usage tracking have not been implemented.

## Accepted implementation baseline

Phases 0–10 are human accepted and complete; RouteLens AI MVP v1 is implementation-complete. The accepted product is a local, driving-only Vancouver journey companion with explicit route selection and on-demand analysis. The implementation covers the app/map and journey workflow (Phases 1–3), Road Ahead and DriveBC road evidence (4–5), OpenWeather and ECCC/SWOB weather evidence (6), Vancouver destination cameras (7), validated camera vision (8), the internal evidence bundle (9), and the three-topic AI Journey Briefing (10). This is a milestone summary; detailed acceptance evidence and limitations are preserved in the archive and integration notes.

**Phase 10 status:** Human acceptance is explicit in archived `PROJECT_STATE_pre-QAR1.md`, Section 53: Assignment 10D and Phase 10 are accepted and complete, following two successful live end-to-end briefing tests after the final reliability hotfix. The older pending-acceptance language in Sections 51–52 is historical and superseded by Section 53. Acceptance is not used to infer a Git commit.

## QAR-1 implementation status

Vision and briefing reservations now use one deterministic operating-system lock derived from their canonical ledger-path pair. Under that lock, each role validates both persisted ledgers, applies its existing role safeguards and the strict combined estimate limit, then atomically replaces only its own JSON ledger. A valid-state ARCH-004 regression and repeated separate-process concurrency coverage are in place. Full thresholds, error behavior, crash/write semantics, acceptance criteria, and exclusions remain in [the archived QAR-1 plan](docs/archive/BUILD_PLAN_pre-AlphaUX.md).

No external API or paid provider was used. QAR-1 was human accepted and committed/pushed at `d1bbcd4`. Local ledger estimates do not represent historical or authoritative provider/account spending.

## Accepted lifecycle corrections and deferred findings

- **USER-001 — Duplicate briefing attempts:** Confirmed cross-session numeric-ID collision is corrected. Each explicit Analyze Journey operation now gets one UUID v4 logical attempt ID carried through JourneyEvidenceBundle v1 and briefing request/result contracts. Numeric lifecycle IDs remain for camera matching and stale-response guards. The adapter still deduplicates in process memory; restart resets that state, multiple workers do not share it, and the set grows for the process lifetime. USER-001 was human accepted and committed at `b5dd20b`.
- **USER-002 — Camera interpretation timing:** Corrected the confirmed case where camera evidence completed by the accepted 15-second cutoff but was omitted because journey analysis finished after the cutoff. The camera opportunity coordinator now starts with camera inference and records monotonic settlement timing; timely evidence is retained for the single frozen briefing snapshot, while pending-at-cutoff evidence remains excluded if it arrives later. The independent 70-second camera deadline, briefing deadlines, and one-request rule are unchanged. Typical real-world camera latency remains unmeasured; USER-002 was human accepted and committed at `40df498`.
- **Deferred implementation findings:** Road Ahead selected-event emphasis may remain bold after journey-input edits or route regeneration until a new Analyze Journey operation. Camera failure-isolation improvements, exhaustive narrow-screen/source-combination review, and optional performance work remain deferred. They do not change the accepted MVP status.
- **Architecture scope:** The Phase 9 normalized timeline and richer cross-source reasoning/UI described in older roadmap material remain deferred; the accepted implementation uses the internal evidence bundle and Phase 10 briefing. Multi-view inference remains deferred; the MVP briefing uses one selected camera direction.

## Accepted architectural and product decisions

- `AGENTS.md` and `APP_SPEC.md` remain governing documents. `BUILD_PLAN.md` defines the current bounded approved assignment; this file records implementation reality. Historical decisions and evidence remain discoverable in the archives and integration notes.
- Codex may implement only separately authorized assignments. Future accepted assignments should be summarized here rather than appended as full implementation transcripts.
- RouteLens remains driving-only for the datathon MVP, with Vancouver destinations, explicit candidate-route selection, and manual/on-demand analysis. It is a journey companion, not a navigation replacement.
- Source evidence remains distinct and provenance-bearing. Missing/empty evidence is not an all-clear; camera retrieval time is not a verified capture time; Point proximity is not route overlap; camera observations are not authoritative speed, congestion, or meteorological measurements.
- The Phase 8/10 integrations use `google/gemma-4-31b-it` through OpenRouter with separate vision and briefing ledgers, role-specific quotas/estimates, and provider/account billing as authoritative. QAR-1 preserves these controls while coordinating aggregate local estimates.
- The later Phase 8D record authorizes current validated City of Vancouver camera frames to be sent to OpenRouter solely for the private, noncommercial prototype under existing limits; it supersedes the earlier 8B restriction. It does not authorize bulk/history collection, public redistribution, commercial deployment, or broader external sharing. Provider-side processing/retention and external image-use rights remain considerations for any expansion.
- Human developers control staging, commits, pushes, and Git history.

## Current limitations and external considerations

- Occasional camera unavailability, the limits of one directional view, temporal/geographic differences between images and weather, and possible model factual errors remain. References and deterministic source selection support review but do not prove every generated claim is entailed; human source comparison remains relevant.
- A historical repeated backend run stalled at `test_openweather_products_are_reported_independently[current]`. The confirmed unmocked Road Ahead requests were corrected in QAR-2, but the exact cause of that earlier stall was not established. The existing frontend production build reports a nonblocking large-bundle advisory.
- Provider model/routing capabilities, prices, account restrictions, and cumulative account spending can change. Provider/account billing is authoritative; local role ledgers do not establish total historical/account usage. Reconcile current cumulative usage against the project limit before further paid inference. No provider/account reconciliation was performed for this documentation task.

## Latest meaningful verification evidence

**Historical application verification (final Phase 10 record, 2026-10-11):** Focused briefing API tests passed (48); one full backend regression run passed (439 tests); Ruff passed; the full frontend suite passed (11 test files); and the TypeScript/Vite production build passed with the existing large-bundle advisory. A subsequent repeated backend run stalled and was interrupted as described above. The developer recorded two successful live end-to-end briefing tests after the final model-output hotfix and accepted the MVP. These are historical results, not checks rerun during this compaction.

**Documentation compaction verification at the 2026-10-28 checkpoint:** The archives were compared byte-for-byte with the original active documents before compaction (948 and 1,609 lines). Local markdown links and headings were checked, the expected four paths were the only changed documentation files, and `git diff --check` passed. No application tests, frontend build, live API, or paid provider checks were run for that compaction.

**QAR-1 corrective verification (2026-10-28):** Focused aggregate, vision, camera-vision API, and briefing API tests passed (138 total); Ruff and `git diff --check` passed. The compatibility-aware ARCH-004 regression was also run against the original adapters from `HEAD`; it failed at the expected budget assertion after the original logic accepted the sequence and persisted $5.002. Oversized valid JSON, semantically invalid ledgers, extreme numeric values, and process lock blocking are covered. No external provider requests or paid calls were made. QAR-1 was subsequently human accepted and committed/pushed at `d1bbcd4`.

**QAR-2 test-isolation verification (2026-10-29):** Both weather-product variants passed (2); the complete analysis API module passed (24); and the full backend suite passed (473) with 24 existing multiprocessing fork deprecation warnings. Every pytest run used a temporary socket/DNS guard; zero outbound attempts were recorded. Ruff on `test_analysis_api.py` and `git diff --check` passed. No live external or paid provider calls were made. The historical stall's exact cause remains unproven. QAR-2 was subsequently human accepted and committed at `45015aa`.

**USER-001 correction verification (2026-10-29):** The full backend suite passed (475) under a socket/DNS guard with zero outbound attempts; focused briefing API tests passed (51); Ruff and `git diff --check` passed; all 11 frontend test files passed; and the TypeScript/Vite production build passed with the existing large-bundle advisory. Regression coverage exercises default UUID v4 generation and uniqueness across a reset lifecycle counter, UUID v4 request/result validation, same-UUID concurrent deduplication with one provider dispatch and budget reservation, and failed-analysis no-dispatch wiring. The full frontend suite and app/Vite TypeScript no-emit checks were rerun for the default-generator coverage correction. No external service or paid provider was contacted.

**USER-002 timing correction (2026-10-29):** Camera opportunity settlement is coordinated from camera request initiation, using `performance.now()` and the unchanged 15-second absolute cutoff. Deterministic frontend regressions cover camera success at t=5 with analysis at t=20, late completion, pending-at-cutoff, just-before and exact-cutoff inclusion, bounded failure status, remaining-window behavior, superseded lifecycle suppression, and no second briefing request after late completion. Focused camera/briefing/evidence tests passed; the full 11-file frontend suite passed; TypeScript no-emit and the production build passed with the existing large-chunk advisory; `git diff --check` passed. No backend code, external API, or paid provider was used. The correction does not establish typical real-world camera latency. USER-002 was human accepted and committed at `40df498`.

## Next action

Commit and push the human-accepted Alpha-UX-2 implementation. Next, plan a minimal protected deployment for a small group of friends using the existing development environment. Full Google OAuth and usage analytics remain deferred.

**Alpha UX presentation refinement (2026-10-30):** The map-side panel now groups direct Road Ahead, nearby Road Ahead, and DriveBC Open511 in that order; only direct findings are open by default, and relocated event lists are absent from lower supporting information. Frontend tests and build passed; a local CSS fixture demonstrated map adjacency and independent panel scrolling. Full application visual behavior remains for human review. No backend, API, normalized data, inference, provider, infrastructure, or dependency changes; no external requests or paid inference.

## Archive and integration-note references

- Completed QAR-1 active plan before Alpha UX preparation (relative links adjusted): [pre-Alpha UX build plan](docs/archive/BUILD_PLAN_pre-AlphaUX.md).

- Exact pre-compaction records: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md). They preserve original content and inconsistencies as found.
- Accepted Phase 8B implementation, provider, and budget record: [`docs/integration-notes/camera-vision-phase-8b.md`](docs/integration-notes/camera-vision-phase-8b.md).
- Later accepted single-image MVP and camera-transfer authorization: [`docs/integration-notes/camera-vision-phase-8d.md`](docs/integration-notes/camera-vision-phase-8d.md).
- Accepted Phase 9A evidence inventory and bundle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](docs/integration-notes/journey-evidence-phase-9a.md).
- Accepted Phase 10A briefing contract and amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](docs/integration-notes/journey-briefing-phase-10a.md).
