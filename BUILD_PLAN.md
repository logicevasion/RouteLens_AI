# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 1 — Application Shell + Map
**Status:** Planned — authorized for implementation; not yet verified
**Source:** `docs/implementation-plan.md`, Phase 1
**Previous phase:** Phase 0 — Integration Readiness, accepted by the human developer on 2026-10-09

### Objective

Create the initial runnable RouteLens AI application, establishing the frontend and backend foundations and a visually coherent desktop interface.

Phase 1 must deliver:

- a functioning React/Vite/TypeScript frontend;
- a minimal FastAPI backend;
- successful frontend-to-backend communication;
- an interactive MapLibre map using the validated MapTiler dark basemap;
- a desktop layout with a fixed approximately 65% map / 35% intelligence-panel split;
- foundational styling and intentional placeholder states.

**Phase 1 establishes the working application shell. It does not implement journey analysis or telemetry integration.**

The result should be a recognizable, interactive RouteLens application that can be launched locally and visually inspected.

---

## 2. Execution Scope

This document defines the complete Phase 1 acceptance boundary.

Phase 1 may be implemented through multiple smaller Codex assignments. Each assignment receives a bounded prompt specifying its immediate objective, expected changes, and verification requirements.

- Do not interpret this document as authorization to implement every Phase 1 component in one assignment.
- Implement only the work specifically authorized by the current assignment prompt.
- Preserve completed functionality and verification evidence between assignments.
- Update `PROJECT_STATE.md` with meaningful implementation progress.
- Do not begin Phase 2 until Phase 1 has been accepted by the human developer.

### Planned Assignments

**Assignment 1A — Application Foundation**

Establish the frontend/backend project structure, approved dependencies, minimal FastAPI health endpoint, and verified frontend-to-backend connectivity.

**Assignment 1B — Interactive Vancouver Map**

Integrate MapLibre with MapTiler's validated dark style, establishing an interactive geographic map with appropriate resource handling, attribution, and initial Vancouver viewport.

**Assignment 1C — Desktop Shell and Visual Integration**

Build the complete desktop application layout, integrate the map into its intended interface, implement the right-side intelligence placeholder, and perform Phase 1 visual and functional verification.

These assignment boundaries are organizational, not independent architectural layers.

Avoid introducing elaborate abstractions merely to accommodate separate assignments.

---

## 3. Established Phase 0 Readiness

Phase 0 was completed and accepted before this build plan was prepared.

Relevant verified findings are recorded in:

- `docs/integration-notes/phase-0-readiness-summary.md`
- `docs/integration-notes/geographic-services-readiness.md`
- `PROJECT_STATE.md`

### MapTiler

Phase 0 established:

- working authenticated MapTiler access;
- accessible geocoding/autocomplete;
- usable Metro Vancouver coordinates and administrative context;
- an accessible `streets-v4-dark` map style;
- successful retrieval of supporting TileJSON, vector-tile, sprite, and glyph resources.

Phase 1 should use the validated dark style.

Do not repeat broad MapTiler discovery or switch basemap providers without a material implementation reason.

Actual MapLibre browser rendering was not tested during Phase 0 and must now be verified.

### Other Integrations

Phase 0 also validated representative OpenWeather, openrouteservice, and OpenRouter capabilities.

Those providers are not part of Phase 1 functionality.

Do not introduce their application adapters, API calls, or UI integrations during this phase.

### Configuration

The root `.env.example` contains the approved credential names and provisional OpenRouter model identifiers.

The root `.env` is Git-ignored and contains the locally configured MapTiler credential.

The TransLink key remains a deferred configuration follow-up before Phase 10 and does not block Phase 1.

Preserve existing configuration and secret-handling requirements.

---

## 4. Required Phase 1 Workstreams

### 4.1 Backend — FastAPI Application Foundation

Create the minimal Python backend consistent with the approved technical design.

Required behavior:

- A runnable FastAPI application.
- A health-check endpoint:

  `GET /api/health`

