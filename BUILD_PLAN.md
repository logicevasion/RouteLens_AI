# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 0 — Integration Readiness  
**Status:** Planned — not yet implemented or verified by Codex  
**Source:** `docs/implementation-plan.md`, Phase 0

### Objective

Resolve remaining external-service access, schema, configuration, and integration uncertainties before substantial application implementation begins.

Most core data-source research has already been completed during planning.

This phase must confirm outstanding integrations, preserve useful evidence, and identify blockers without unnecessarily repeating completed research.

**Phase 0 establishes integration readiness. It does not build application features.**

## 2. Execution Scope

This document defines the complete Phase 0 acceptance boundary.

Phase 0 may be completed through multiple smaller Codex assignments. Each assignment receives a bounded prompt from the planning agent specifying its immediate objective, expected outputs, and verification requirements.

- Do not interpret this document as authorization to implement every workstream in a single assignment.
- Perform only the workstream or subset explicitly assigned by the current prompt.
- Preserve completed work and findings between assignments through repository artifacts and `PROJECT_STATE.md`.
- Do not begin Phase 1 until the human accepts Phase 0 and authorizes the next phase.

The requirements below describe the full phase, not a mandatory execution sequence.

## 3. Existing Planning Research

The following integrations have already undergone substantial planning-stage investigation.

### Vancouver Traffic Webcams

- Geolocated camera catalogue is available.
- Official camera pages expose directional JPEG URLs requiring catalogue enrichment.
- One-nearest-usable-intersection and combined multi-view assessment strategies are approved.

### Vancouver Road Ahead

- Both Current Road Closures and Projects Under Construction were investigated.
- Full geometry is available, including complex geometry types.
- Short dataset fields may be incomplete.
- Detail pages provide supplementary schedule and restriction context.
- Validated daily caching is approved.

### DriveBC Open511

- Regional bounding-box fetching is the approved strategy.
- Pagination is required.
- Regional map visibility and journey-specific filtering are separate.
- Initial regional cache interval is approximately 5–15 minutes.

### ECCC GeoMet / SWOB

- Live Vancouver-area observations were successfully retrieved.
- Station coverage is sparse and measurements may be missing.
- Station catalogue coverage may be incomplete.
- Initial cache interval is approximately 10–15 minutes.

### TransLink

- API credentials were obtained and tested during planning.
- GTFS Static was inspected.
- GTFS-Realtime Service Alerts were decoded and investigated.
- Deterministic route/direction matching is viable.
- Request-header handling requires attention.
- Trip Updates and Vehicle Positions are deferred.

These findings provide the existing research baseline.

Do not repeat broad discovery for these sources unless a specific assigned readiness task, missing fixture, changed source behavior, or material discrepancy justifies further validation.

Prior planning results do not automatically establish that current repository fixtures, configuration, or executable checks exist. Record actual repository state separately.

## 4. Required Phase 0 Workstreams

### 4.1 OpenWeather — Priority Integration Gap

OpenWeather is the largest remaining source-specific uncertainty.

Required outcomes:

- Confirm the existing API key works.
- Identify accessible current-condition and forecast endpoints.
- Inspect actual response schemas.
- Identify usable current-condition fields.
- Identify available forecast fields and intervals.
- Establish supported near-term lookahead granularity.
- Determine a practical initial request and cache strategy.
- Save representative sanitized response fixtures.
- Document limitations, unavailable fields, and relevant plan restrictions.

Do not assume endpoint access, forecast granularity, or field availability until confirmed through actual API responses.

Do not implement the complete weather adapter or frontend weather presentation in Phase 0.

### 4.2 MapTiler — Mapping and Geocoding Readiness

Confirm:

- API-key access and expected authentication behavior.
- Autocomplete/geocoding availability.
- Representative place-search results and coordinate information.
- Dark basemap/style access suitable for MapLibre integration.

Record relevant configuration requirements and integration limitations.

A full map UI is not required; it belongs to Phase 1.

### 4.3 openrouteservice — Routing Readiness

Confirm:

- API-key access and routing endpoint availability.
- Successful routing for representative Metro Vancouver origins and Vancouver destinations.
- Availability and behavior of alternative route candidates.
- Usable returned geometry and route metadata.
- Practical limitations affecting route-candidate selection.

Do not assume three route alternatives will always be returned.

Do not implement the journey route-selection UI or complete routing application layer.

### 4.4 OpenRouter — AI Inference Readiness

Confirm candidate inference models for two responsibilities.

**Vision model:**

- Valid configured model identifier.
- Successful authenticated API request.
- Ability to accept multiple images in one request.
- Feasibility of returning structured output suitable for `CameraObservation`.

**Text model:**

- Valid configured model identifier.
- Successful authenticated API request.
- Feasibility of reliable structured output for journey briefing.

Record model identifiers, configuration requirements, observed limitations, and relevant output-format behavior.

Models are not permanently fixed by the architecture. Candidate selection may be revisited when the corresponding application phases are implemented.

Do not construct the complete camera-analysis or journey-briefing pipelines during Phase 0.

### 4.5 Configuration and Credential Readiness

Create or update `.env.example` with the required configuration variable names and placeholders.

Confirm that:

- `.env` is Git-ignored.
- Credentials are accessed through appropriate environment configuration.
- Required credentials are present or explicitly identified as missing.
- No secrets appear in tracked fixtures, code, logs, or reports.
- Provider-specific configuration requirements are documented sufficiently for later integration.

Do not fabricate credentials or commit secret values.

### 4.6 Representative Fixtures and Evidence

Preserve useful representative response fixtures for the sources needed in early implementation phases.

