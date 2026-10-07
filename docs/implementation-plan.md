# RouteLens AI — Implementation Plan

## 1. Purpose

This document defines the planned implementation sequence for the RouteLens AI MVP.

It answers:

> **In what order should the system be built?**

The Product Requirements Document defines the product destination.

The Technical Design defines the intended architecture.

This implementation plan converts those artifacts into a sequence of **vertical development slices** that produce observable working functionality as early as possible.

The plan is intended primarily for:

- the human developer;
- the planning agent;
- creation of the Codex-facing SDD harness;
- generation of bounded Codex implementation prompts.

This document is a roadmap, not a live progress tracker.

Current implementation state should eventually be recorded separately in:

> `PROJECT_STATE.md`

---

# 2. Implementation Philosophy

RouteLens should be built using **vertical slices / tracer-bullet development**.

Avoid a horizontal sequence such as:

```text
build entire backend
        ↓
build all adapters
        ↓
build database
        ↓
build entire frontend
        ↓
finally integrate
```

Instead, build narrow end-to-end capabilities:

```text
external source
      ↓
normalization
      ↓
business / geospatial logic
      ↓
API
      ↓
frontend
      ↓
observable behavior
      ↓
verification
```

Each meaningful phase should leave RouteLens in a valid and increasingly usable state.

---

# 3. Phase Boundaries

Each phase should be small enough that:

- Codex can implement it within a bounded context;
- the human can review it in one sitting;
- the functionality can be tested behaviorally;
- the phase can become one logical human-created Git commit.

A phase should not attempt to implement several unrelated systems at once.

---

# 4. Human-Controlled Git Checkpoints

Codex does not own Git history.

For every implementation phase:

```text
Planning agent defines phase
        ↓
Codex implements
        ↓
Codex runs verification
        ↓
Codex reports changes/results
        ↓
Human reviews
        ↓
Fixes if required
        ↓
Human manually commits
        ↓
Next phase
```

Codex must not:

- commit
- push
- merge
- tag
- rewrite Git history

The accepted human commit forms the stable checkpoint before the next phase begins.

---

# 5. Default Phase Completion Requirements

Unless a phase explicitly states otherwise, completion requires:

- relevant pytest tests pass;
- Ruff passes for affected backend code;
- frontend build passes if frontend code changed;
- manual behavioral verification is completed;
- key error paths introduced in the phase are checked;
- Codex reports modified files and verification performed;
- no Git commit has been created by Codex.

A phase is not complete solely because Codex reports that implementation succeeded.

---

# 6. External Integration Development Pattern

For each external data source, use the following pattern where practical:

```text
inspect live source once
        ↓
understand actual schema / behavior
        ↓
save representative fixture
        ↓
implement against fixture
        ↓
write deterministic tests
        ↓
connect vertical slice
        ↓
manually verify against live source
```

Normal automated tests should not depend on live external services.

Representative fixtures should be retained for repeatable development.

---

# 7. Architecture Evolution Rule

Do not construct all infrastructure before it is needed.

Use **just-in-time implementation**.

Examples:

- add SQLite/SQLAlchemy when persistence or caching becomes necessary;
- add image caching when camera functionality arrives;
- add structured AI contracts when AI functionality arrives;
- add transit-specific logic when the transit slice begins.

Do not pre-build speculative subsystems merely because they appear in the final technical design.

---

# 8. Planned Phase Overview

The initial roadmap is:

```text
Phase 0   Integration Readiness
Phase 1   Application Shell + Map
Phase 2   Journey Input + Geocoding
Phase 3   Drive Route Candidates + Selection
Phase 4   Road Ahead Vertical Slice
Phase 5   Regional Road Context
Phase 6   Current + Near-Term Weather
Phase 7   Vancouver Camera Pipeline
Phase 8   Camera AI Analysis
Phase 9   Journey Relevance + Timeline Refinement
Phase 10  Transit Mode
Phase 11  AI Journey Briefing
Phase 12  Integration Hardening
Phase 13  Presentation + Demo Polish
```

Phases 0–6 are relatively firmly defined.

