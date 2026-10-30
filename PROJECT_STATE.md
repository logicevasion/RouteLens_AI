# RouteLens AI — Project State

## Current repository and SDD status

- **Implementation checkout:** Clean `main` at `566182e` when Alpha-UX-1 work began; changes below remain uncommitted. The earlier pre-Alpha documentation checkpoint was `40df498`.
- **Accepted corrections:** QAR-1 `d1bbcd4`, QAR-2 `45015aa`, USER-001 `b5dd20b`, and USER-002 `40df498`. Acceptance of all four is confirmed by the current human assignment; commit identities are independently verified locally.
- **Immediate objective:** Correct the second failed Alpha-UX-1 visual acceptance and prepare the slice for human re-review. This presentation work does not establish authentication, usage tracking, or deployment readiness.
- **Planning status:** Initial Alpha-UX-1 visual acceptance failed because a deferred React state updater read a mutable analysis-controller ref and stayed in Stage 1. The second visual test confirmed the summary transition but found page scrolling and forecast-card overflow defects. Those corrections and regressions are implemented; human re-review is pending. Alpha-UX-2 remains unauthorized.
- **Git control:** Human developers retain all staging and Git history control. No staging, commit, push, reset, or history change was performed for this task.

## Alpha-UX-1 implementation status

Initial human visual testing failed to show the Stage 2 summary. The confirmed cause was a deferred `setPresentation` updater reading `analysisController.current` after the handler assigned the active controller; it therefore kept the prior Stage 1 value. The transition now commits from the validated Analyze handler without reading the ref in a deferred updater. `JourneyStageLayout` keeps the summary and existing workspace together as one tested application composition.

The second human visual test confirmed that the summary mounted, then found the header scrolled out of view and no usable vertical scroll. Stage 2 had an auto-height shell under fixed-height roots and a hidden-overflow body; `scrollIntoView` moved the viewport to the summary while the shell had no scroll range. Stage 2 now uses a viewport-height scroll shell on desktop, normal document flow on narrow screens, a content-height workspace with a sized map, and a naturally growing support panel. Its one-time transition adjustment resets the viewport to the top. Primary next-hour cards now show only timestamp, temperature, condition, and precipitation probability; detailed measurements remain in the full supporting forecast. Their previous `white-space: nowrap` rule overrode the weaker wrapping rule for the long measurement string.

Stage 1 presents journey guidance and explicit route selection beside the large map, with the idle AI briefing placeholder removed. A valid Analyze Journey enters Stage 2 immediately, scrolls the primary summary into view once without moving focus, and shows a navigable one-image camera gallery, OpenWeather current conditions and actual next-hour intervals, the closest eligible ECCC observation, and a source-qualified Road Ahead direct-overlap count. The map, editable journey controls, detailed forecast/station data, Road Ahead findings, DriveBC context, and active briefing states remain accessible below the summary. Alpha-UX-2's map/construction layout, Experimental briefing placement, and collapsed supporting sections are not implemented.

Changed components and helpers: `App.tsx`, `JourneyStageLayout.tsx`, `JourneyPrimarySummary.tsx`, `presentation.ts`, `journeySummary.ts`, `DestinationCameraPanel.tsx`, `DestinationWeatherPanel.tsx`, `cameras.ts`, `weather.ts`, and `styles.css`. Deterministic presentation coverage was added or updated in `primarySummary.test.mjs`, `cameraPanel.test.mjs`, `weatherPanel.test.mjs`, and `journeyBriefingCard.test.mjs`.

**Verification:** Focused frontend checks passed (59 test cases across 5 files), including stage/page composition and compact forecast regressions. `cd frontend && npm test` passed (105 test cases across 12 files, 0 failures); `cd frontend && npm run build` passed with the existing nonblocking large-bundle advisory; `git diff --check` passed. Headless Chrome measured the production-CSS Stage 2 fixture at desktop and narrow widths: desktop app-shell scroll range was 119 px with the map reachable after scrolling; at an effective 500 px width the document scroll range was 534 px and the map entered the viewport after scrolling. This fixture did not load the full React app or MapLibre. No external requests or paid inference calls were made. Human visual re-review remains required for the live page, camera/map interactions, and proportions.

The USER-001 UUID v4 attempt identity, USER-002 inclusive camera cutoff, timeouts, abort/stale-result guards, frozen briefing evidence, and single briefing dispatch remain in the existing orchestration and lifecycle tests. No backend, API, normalized data contract, provider, or inference code changed. Alpha-UX-1 is not human accepted; Alpha-UX-2 remains unauthorized.

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

Human review of this documentation preparation, followed by a separate Alpha-UX-1 implementation prompt. Alpha-UX-2 remains separately authorized. No implementation has begun.

**Alpha UX documentation preparation (2026-10-30):** Governing documents, frontend composition and existing tests were source-inspected; accepted checkpoints were verified against local Git history. Documentation links, consistency and whitespace are checked for this task. No source/test changes, application test runs, live external requests, or paid inference. Documentation preparation does not establish runtime or visual acceptance.

## Archive and integration-note references

- Completed QAR-1 active plan before Alpha UX preparation (relative links adjusted): [pre-Alpha UX build plan](docs/archive/BUILD_PLAN_pre-AlphaUX.md).

- Exact pre-compaction records: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md). They preserve original content and inconsistencies as found.
- Accepted Phase 8B implementation, provider, and budget record: [`docs/integration-notes/camera-vision-phase-8b.md`](docs/integration-notes/camera-vision-phase-8b.md).
- Later accepted single-image MVP and camera-transfer authorization: [`docs/integration-notes/camera-vision-phase-8d.md`](docs/integration-notes/camera-vision-phase-8d.md).
- Accepted Phase 9A evidence inventory and bundle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](docs/integration-notes/journey-evidence-phase-9a.md).
- Accepted Phase 10A briefing contract and amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](docs/integration-notes/journey-briefing-phase-10a.md).