- A small JSON success response indicating that the backend is operational.
- Appropriate local-development startup configuration.
- Straightforward and maintainable application structure.
- Basic automated health-endpoint verification.

The backend should remain minimal.

Do not create source adapters, persistence infrastructure, orchestration services, or speculative domain abstractions.

### 4.2 Frontend — React Application Foundation

Create the frontend using the approved stack:

- React;
- Vite;
- TypeScript;
- Tailwind CSS;
- MapLibre GL JS;
- Framer Motion;
- Lucide icons.

Required outcomes:

- A functioning local Vite development server.
- A maintainable frontend source structure.
- Functional React application entry point.
- Global styles and a coherent dark visual foundation.
- Working production frontend build.
- Clear development instructions for starting the frontend.

Use stable, compatible dependency versions.

Follow current dependency-specific configuration requirements rather than assuming older setup patterns remain valid.

Do not introduce a component framework or state-management library without a concrete need.

### 4.3 Frontend-to-Backend Communication

Establish a working connection between the Vite frontend and FastAPI backend.

Requirements:

- The frontend can request `GET /api/health`.
- Successful communication is visibly or otherwise directly verifiable.
- Backend unavailability does not crash the frontend.
- Connection failures produce a reasonable development-stage state.
- Local development avoids unnecessary cross-origin complexity.

Prefer a Vite development proxy for `/api` requests unless there is a concrete reason to choose another approach.

Do not introduce authentication, user accounts, background polling systems, or a generic API-client abstraction.

### 4.4 MapLibre — Interactive Vancouver Map

Render a real interactive geographic map using:

- MapLibre GL JS;
- MapTiler;
- the validated `streets-v4-dark` style.

Requirements:

- The map loads successfully in a browser.
- The initial viewport is centered on Vancouver.
- An appropriate initial zoom level displays useful geographic context.
- Users can pan and zoom.
- The map fills its intended container.
- Map resizing and container changes do not leave the viewport broken.
- Loading and error states are handled reasonably.
- Required attribution remains visible.
- Map initialization and cleanup work correctly within React lifecycle behavior.

Do not implement route layers, telemetry overlays, camera markers, transit visualization, or geocoding.

This phase establishes only the foundational basemap interaction.

### 4.5 MapTiler Credential Handling

MapTiler's browser-accessible map resources require suitable client-side configuration.

The local root `.env` currently contains the validated MapTiler credential.

Requirements:

- Use an explicit, documented mechanism to make only the necessary MapTiler browser key available to Vite.
- Do not expose backend-only credentials to the frontend.
- Do not copy the entire root `.env` into the Vite frontend environment.
- Do not embed actual credentials directly in tracked source code.
- Do not assume that a Vite-prefixed variable is secret or hidden from browser users.
- Preserve `.env` ignore behavior and sanitize diagnostic output.

If the existing MapTiler key requires additional restrictions or is unsuitable for browser use, identify that requirement for human review.

Do not implement a general secret-management platform or proxy all map tiles through FastAPI solely to conceal a browser-accessible map key.

### 4.6 Desktop Layout

Establish the approved RouteLens desktop interface.

Primary regions:

1. Top journey-controls area.
2. Left map area.
3. Right journey-intelligence panel.

Use a **fixed approximately 65% map / 35% intelligence-panel split** for the main desktop content region.

This ratio should remain visually consistent on normal desktop viewport sizes.

Requirements:

- The map occupies the dominant portion of the interface.
- The intelligence panel is visibly distinct.
- The layout avoids overlapping regions.
- The map remains usable and correctly sized.
- Normal browser resizing does not break the interface.
- The panel can support future vertically scrolling information.
- The top region clearly communicates where journey input will eventually appear.

Do not implement a user-resizable panel or draggable split controls.

Do not introduce persistent layout preferences.

A basic fallback for narrower screens is permitted to avoid broken presentation, but mobile-specific product design is outside the MVP scope.

### 4.7 Foundational Visual Design