Later phases may be adjusted based on discoveries from the working application.

---

# 9. Phase 0 — Integration Readiness

## Objective

Resolve external-service uncertainty before substantial implementation begins.

This phase should verify that the planned services are actually usable and that required credentials or access methods are available.

## Integrations to Verify

At minimum:

- MapTiler
- openrouteservice
- Vancouver webcams
- Vancouver Road Ahead
- DriveBC Open511
- DriveBC cameras
- ECCC GeoMet / SWOB
- OpenWeatherMap
- TransLink GTFS-Realtime
- OpenRouter

## Required Work

For each relevant source:

- identify actual endpoint(s);
- confirm whether authentication is required;
- verify available API key;
- make one successful request where possible;
- inspect representative response structure;
- note update/freshness behavior;
- identify obvious rate-limit or usage constraints;
- record any source-specific implementation concerns.

Create or update:

```text
.env.example
```

with required configuration names.

Ensure:

```text
.env
```

is Git-ignored.

Save representative source responses as fixtures where appropriate.

## Important Questions to Resolve

Examples:

- Does Road Ahead return usable point/line geometry?
- What exact Open511 event geometry is available?
- How are Vancouver webcam metadata and image URLs structured?
- Are camera capture timestamps exposed?
- Which ECCC/SWOB endpoint is easiest for current local observations?
- What useful near-term granularity is available from OpenWeatherMap?
- What TransLink realtime feeds are accessible?
- Does ORS reliably provide route alternatives?
- Which OpenRouter vision/text models appear viable?

## Acceptance Criteria

- required API credentials are known or confirmed unnecessary;
- every core source has an identified access method;
- at least one representative response has been inspected for each accessible source;
- fixtures exist for sources where implementation will shortly begin;
- no major integration blocker remains undiscovered.

## Non-Goals

Do not build the full application.

This phase exists to reduce uncertainty.

---

# 10. Phase 1 — Application Shell + Map

## Objective

Create the basic RouteLens application and establish the polished desktop visual foundation.

The phase should end with a real interactive map visible inside the intended desktop layout.

## Backend

Create minimal FastAPI application.

Include:

```text
GET /api/health
```

No major domain logic yet.

## Frontend

Create:

- React
- Vite
- TypeScript
- Tailwind
- MapLibre
- Framer Motion
- Lucide

Build the primary desktop shell:

```text
top journey controls area
left map area
right intelligence panel area
```

Integrate MapTiler dark basemap.

## Initial Visual Standard

The UI should already establish:

- dark city-intelligence aesthetic;
- correct map/panel proportions;
- clean typography;
- elevated panel styling;
- basic loading/status design language.

Do not defer all styling until the end.

However, deep polish is not required yet.

## Acceptance Criteria

- frontend starts locally;
- FastAPI starts locally;
- frontend can reach backend health endpoint;
- MapLibre renders MapTiler basemap;
- full desktop shell is visible;
- right panel placeholder exists;
- project runs without unnecessary infrastructure.

## Verification

- backend tests for health endpoint;
- Ruff;
- frontend build;
- manually verify map interaction and layout.

---

# 11. Phase 2 — Journey Input + Geocoding

## Objective

Allow the user to enter/select a real origin and Vancouver destination.

This phase establishes the first real user interaction.

## Backend / Integration

Add MapTiler geocoding/autocomplete support using the chosen architecture.

Normalize selected places into:

```text
Location
```

Implement destination support validation.

The backend must reject unsupported destinations outside the City of Vancouver.

## Frontend

Implement:

```text
JourneyInput
AddressAutocomplete
ModeSelector
Analyze/continue control
```

For this phase:

- Drive can be the primary active mode;
- Transit can be visible but may remain incomplete.

Origin must be manually selected.

No current-location permission.

## UX

The user should:

1. type an origin;
2. select suggestion;
3. type destination;
4. select suggestion;
5. receive clear validation if destination is unsupported.

## Acceptance Criteria

- origin autocomplete works;
- destination autocomplete works;
- selected places contain canonical coordinates;
- Vancouver destination passes validation;
- outside-Vancouver destination is rejected clearly;
- selected origin/destination persist in frontend state.

