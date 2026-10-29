# RouteLens AI — Project State

## Current repository and SDD status

- **Repository checkpoint:** At the start of the SDD consistency update on 2026-10-28, `main` was at `27a0aaa` and the working tree was clean. This is a dated checkpoint, not a permanent current-revision claim. The authorized update now changes only `AGENTS.md`, `APP_SPEC.md`, and this file.
- **Completed documentation compaction:** The SDD compaction is complete. The pre-compaction `BUILD_PLAN.md` and `PROJECT_STATE.md` are preserved as [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md). Detailed accepted Phase 8–10 decisions and evidence remain in the integration notes listed below.
- **Git control:** No staging, commit, push, reset, or other history operation was performed for this update. Human developers retain control of Git history.
- **Current assignment:** QAR-1 was human accepted and committed/pushed at `d1bbcd4`. QAR-2's narrowly scoped test-isolation correction is implemented and ready for human review; it has not been accepted. USER-001, USER-002, and other architecture findings remain pending/deferred.

## Accepted implementation baseline

Phases 0–10 are human accepted and complete; RouteLens AI MVP v1 is implementation-complete. The accepted product is a local, driving-only Vancouver journey companion with explicit route selection and on-demand analysis. The implementation covers the app/map and journey workflow (Phases 1–3), Road Ahead and DriveBC road evidence (4–5), OpenWeather and ECCC/SWOB weather evidence (6), Vancouver destination cameras (7), validated camera vision (8), the internal evidence bundle (9), and the three-topic AI Journey Briefing (10). This is a milestone summary; detailed acceptance evidence and limitations are preserved in the archive and integration notes.

**Phase 10 status:** Human acceptance is explicit in archived `PROJECT_STATE_pre-QAR1.md`, Section 53: Assignment 10D and Phase 10 are accepted and complete, following two successful live end-to-end briefing tests after the final reliability hotfix. The older pending-acceptance language in Sections 51–52 is historical and superseded by Section 53. Acceptance is not used to infer a Git commit.

## QAR-1 implementation status

Vision and briefing reservations now use one deterministic operating-system lock derived from their canonical ledger-path pair. Under that lock, each role validates both persisted ledgers, applies its existing role safeguards and the strict combined estimate limit, then atomically replaces only its own JSON ledger. A valid-state ARCH-004 regression and repeated separate-process concurrency coverage are in place. Full thresholds, error behavior, crash/write semantics, acceptance criteria, and exclusions remain in `BUILD_PLAN.md`.

No external API or paid provider was used. QAR-1 was human accepted and committed/pushed at `d1bbcd4`. Local ledger estimates do not represent historical or authoritative provider/account spending.

## Outstanding investigations and deferred findings

- **USER-001 — Duplicate briefing attempts:** Browser-local numeric attempt IDs may be reused after reloads while the backend deduplicates across its process lifetime, potentially rejecting legitimate new briefing attempts. Investigate and reproduce before approving a session-scoped identity correction; preserve one paid briefing dispatch per logical attempt.
- **USER-002 — Camera interpretation timing:** The briefing freezes evidence after a 15-second camera opportunity while vision may continue toward its 70-second frontend deadline. Investigate late-arriving results and actual latency before deciding whether to preserve the window, extend it, or introduce a controlled update. Any change to the single-request policy requires explicit approval.
- **QAR-2 — Analysis test-suite reliability:** The weather-product test omitted a mock for `app.analysis.get_road_ahead_data`, and both parameter variants attempted two Road Ahead GETs. The test now supplies an empty `RoadAheadResult` with valid source statuses and asserts the patched loader is called once. The unintended requests are confirmed; their relationship to the earlier historical stall remains unproven. QAR-2 is ready for human review, not accepted.
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

**QAR-2 test-isolation verification (2026-10-29):** Both weather-product variants passed (2); the complete analysis API module passed (24); and the full backend suite passed (473) with 24 existing multiprocessing fork deprecation warnings. Every pytest run used a temporary socket/DNS guard; zero outbound attempts were recorded. Ruff on `test_analysis_api.py` and `git diff --check` passed. No live external or paid provider calls were made. The historical stall's exact cause remains unproven. QAR-2 is ready for human review, not accepted.

## Next action

Human review of the QAR-2 test-isolation correction. Human acceptance and Git checkpoint remain pending.

## Archive and integration-note references

- Exact pre-compaction records: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md). They preserve original content and inconsistencies as found.
- Accepted Phase 8B implementation, provider, and budget record: [`docs/integration-notes/camera-vision-phase-8b.md`](docs/integration-notes/camera-vision-phase-8b.md).
- Later accepted single-image MVP and camera-transfer authorization: [`docs/integration-notes/camera-vision-phase-8d.md`](docs/integration-notes/camera-vision-phase-8d.md).
- Accepted Phase 9A evidence inventory and bundle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](docs/integration-notes/journey-evidence-phase-9a.md).
- Accepted Phase 10A briefing contract and amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](docs/integration-notes/journey-briefing-phase-10a.md).
