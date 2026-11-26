# RouteLens AI — Active Build Plan

## SDD authority and workflow

- `AGENTS.md` and `APP_SPEC.md` are the governing operating and product documents.
This file defines the currently selected bounded assignment. Planning approval does not authorize implementation; each implementation requires a separate human-approved prompt.
- `PROJECT_STATE.md` records repository implementation reality, accepted status, limitations, and current verification.
- Historical decisions and detailed evidence remain available in the exact pre-QAR-1 archives and accepted integration notes linked below.
- Codex may implement an assignment only after separate human authorization. Human developers control staging, commits, pushes, and all Git history.
- Future accepted assignments should be summarized in `PROJECT_STATE.md`, not appended as full implementation transcripts.

## Phase 1 — UX Stabilization

**Status:** Phases 1A–1D are complete. All four passed manual verification and independent Claude Code review and were accepted by the human developer.

### Phase 1A — Vancouver-only destination suggestions (accepted)

- Preserve broad origin autocomplete behavior.
- Destination autocomplete sends a MapTiler bbox derived from the authoritative City of Vancouver polygon, requests enough candidates to account for filtering, and returns at most the existing five suggestions in provider order.
- The existing municipal polygon validator is the eligibility filter. Keep submit-time destination validation unchanged.
- Keep the API backward compatible for callers that omit the optional search role. Handle empty/malformed results and upstream errors using current sanitized behavior.
- Limit code changes to the geocoding adapter/API, autocomplete request, focused tests, and factual project state.

### Phase 1B — Automatic first-route selection (accepted)

- On successful route generation, select the first usable candidate in response order. Use the existing selected card and map styling and the selected route for manually initiated analysis. Keep manual route selection available.
- Clear the old selection and dependent analysis when a new search starts. Empty and failed searches leave the selection clear. Preserve cancellation and stale-response guards so an older request cannot replace current results or selection.

### Phase 1C — Typography readability (accepted)

- Increase undersized frontend text by approximately 2–4 px where appropriate. Preserve the existing visual hierarchy, application behavior, and MapLibre basemap labels.
- Check wrapping for long location names and narrow viewports. Run the existing frontend tests, production build, and `git diff --check`. Use available browser tooling for a lightweight layout check.
- Record verification in `PROJECT_STATE.md` and provide a manual browser checklist for human review. Human developers retain staging, commits, pushes, and deployment.

### Phase 1D — Camera outage fallback (accepted)

- Screen the first validated-URL view at up to four intersections in the existing proximity order. Skip confirmed placeholders and unavailable primaries. Fetch other directions only at the selected intersection.
- Use the supplied JPEG as the source for an embedded SHA-256 and a small Pillow template tolerant of recompression and resizing. Preserve the original JPEG as a regression fixture.
- Bind browser-triggered vision to the gallery's selected intersection and current frame identities through a response/request header and cache-only validation. Keep the existing JSON response and briefing lifecycle. Exclude placeholders before inference or cached image delivery.
- Fixture-backed camera responses and a mocked vision provider verified the fallback and gallery-to-vision consistency. Browser behavior was manually verified. Matching against a newly captured live City outage image remains unverified, and the existing first-briefing camera interpretation timing issue remains open.
- All Phase 1D QA follow-up findings were addressed to Claude Code's and the human developer's satisfaction. The follow-up passed 497 backend tests and Ruff. Earlier Phase 1D verification passed all 15 frontend test files and the TypeScript/Vite production build with the existing large-chunk advisory. [Detailed verification](PROJECT_STATE.md#phase-1-status)

## Phase 2 — API usage visibility and controls

- **Phase 2A complete.** Read-only audit of provider integrations, caches, budgets, and tracking feasibility.
- **Phase 2B implemented and ready for review.** SQLite stores backend request-attempt counts per operation and UTC date. `GET /api/usage` supplies the header's API Usage disclosure with aggregate counts over 30 UTC dates, including today. The read-only `backend/scripts/api_usage_report.py` accepts `--days`, `--daily`, and `--operations`. Browser-side MapTiler resources are untracked, and calls before instrumentation have no historical records. Tracking is best effort and surfaces known gaps or database unavailability. [Implementation and verification](PROJECT_STATE.md#phase-2-status)
- **Phase 2C deferred.** Separately authorize any lightweight daily quotas. Phase 2B preserves existing provider budgets and performs no quota enforcement.

## Completed correction assignment

QAR-1 is accepted at `d1bbcd4`. Its prior active plan (only relative links adjusted for the archive location), including thresholds, persisted-state semantics and verification criteria, is preserved in [the pre-Alpha UX archive](docs/archive/BUILD_PLAN_pre-AlphaUX.md). QAR-2 (`45015aa`), USER-001 (`b5dd20b`) and USER-002 (`40df498`) are also human accepted. These checkpoints were confirmed in local Git history; acceptance is supplied by the human task prompt.

## Accepted baseline: Phases 0–10

The human-accepted datathon MVP is driving-only and serves journeys into Vancouver. Phases 0–3 established the SDD foundation, application shell, Vancouver map, canonical geocoding and destination validation, and ORS route alternatives. That baseline required manual route selection until UX Stabilization Phase 1B added automatic first-route selection. Phases 4–6 added Road Ahead, DriveBC Open511, OpenWeather, and ECCC/SWOB evidence with source-specific provenance and failure handling. Phase 7 added the Vancouver camera catalogue, current-frame retrieval, gallery, and metadata-only nearby markers. Phase 8 added validated single-direction camera inference and provenance. Phase 9 added the internal journey evidence bundle and lifecycle handoff. Phase 10 added the source-grounded, three-topic AI Journey Briefing and completed the MVP. Accepted implementation details, caveats, and evidence remain in `PROJECT_STATE.md`'s archive and the integration notes.

## Historical records and accepted integration notes

- Exact original active documents, including their historical inconsistencies: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](docs/archive/BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](docs/archive/PROJECT_STATE_pre-QAR1.md).
- Phase 8B camera vision implementation and provider/budget evidence: [`docs/integration-notes/camera-vision-phase-8b.md`](docs/integration-notes/camera-vision-phase-8b.md).
- Phase 9A evidence inventory and accepted bundle/lifecycle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](docs/integration-notes/journey-evidence-phase-9a.md).
- Phase 10A briefing contract, model, limits, and accepted amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](docs/integration-notes/journey-briefing-phase-10a.md).