## Verification

- location normalization tests;
- destination validation tests;
- mocked geocoder tests where useful;
- Ruff;
- frontend build;
- manual test with several Metro Vancouver origins and Vancouver/non-Vancouver destinations.

---

# 12. Phase 3 — Drive Route Candidates + Selection

## Objective

Turn the selected origin/destination into visible approximate driving-route context.

At the end of this phase, RouteLens should support the basic:

> enter trip → see plausible routes → select closest route

workflow.

## Backend

Add openrouteservice integration.

Normalize results into:

```text
RouteCandidate
SelectedRoute
```

Return:

- up to three candidates where available;
- one route when alternatives are unavailable.

## Frontend

Implement:

```text
RouteSelector
RouteLayer
```

Display:

- candidate routes;
- selected route;
- clearly muted alternatives.

Ask the user:

> Which route most closely matches your planned trip?

The UI must not imply that RouteLens is recommending the optimal route.

## Acceptance Criteria

- route request works for real Metro Vancouver → Vancouver journeys;
- at least one route is returned for supported test cases;
- alternatives appear where ORS provides them;
- user can select a route;
- selected route becomes visually prominent;
- selected route is represented in application state as `SelectedRoute`.

## Verification

Test representative routes such as:

- New Westminster → downtown Vancouver
- Burnaby → UBC area
- Richmond → downtown Vancouver
- North Vancouver → Vancouver
- Surrey → Vancouver

Exact Google Maps reproduction is not required.

---

# 13. Phase 4 — Vancouver Road Ahead Vertical Slice

## Objective

Build the first complete telemetry slice.

This phase proves the central RouteLens architecture:

```text
live city source
→ adapter
→ normalization
→ geospatial relevance
→ API
→ map
→ journey interpretation
```

## Backend

Implement:

```text
vancouver_road_ahead.py
```

Add normalized:

```text
CityEvent
```

Implement initial Shapely route relevance:

- convert selected route to geometry;
- create route buffer;
- include relevant construction/closure events;
- exclude clearly unrelated events.

Introduce basic source status/error isolation.

## API

Begin or extend:

```text
POST /api/trips/analyze
```

For now, the analysis may contain primarily Road Ahead evidence.

## Frontend

Add Road Ahead events to:

- MapPanel
- initial Along Your Route section

Relevant events should appear visibly on/near the route.

## Placeholder Journey Summary

A deterministic summary may be used.

Example:

```text
2 construction events found near the selected journey.
```

Do not add final LLM briefing yet.

## Acceptance Criteria

Given a selected drive route:

- Road Ahead is fetched;
- payload is normalized;
- relevant events are filtered;
- unrelated distant events are excluded;
- relevant construction appears on map;
- route panel displays useful event information;
- Road Ahead failure does not crash the whole analysis.

## Tests

Include fixtures covering:

- typical valid event;
- empty response;
- malformed/partial event;
- route-near event;
- distant event.

This is the first major architectural proof point.

---

# 14. Phase 5 — Regional Road Context

## Objective

Extend road awareness beyond Vancouver municipal construction.

Add:

- DriveBC Open511
- DriveBC cameras

This creates useful journey context for approaches into Vancouver.

## Backend

Implement:

```text
drivebc_open511.py
drivebc_cameras.py
```

Open511 events normalize primarily into:

```text
CityEvent
```

DriveBC camera metadata normalize into:

```text
Camera
```

Reuse existing geospatial relevance services rather than introducing a separate relevance system.

## Relevance

DriveBC data should be surfaced primarily where useful for:

- highways;
- bridges;
- major approach corridors;
- road events near selected route.

Do not load/display irrelevant province-wide telemetry.

## Frontend

Add:

- regional road events;
- relevant DriveBC camera markers.

The primary destination camera feature is not implemented yet.

DriveBC camera imagery may be viewable in a basic form if easy, but dedicated camera UX belongs to a later phase.

## Acceptance Criteria

- relevant Open511 events appear;
- distant events are excluded from automated findings;
- useful DriveBC cameras appear along appropriate approach corridors;
- Road Ahead and Open511 coexist through common normalized models;
- failure of either source remains isolated.

