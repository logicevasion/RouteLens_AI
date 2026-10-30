# RouteLens AI — Active Build Plan

## SDD authority and workflow

- `AGENTS.md` and `APP_SPEC.md` are the governing operating and product documents.
This file defines the currently selected bounded assignment. Planning approval does not authorize implementation; each implementation requires a separate human-approved prompt.
- `PROJECT_STATE.md` records repository implementation reality, accepted status, limitations, and current verification.
- Historical decisions and detailed evidence remain available in the exact pre-QAR-1 archives and accepted integration notes linked below.
- Codex may implement an assignment only after separate human authorization. Human developers control staging, commits, pushes, and all Git history.
- Future accepted assignments should be summarized in `PROJECT_STATE.md`, not appended as full implementation transcripts.

## Current assignment: QAR-1 — OpenRouter aggregate estimated-spending guard correction

**Status:** Scope approved for planning. The plan is for human review; implementation has not started and requires a separate human-approved implementation prompt.

**Objective:** Correct the reproduced defect that allows combined local estimated spending in the OpenRouter vision and briefing role ledgers to reach or exceed the accepted project-wide limit of strictly less than US$5.

### Approved scope and design

Use one shared project-level inter-process reservation coordination mechanism for every vision and briefing reservation path. Keep the provider adapters independent and the two persisted JSON role ledgers separate. Under the shared coordination, each reservation must read and validate both ledgers, apply all existing role-specific checks and the strict aggregate `< US$5` invariant, then update only the reserving role's ledger using its existing atomic-file replacement pattern. No reservation path may bypass the shared mechanism.

Preserve the existing role-specific thresholds and semantics:

- Vision: `round(role_estimate + reservation, 8) > 4.90` rejects. Exactly US$4.90 remains allowed by this role check.
- Briefing: `round(vision_estimate + briefing_estimate + reservation, 8) >= 4.99` rejects, including equality at US$4.99. Do not loosen this stricter existing check when adding the separate aggregate invariant.
- Both role ledgers retain their existing caps of 50 attempts per rolling hour and 100 per UTC day. Vision reserves US$0.02 per attempt and retains its approximately US$1/day estimate guard; briefing reserves US$0.002 per attempt. These role-specific estimate safeguards and provider/account-authoritative billing remain in force. Every accepted reservation is counted before transport, including failed and timed-out calls; QAR-1 adds no refunds, retries, or dispatch changes.

The local aggregate covers estimates represented in these two ledgers. It does not include unledgered historical spend or replace reconciling cumulative provider/account usage, including historical usage, against the under-US$5 project limit before any further paid inference. The vision US$4.90 estimate is a role safeguard, not an additional pool that can be added to US$5.

### Persisted state and failure semantics

- A missing role ledger keeps its existing empty-ledger initialization behavior.
- Malformed, unreadable, oversized, or otherwise invalid persisted state in either ledger fails closed. Do not reset, repair, or silently replace invalid state.
- The shared operating-system lock serializes reservation decisions across processes and is released if a process exits or crashes. The two ledger files are not one atomic transaction.
- A crash before atomic replacement leaves the prior target ledger intact (an unused temporary file may remain). A crash after replacement leaves the reservation counted, even if provider dispatch did not occur.
- A failed write or replacement denies dispatch and leaves the existing target ledger intact wherever the filesystem's atomic-replace guarantee applies.

### Verification and acceptance

Use temporary persisted-ledger files and mocked or non-dispatching transports only; no paid provider request is permitted. Add a valid-shaped controlled regression that reproduces the original aggregate violation, and cover:

- both sequential reservation orders and strict aggregate-threshold behavior;
- concurrent cross-role reservations from separate processes synchronized against the same ledgers;
- existing per-role hourly/daily attempt caps and estimate safeguards;
- missing-ledger initialization;
- malformed, unreadable, oversized, and otherwise invalid state in either ledger;
- denied reservations never dispatching a provider request.

Simulate unreadability deterministically if filesystem permissions do not reproduce it in the test environment. Run focused vision and briefing budget/API tests, Ruff on affected backend code and tests, and `git diff --check`. The controlled regression must fail against the original behavior and pass after correction.

Acceptance requires every reservation path to use the same inter-process coordination, no accepted sequential or concurrent reservations to produce a combined persisted estimate at or above US$5, all existing role-specific thresholds and semantics to remain unchanged, persisted-state errors to fail closed, and the stated focused tests/static checks to pass.

### Out of scope

USER-001, USER-002, QAR-2/test-suite investigation, other architecture findings, Phase 10 acceptance or implementation changes, provider/account integration, billing reconciliation, databases, new infrastructure or dependencies, and all Git operations. No API, model, prompt, provider, or frontend lifecycle changes are authorized.

## Accepted baseline: Phases 0–10

The human-accepted datathon MVP is driving-only and serves journeys into Vancouver. Phases 0–3 established the SDD foundation, application shell, Vancouver map, canonical geocoding and destination validation, ORS route alternatives, and explicit route selection. Phases 4–6 added Road Ahead, DriveBC Open511, OpenWeather, and ECCC/SWOB evidence with source-specific provenance and failure handling. Phase 7 added the Vancouver camera catalogue, current-frame retrieval, gallery, and metadata-only nearby markers. Phase 8 added validated single-direction camera inference and provenance. Phase 9 added the internal journey evidence bundle and lifecycle handoff. Phase 10 added the source-grounded, three-topic AI Journey Briefing and completed the MVP. Accepted implementation details, caveats, and evidence remain in `PROJECT_STATE.md`'s archive and the integration notes.

## Historical records and accepted integration notes

- Exact original active documents, including their historical inconsistencies: [`docs/archive/BUILD_PLAN_pre-QAR1.md`](BUILD_PLAN_pre-QAR1.md) and [`docs/archive/PROJECT_STATE_pre-QAR1.md`](PROJECT_STATE_pre-QAR1.md).
- Phase 8B camera vision implementation and provider/budget evidence: [`docs/integration-notes/camera-vision-phase-8b.md`](../integration-notes/camera-vision-phase-8b.md).
- Phase 9A evidence inventory and accepted bundle/lifecycle decisions: [`docs/integration-notes/journey-evidence-phase-9a.md`](../integration-notes/journey-evidence-phase-9a.md).
- Phase 10A briefing contract, model, limits, and accepted amendments: [`docs/integration-notes/journey-briefing-phase-10a.md`](../integration-notes/journey-briefing-phase-10a.md).