The interface should establish the approved dark city-intelligence aesthetic.

Priorities:

- dark, low-clutter presentation;
- readable typography;
- clear visual hierarchy;
- suitable map/panel contrast;
- cohesive spacing;
- clean panel boundaries;
- restrained accent colors;
- intentional placeholders;
- basic loading, connection, and failure states.

Use Tailwind CSS for primary styling.

Lucide may provide appropriate visual icons.

Framer Motion is an approved dependency, but do not add decorative animation merely to demonstrate its use.

Subtle transitions are acceptable where they improve comprehension.

### 4.8 Placeholder Components and Future Integration

The Phase 1 shell should visibly communicate the eventual RouteLens workflow without pretending later-phase features are functional.

Reasonable placeholders include:

- origin input area;
- destination input area;
- Drive / Transit mode area;
- Analyze Journey action;
- destination-condition panel;
- route findings;
- transit advisories;
- AI briefing area.

These are presentation scaffolds only.

Requirements:

- Future actions must be disabled, labeled as unavailable, or otherwise clearly nonfunctional.
- Do not fabricate live weather, road events, camera interpretations, or transit alerts.
- Do not display invented journey analysis as real application results.
- Avoid designing permanent application data contracts from placeholder content.
- Keep placeholders easy to replace during later vertical slices.

The frontend may display real backend connectivity status because that functionality is implemented in Phase 1.

---

## 5. Expected Scope and Artifacts

Phase 1 may create or update:

- `backend/` — minimal FastAPI application, dependencies, configuration, and tests;
- `frontend/` — React/Vite/TypeScript application and required configuration;
- frontend styling and shell components;
- MapLibre initialization and presentation components;
- local development instructions;
- relevant configuration templates or narrowly scoped environment handling;
- `PROJECT_STATE.md`.

These paths are anticipated areas, not a strict filesystem allowlist.

A suggested structure from `docs/technical-design.md` may be used where appropriate, but do not pre-create empty source adapters, domain modules, database directories, or future feature components.

Create only what the current bounded assignment needs.

---

## 6. Non-Goals

Phase 1 must not implement:

- MapTiler autocomplete or geocoding application behavior;
- origin/destination normalization;
- City of Vancouver destination-boundary validation;
- openrouteservice routing;
- route alternatives or route selection;
- Road Ahead, Open511, SWOB, OpenWeather, or TransLink integration;
- Vancouver camera ingestion or image processing;
- OpenRouter inference;
- journey analysis or AI briefing;
- persistence, SQLite models, or production caching;
- authentication, user accounts, or personalization;
- mobile application functionality;
- real-time subscriptions or background workers;
- custom route optimization;
- deferred MVP sources.

Do not use mock telemetry to imply real functionality exists.

Do not introduce Docker, Kubernetes, Redis, PostgreSQL, or other infrastructure not required by the approved local MVP.

Do not redesign the approved architecture merely because a different tool appears convenient.

---

## 7. Verification Requirements

Each bounded assignment must perform the relevant checks for its authorized changes.

### Backend Verification

Where the backend is affected:

- Confirm the FastAPI application starts.
- Test `GET /api/health`.
- Verify expected status code and response structure.
- Run pytest for relevant tests.
- Run Ruff for affected Python files.
- Report startup, dependency, and test failures.

### Frontend Verification

Where the frontend is affected:

- Confirm the Vite application starts.
- Run the frontend production build.
- Verify frontend-to-backend connectivity where applicable.
- Inspect development-server errors.
- Check for missing dependencies or TypeScript failures.

### Map Verification

Where map functionality is affected:

- Verify real MapTiler style/resource loading.
- Verify MapLibre initializes successfully.
- Verify panning and zooming.
- Verify attribution is displayed.
- Check map-container sizing.
- Check loading and failure behavior.

A successful MapTiler HTTP response alone does not prove that the map renders correctly in the browser.

Browser-rendering verification must be explicitly reported as Passed, Failed, or Not run.