---

# 15. Phase 6 — Current + Near-Term Weather

## Objective

Add meaningful destination weather context while preserving the distinction between observed and forecast conditions.

This phase combines:

- ECCC SWOB
- OpenWeatherMap

because their value is strongest when presented together.

## Backend

Implement:

```text
eccc_swob.py
openweathermap.py
```

Normalize into:

```text
WeatherObservation
WeatherForecast
```

Select an appropriate current observation near the destination.

Extract only useful product fields.

Retrieve near-term forecast information focused roughly on:

```text
30 minutes – 2 hours
```

## Frontend

Add destination weather section showing clearly separate:

```text
Observed
Forecast
```

Examples:

```text
Observed 8 min ago
11°C · light wind · recent precipitation

Near-term
Light rain possible within the next hour
```

## Acceptance Criteria

- nearest useful current observation is selected;
- forecast data is retrieved;
- observation and forecast remain structurally distinct;
- timestamps/freshness are visible;
- either weather source may fail independently;
- journey remains usable when one is unavailable.

---

# 16. Phase 7 — Vancouver Camera Pipeline

## Objective

Implement the signature visual-data pipeline without AI analysis yet.

This phase introduces:

- Vancouver camera adapter;
- destination camera ranking;
- backend image proxy;
- temporary latest-image cache;
- dedicated camera UX;
- SQLite/SQLAlchemy where needed.

## Backend

Implement:

```text
vancouver_cameras.py
```

Normalize cameras into:

```text
Camera
```

Implement destination-camera ranking based on:

1. distance;
2. freshness;
3. source preference if useful.

Select:

- one primary camera;
- a small number of alternatives.

## Persistence

Introduce SQLite + SQLAlchemy as needed for:

- source cache;
- camera metadata;
- cached image metadata.

Do not build unrelated persistence infrastructure.

## Image Proxy

Implement:

```text
GET /api/cameras/{id}/image
```

Behavior:

```text
fresh cached image?
     ↓
yes → return cache

no
 ↓
fetch upstream
 ↓
overwrite camera cache
 ↓
return same frame
```

No historical archive.

## Frontend

Implement:

```text
DestinationConditions
CameraDetail
```

The Journey Overview should prominently display:

- primary camera image;
- location/name;
- image freshness;
- alternative thumbnails.

Map camera markers should be interactive.

Clicking a camera should transition the right panel into CameraDetail.

Back returns to JourneyOverview.

## Acceptance Criteria

- Vancouver cameras load;
- primary destination camera is automatically selected;
- alternatives are displayed;
- image proxy works;
- repeated fresh requests reuse cache;
- stale cache is refreshed;
- no historical images are retained;
- map camera click opens CameraDetail;
- Back restores JourneyOverview.

---

# 17. Phase 8 — Camera AI Analysis

## Objective

Add multimodal interpretation to the camera pipeline.

This is the first major AI capability.

## Backend

Add OpenRouter vision integration.

All calls originate from FastAPI.

Input:

- the exact cached image used by the UI;
- constrained structured-analysis prompt.

Output:

```text
CameraObservation
```

validated through Pydantic.

## Automatic Behavior

The primary destination camera should be analyzed automatically during journey analysis.

Alternative cameras should be analyzed only when explicitly selected, unless a fresh cached analysis already exists.

## Camera Analysis Cache

Reuse analysis while associated image remains fresh.

A new camera frame invalidates the old current-frame analysis.

## Structured Fields

At minimum:

- precipitation visible
- precipitation type
- road surface
- traffic level
- visibility
- confidence
- concise note

## Failure Behavior

If AI analysis fails:

- camera image remains available;
- other journey telemetry remains available;
- UI shows camera-analysis unavailable;
- invalid LLM output does not break journey analysis.

## Acceptance Criteria

- primary camera analysis occurs automatically;
- structured output validates;
- same fresh frame does not trigger unnecessary repeat AI calls;
- alternate camera can trigger analysis on demand;
- malformed AI output fails safely;
- frontend displays camera observations clearly.