Requirements:

- Prefer real observed payloads or representative excerpts.
- Preserve meaningful schema structure and relevant edge cases.
- Remove secrets, tokens, and sensitive request information.
- Make fixture provenance and observed behavior understandable.
- Avoid creating extensive test infrastructure before application functionality exists.

Reuse existing valid fixtures when available.

Do not manufacture purportedly live evidence for integrations that could not be accessed.

## 5. Expected Scope and Artifacts

Phase 0 may create or update:

- `.env.example`;
- `.gitignore`, where needed;
- source fixtures under an appropriate test-fixture location;
- lightweight integration-check scripts or tests where useful;
- concise integration findings or configuration notes where needed;
- `PROJECT_STATE.md`.

These are anticipated areas, not a rigid filesystem allowlist.

Additional supporting files may be created when directly necessary for the assigned work.

The repository's eventual directory structure should remain consistent with `docs/technical-design.md`, without pre-creating unrelated application modules.

## 6. Non-Goals

Phase 0 must not implement:

- the FastAPI application shell or production API endpoints;
- the React frontend or MapLibre map interface;
- journey input, autocomplete UI, or route-selection UX;
- complete telemetry adapters and orchestration;
- database-backed caching or persistence infrastructure;
- production camera analysis or journey briefing;
- speculative abstractions for later integrations;
- deferred MVP data sources.

Do not redesign approved source strategies merely because an alternative appears convenient.

Do not introduce heavyweight infrastructure or significant new runtime dependencies without approval.

## 7. Verification Requirements

Each assigned workstream must provide evidence appropriate to its scope.

### External-Service Verification

For every required unresolved integration:

- Attempt safe authenticated requests using available configuration.
- Establish whether access succeeds or fails.
- Inspect relevant real response behavior.
- Capture representative evidence where appropriate.
- Report unsupported assumptions, errors, and limitations.

Successful authentication alone is insufficient when endpoint capabilities or schemas remain unresolved.

### Repository Verification

Where files, scripts, or tests are introduced:

- Run relevant available tests.
- Run Ruff for affected Python code.
- Verify that fixtures are readable and free of credentials.
- Verify environment-file ignore behavior.
- Run additional checks required by the bounded assignment.

Frontend builds are not required unless frontend code is explicitly authorized and modified.

### Verification Reporting

Classify each check as:

- **Passed** — performed successfully.
- **Failed** — performed but did not satisfy expectations.
- **Not run** — could not be performed, with reason.

Do not report planned or assumed verification as completed.

A live-service failure must not be concealed by a locally fabricated success result.

## 8. Phase 0 Acceptance Criteria

Phase 0 is ready for human acceptance when:

- [ ] Every core MVP telemetry source has a documented access path.
- [ ] Required credentials are available or confirmed unnecessary, with no unresolved required-access blocker.
- [ ] OpenWeather has undergone actual authenticated endpoint and schema exploration.
- [ ] OpenWeather current/forecast availability, practical lookahead, and initial caching approach are documented.
- [ ] MapTiler geocoding/autocomplete and basemap access are verified.
- [ ] openrouteservice routing and route-alternative behavior are verified.
- [ ] OpenRouter candidate vision and text models have been called successfully and their relevant capabilities evaluated.
- [ ] `.env.example` documents required configuration names without secrets.
- [ ] `.env` is Git-ignored and committed/tracked artifacts contain no credentials.
- [ ] Representative fixtures exist for sources needed in early phases.
- [ ] Important integration limitations and unexpected behavior are recorded.
- [ ] No major required source-access blocker remains undiscovered or unresolved.
- [ ] `PROJECT_STATE.md` accurately reflects completed checks, findings, limitations, and outstanding work.
- [ ] Codex has reported verification results and confirmed that it performed no Git commit or push.

Planning-stage source research may satisfy documented discovery requirements where sufficient evidence already exists. Repository artifacts and newly required live checks must be verified rather than assumed.

Passing the checklist makes Phase 0 eligible for human review; it does not constitute automatic acceptance.

## 9. Blockers and Escalation

Stop affected work and report when:

- required credentials are missing or rejected;
- a required endpoint or API capability is unavailable;
- source behavior materially contradicts the approved design;
- a significant new dependency or provider change appears necessary;
- expected structured output or multi-image capability is not supported;
- acceptance criteria cannot be met within the authorized scope;
- destructive operations or material architectural changes become necessary.

For each blocker, report the observed problem, affected requirement, evidence, and reasonable options if apparent.

Continue unrelated in-scope readiness work when safe.

Do not independently substitute a provider, redesign the integration, expand the phase, or declare a blocked requirement satisfied.

Blocked or partially verified work must remain visible in `PROJECT_STATE.md`.

The human and planning agent decide whether a design adjustment, additional validation, or revised acceptance criterion is appropriate.

## 10. Phase Completion and Handoff

At the end of each bounded Codex assignment:

- Update `PROJECT_STATE.md` with factual results and outstanding work.
- Provide the completion report required by `AGENTS.md`.
- Distinguish completed verification from pending checks.
- Do not claim that Phase 0 is accepted before human review.

Phase 0 is accepted only when the human reviews the accumulated readiness evidence, resolves or deliberately revises blockers, and approves the phase checkpoint.

Git commits are created manually by the human.

## 11. Next Phase

**Phase 1 — Application Shell + Map**

After Phase 0 acceptance, the planning agent will prepare the next `BUILD_PLAN.md`.

Phase 1 establishes the minimal FastAPI backend, React/Vite frontend, dark MapTiler/MapLibre map, and desktop application shell.

Phase 1 work is not authorized by this document.