### Visual Verification

For the completed shell:

- Inspect the main interface at a normal desktop viewport.
- Confirm the fixed approximate 65/35 split.
- Confirm usable map dimensions.
- Confirm right-panel readability.
- Confirm placeholders do not falsely indicate working functionality.
- Check layout behavior after browser resizing.
- Check that frontend and backend failure states are understandable.

Human visual acceptance is required for Phase 1 completion.

### Reporting Standard

Every check must be classified as:

- **Passed** — performed successfully.
- **Failed** — performed but did not satisfy expectations.
- **Not run** — not executed, with reason.

Do not report a test or manual browser inspection as successful unless it actually occurred.

---

## 8. Phase 1 Acceptance Criteria

Phase 1 is ready for human acceptance when:

- [ ] The backend starts locally.
- [ ] `GET /api/health` returns the expected success response.
- [ ] Backend health-endpoint tests pass.
- [ ] Relevant Ruff checks pass.
- [ ] The React/Vite/TypeScript frontend starts locally.
- [ ] The frontend can reach the FastAPI backend.
- [ ] Backend unavailability is handled without a frontend crash.
- [ ] MapLibre renders the validated MapTiler dark style.
- [ ] Vancouver appears in a suitable initial viewport.
- [ ] The map supports pan and zoom interactions.
- [ ] MapTiler attribution is visible.
- [ ] The layout has a recognizable top-control region.
- [ ] The desktop content uses the approved fixed approximately 65/35 map/panel split.
- [ ] The right-side intelligence panel is visible and readable.
- [ ] Placeholder actions are clearly nonfunctional.
- [ ] No fictitious telemetry is presented as real data.
- [ ] The frontend build succeeds.
- [ ] Local startup instructions are documented.
- [ ] No backend-only API credentials are exposed through the frontend.
- [ ] Relevant browser/map behavior is manually verified.
- [ ] `PROJECT_STATE.md` reflects the implementation and verification results.
- [ ] Codex provides the required completion report and confirms no Git commit or push was performed.

Passing this checklist makes Phase 1 eligible for human review; it does not constitute automatic acceptance.

---

## 9. Blockers and Escalation

Stop affected work and report when:

- required MapTiler access is missing or rejected;
- selected dependencies are materially incompatible;
- browser map rendering cannot be established within the approved stack;
- the existing MapTiler credential is unsuitable for browser use without a significant design decision;
- an architectural change or new major dependency becomes necessary;
- completion requires implementing later-phase behavior;
- destructive operations or unrelated repository changes become necessary;
- verification cannot be completed and the remaining uncertainty materially affects acceptance.

For each blocker, report:

- observed problem;
- affected requirement;
- available evidence;
- reasonable options, where apparent.

Continue independent in-scope implementation work when safe.

Routine implementation details, small compatibility corrections, and ordinary test failures may be resolved autonomously within the assignment.

Do not independently change providers, introduce substantial infrastructure, or expand application scope.

---

## 10. Phase Completion and Handoff

After each bounded assignment:

- Run relevant verification.
- Update `PROJECT_STATE.md` with verified progress.
- Preserve completed functionality.
- Report new files and behavior.
- Identify failures, limitations, and material decisions.
- Provide the standard completion report required by `AGENTS.md`.
- Do not claim the entire phase is complete until all applicable acceptance criteria have been assessed.

Phase 1 is accepted only after human review of:

- running application behavior;
- interactive map functionality;
- visual layout;
- relevant tests and builds;
- meaningful limitations or deviations.

Git checkpoints remain human-controlled.

Codex must not stage, commit, push, amend, merge, rebase, or rewrite history.

---

## 11. Next Phase

**Phase 2 — Journey Input + Geocoding**

After Phase 1 acceptance, Phase 2 adds:

- MapTiler place autocomplete;
- origin/destination selection;
- canonical location data;
- deterministic City of Vancouver destination validation;
- persistent frontend selection state.

Phase 2 work is not authorized by this document.