---

# 18. Phase 9 — Journey Relevance + Timeline Refinement

## Objective

Turn the growing set of telemetry into a coherent deterministic journey model before adding the final LLM briefing.

This phase should refine:

- relevance ranking;
- event importance;
- event density;
- timeline ordering;
- Journey Status foundation.

## Backend

Combine current:

- construction;
- road incidents;
- cameras;
- camera observations;
- observed weather;
- forecast weather.

Refine deterministic scoring using:

- distance;
- route intersection;
- destination proximity;
- freshness;
- severity;
- source type.

Limit automated important findings to approximately:

```text
3–6
```

Build normalized timeline events.

## Timeline

Order relevant events approximately along the journey.

Example:

```text
START
  │
  ● construction
  │
  ● road incident
  │
  ● visual condition
  │
DESTINATION
  ● rain likely
```

Do not ask the LLM to invent this ordering.

## Frontend

Implement final intended:

```text
JourneyTimeline
JourneyStatus
AlongYourRoute
```

The map may still expose more telemetry than the timeline.

## Acceptance Criteria

- route evidence is ranked deterministically;
- timeline contains only important events;
- irrelevant map telemetry does not automatically become a highlighted insight;
- no more than roughly 3–6 important findings appear in the automated experience;
- destination conditions receive appropriate priority.

---

# 19. Phase 10 — Transit Mode

## Objective

Add useful transit journey analysis while deliberately avoiding full transit navigation.

Drive behavior should already be stable before this phase.

## Backend

Implement TransLink GTFS-Realtime integration.

Focus on:

1. service alerts;
2. trip updates / delays;
3. other useful realtime disruption information.

Normalize into:

```text
TransitAlert
```

## Transit Corridor

Implement a broad approximate journey corridor.

The first version may use:

- direct origin/destination geometry;
- broadened relevance buffer;
- experimentally useful approximate path if justified.

Do not imply exact bus/SkyTrain routing.

## Relevance

Transit mode may use wider relevance than drive mode.

Test whether useful service information can be associated with:

- journey area;
- affected routes;
- affected stops;
- destination context.

The exact heuristic may be adjusted based on real testing.

## Frontend

Transit mode should:

- retain map/camera/weather information;
- add transit alerts;
- clearly identify transit-related disruptions;
- avoid pretending RouteLens knows the authoritative itinerary.

## Acceptance Criteria

- selecting Transit changes analysis behavior;
- TransLink data is queried only when appropriate;
- relevant alerts appear;
- generic journey corridor is visible;
- road/weather/camera information still functions;
- transit failure is isolated.

---

# 20. Phase 11 — AI Journey Briefing

## Objective

Add the final text-model interpretation layer after the underlying structured evidence is stable.

## Backend

Create compact evidence payload containing only relevant information.

Possible input:

```text
Trip
SelectedRoute
important CityEvents
CameraObservation
WeatherObservation
WeatherForecast
TransitAlerts
JourneyTimeline
```

Do not send raw external API payloads.

Call OpenRouter text model.

Require structured response:

```text
JourneyBriefing
```

with:

```text
status
summary
highlights[]
recommendation
```

Validate with Pydantic.

## Behavioral Requirements

The model must:

- only use supplied evidence;
- remain concise;
- avoid invented disruptions;
- allow “journey looks clear” outcomes;
- avoid unnecessary urgency;
- keep highlights aligned with deterministic findings.

## Frontend

Replace any temporary deterministic summary with final:

```text
RouteLens AI Briefing
```

while maintaining structured UI control over:

- status;
- summary;
- highlights;
- recommendation.

## Acceptance Criteria

- valid structured briefing produced;
- malformed output fails safely;
- clear journeys receive appropriately calm output;
- findings correspond to actual supplied evidence;
- briefing does not become a wall of text.

---

# 21. Phase 12 — Integration Hardening

## Objective

Improve reliability after all major product capabilities exist.

This is not a new-feature phase.

## Areas to Review

### Partial Failure

Test combinations such as:

```text
Road Ahead unavailable
TransLink unavailable
camera image unavailable
camera AI unavailable
forecast unavailable
```

The remaining application should still work where possible.

### Cache Behavior

Verify:

- expiry;
- stale handling;
- repeated requests;
- raw source cache;
- camera-image cache;
- camera-analysis cache.

### Timeouts / Retries

Confirm:

- explicit source timeouts;
- minimal retry behavior;
- slow services do not stall indefinitely.

### Logging

Confirm useful logging for:

- fetch success/failure;
- cache hits;
- LLM latency/errors;
- total analysis timing.

### Empty States

Test:

- no construction;
- no incidents;
- no nearby camera;
- no transit alerts;
- clear weather;
- no significant findings.

### API Validation

Test malformed/unsupported input.

## Acceptance Criteria

- individual source failures remain isolated;
- useful source-status information reaches frontend;
- error states are understandable;
- no common failure path results in unnecessary full application failure;
- caches behave predictably.

---

# 22. Phase 13 — Presentation + Demo Polish

## Objective

Turn the functioning MVP into a presentation-ready product.

This phase is protected from feature creep.

Do not add major new integrations.

## Loading UX

Improve analysis-state feedback.

Example:

```text
Analyzing journey…

✓ route loaded
✓ construction checked
✓ road events checked
✓ cameras checked
✓ weather checked
✓ transit checked
✓ generating briefing
```

Exact implementation may differ.

## Freshness UI

Ensure clear labels such as:

```text
Camera · captured 4m ago
ECCC · observed 9m ago
DriveBC · updated 3m ago
Road Ahead · updated 42m ago
```

## Failure UX

Ensure partial errors are visible without overwhelming the interface.

## Motion

Refine:

- route reveal;
- card entrance;
- CameraDetail transition;
- Live indicator;
- small loading states.

Avoid decorative excess.

## Visual Cleanup

Review:

- spacing;
- hierarchy;
- camera prominence;
- marker design;
- route contrast;
- typography;
- empty states;
- panel balance;
- overflow/scroll behavior.

## Demo Routes

Identify a small set of reliable Vancouver demo journeys that exercise different capabilities.

Examples might include:

- regional drive into downtown;
- bridge/highway approach;
- journey with useful Vancouver cameras;
- transit journey with realistic TransLink context.

Exact routes should be selected based on live conditions available near presentation time.

## Demo Smoke Test

Perform end-to-end rehearsal:

```text
fresh application start
→ input journey
→ route selection
→ analysis
→ camera
→ road telemetry
→ weather
→ timeline
→ briefing
→ alternative camera
```

Verify no developer-only setup is needed during the presentation.

## Acceptance Criteria

- primary demo journey works reliably;
- loading states are clear;
- errors degrade gracefully;
- no major visual rough edges remain;
- final experience communicates the RouteLens concept within seconds;
- no new major feature is introduced during this phase.

---

# 23. Expected Evolution of Later Phases

Phases 0–6 are deliberately defined more tightly.

Phases 7 onward may change based on:

- actual API behavior;
- quality of camera metadata;
- camera-image availability;
- LLM model performance;
- observed UI interaction;
- transit relevance testing;
- runtime latency.

Changes should preserve the product requirements unless implementation evidence shows that a requirement itself needs reconsideration.

If architecture changes materially:

> update `docs/technical-design.md`

If product behavior changes materially:

> update `docs/prd.md`

If only build sequence changes:

> update this implementation plan.

---

# 24. Development Artifacts Created From This Plan

This document is not intended to be Codex's complete working context.

Before implementation begins, derive the project SDD harness.

Recommended root files:

```text
AGENTS.md
APP_SPEC.md
BUILD_PLAN.md
PROJECT_STATE.md
```

---

# 25. Relationship to APP_SPEC.md

`APP_SPEC.md` should become the concise Codex-facing implementation specification.

It should derive relevant truths from:

```text
docs/prd.md
+
docs/technical-design.md
```

but omit unnecessary product rationale and discussion history.

It should focus on:

- system invariants;
- major architecture;
- expected behavior;
- key model boundaries;
- non-negotiable constraints.

---

# 26. Relationship to BUILD_PLAN.md

`BUILD_PLAN.md` should convert the current phase from this roadmap into an operational coding task.

For example:

```text
docs/implementation-plan.md

Phase 4
Vancouver Road Ahead vertical slice
```

becomes something closer to:

```text
BUILD_PLAN.md

CURRENT PHASE:
Road Ahead Vertical Slice

Objective:
...

Files/modules likely involved:
...

Requirements:
...

Non-goals:
...

Acceptance criteria:
...

Verification:
...
```

The build plan may evolve more frequently than this implementation roadmap.

---

# 27. Relationship to PROJECT_STATE.md

`PROJECT_STATE.md` tracks reality.

It should answer:

- which phase has been completed;
- which phase is current;
- what functionality actually exists;
- important implementation decisions discovered during development;
- known issues;
- deferred work;
- verification status;
- next recommended action.

Do not turn `implementation-plan.md` into a progress log.

---

# 28. Relationship to AGENTS.md

`AGENTS.md` should define project-wide coding-agent behavior.

Likely rules include:

- inspect existing code before changing it;
- respect documented architecture;
- remain within current phase scope;
- avoid unrelated refactoring;
- use existing patterns where possible;
- run required verification;
- report uncertainty;
- do not invent missing requirements;
- never commit or push;
- stop and report major blockers rather than redesigning the product autonomously.

---

# 29. Planning-Agent Role During Implementation

The planning agent remains active throughout development.

For each phase:

```text
docs/
+
SDD harness
+
PROJECT_STATE.md
        ↓
planning agent
        ↓
bounded Codex prompt
```

The planning agent should:

- understand the current phase;
- identify only relevant architecture/context;
- produce a tightly scoped implementation prompt;
- define acceptance criteria;
- define verification expectations;
- prevent accidental scope expansion.

The planning agent does not need to redesign RouteLens before every phase.

---

# 30. Codex Role During Implementation

Codex is responsible primarily for bounded implementation.

For a given phase, Codex should:

1. inspect relevant repository state;
2. read applicable project instructions;
3. understand the current bounded task;
4. implement only the required capability;
5. use available feedback loops while working;
6. add/update tests;
7. run required verification;
8. report changes and unresolved issues;
9. leave Git history untouched.

Codex should not autonomously decide to implement future phases.

---

# 31. Human Role During Implementation

The human remains responsible for:

- accepting/rejecting phase output;
- architectural judgment;
- product judgment;
- reviewing significant implementation choices;
- behavioral QA;
- deciding whether discovered issues require plan/design changes;
- Git commits;
- deciding when to advance to the next phase.

Manual code review should prioritize:

- source adapters;
- data models;
- geospatial logic;
- caching;
- AI contracts/prompts;
- error handling;
- dependencies;
- API key handling.

Ordinary generated UI/CSS and trivial helpers may receive lighter review if behavior is correct.

---

# 32. Implementation Mental Model

The development path should remain:

```text
VERIFY DEPENDENCIES
        ↓
CREATE VISUAL SHELL
        ↓
ENTER A REAL JOURNEY
        ↓
DRAW A REAL ROUTE
        ↓
ADD ONE REAL CITY SIGNAL
        ↓
ADD MORE DETERMINISTIC SIGNALS
        ↓
ADD CAMERAS
        ↓
ADD MULTIMODAL AI
        ↓
TURN SIGNALS INTO A JOURNEY MODEL
        ↓
ADD TRANSIT
        ↓
ADD FINAL AI SYNTHESIS
        ↓
HARDEN
        ↓
POLISH
```

At every step, RouteLens should become more visibly real.

The implementation should avoid long periods where large amounts of infrastructure exist without a user-observable feature.

---

# 33. Final Implementation Principle

The purpose of this plan is not to predict every implementation detail perfectly.

It is to provide a disciplined path toward a working RouteLens MVP while allowing real application behavior to inform later decisions.

The guiding rule is:

> **Build the smallest real slice, verify it against reality, preserve what works, and use what is learned to shape the next slice.**

The roadmap should remain stable enough to guide development while flexible enough to respond to genuine implementation evidence.
