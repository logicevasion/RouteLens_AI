# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 4 — Vancouver Road Ahead Vertical Slice
**Status:** Planned — authorized for implementation through separately approved bounded assignments; not yet verified
**Source:** `docs/implementation-plan.md`, Phase 4
**Previous phase:** Phase 3 — Drive Route Candidates + Selection, accepted by the human developer on 2026-10-10

### Objective

Implement the first complete real-world journey-intelligence vertical slice using the City of Vancouver's Road Ahead datasets.

Phase 4 establishes:

**Selected driving route → real municipal road events → deterministic route relevance → useful journey context.**

Integrate both:

- Road Ahead — Current Road Closures;
- Road Ahead — Projects Under Construction.

The phase must deliver:

- reliable access to both official datasets;
- validated approximately 24-hour structured-data caching;
- conservative normalization into the approved `CityEvent` model;
- preservation of complete event geometry and provenance;
- projected, metre-based route-relevance calculations;
- direct-overlap detection and nearby supplemental event selection;
- selective deterministic enrichment from official Road Ahead detail pages;
- an initial `POST /api/trips/analyze` workflow;
- display of relevant Road Ahead information on MapLibre;
- an initial Along Your Route intelligence section;
- deterministic summaries based on actual matched events;
- clear source freshness, partial-failure, and error behavior.

This is the first major architectural proof of the RouteLens intelligence pipeline.

It does not implement DriveBC Open511, weather, cameras, transit intelligence, or AI-generated briefings.

---

## 2. Execution Scope

Phase 4 will be implemented through four separately authorized Codex assignments.

Each assignment receives its own bounded implementation prompt.

Do not interpret this build plan as authorization to implement every workstream at once.

Preserve the accepted Phase 1–3 application.

### Assignment 4A — Road Ahead Ingestion, Normalization, and Cache

Implement:

- access to both Road Ahead structured datasets;
- normalization into `CityEvent`;
- geometry and source metadata preservation;
- validated approximately 24-hour caching;
- atomic cache replacement and stale fallback;
- focused deterministic tests;
- targeted live source verification.

This assignment establishes a reliable source-data foundation.

Do not implement route matching, detail-page enrichment, or frontend telemetry presentation.

### Assignment 4B — Geospatial Route Relevance

Implement:

- conversion of route/event geometries into an appropriate projected coordinate system;
- direct route-intersection detection;
- nearby supplemental event matching;
- deterministic prioritization;
- the rule preserving all direct overlaps before supplemental limits;
- meaningful geospatial regression tests.

Do not implement external detail-page enrichment or frontend presentation.

### Assignment 4C — Detail Enrichment and Analysis API

Implement:

- selective Road Ahead detail-page retrieval;
- deterministic extraction of useful restrictions and scheduling information;
- enrichment caching and safe fallback;
- initial Road Ahead trip-analysis API;
- source freshness and failure-status reporting;
- deterministic event-count or evidence summaries.

Do not implement LLM-generated analysis.

### Assignment 4D — Frontend Integration and Acceptance

Implement:

- Analyze Journey activation when a valid route is explicitly selected;
- integration with the Road Ahead analysis API;
- relevant event geometry/markers on MapLibre;
- the initial Along Your Route panel;
- direct-overlap versus nearby-context presentation;
- loading, stale-source, empty, and failure states;
- final end-to-end verification and Phase 4 acceptance assessment.

These assignment boundaries are organizational.

Avoid creating infrastructure or abstractions merely because separate assignments exist.

---

## 3. Established Implementation Baseline

### 3.1 Accepted Application Foundation

Phases 1–3 established:

- FastAPI backend and `/api/health`;
- React/Vite/TypeScript frontend;
- MapLibre with MapTiler dark basemap;
- fixed approximately 65/35 desktop shell;
- Vite `/api` proxy;
- canonical `Location` selection;
- MapTiler geocoding/autocomplete;
- deterministic City of Vancouver destination validation;
- ORS driving-route candidate API;
- normalized route geometries;
- explicit user-controlled route selection;
- correct selected-route invalidation;
- route rendering, candidate summaries, and viewport fitting;
- frontend asynchronous request safeguards;
- provider-credential boundaries;
- backend pytest, Ruff, and frontend build verification.

Preserve this behavior.

Do not rebuild the route-selection system.

### 3.2 Accepted Route Contract

The existing routing API returns candidates with:

- `id`;
- GeoJSON `LineString` geometry;
- `distance_meters`;
- `duration_seconds`;
- optional `label`.

Frontend route identity is request-scoped.

Phase 4 must operate on the explicitly selected route belonging to the current canonical origin/destination pair.

Do not automatically choose an alternative.

Do not analyze stale geometry after the user edits or changes journey inputs.

### 3.3 Road Ahead Research

Planning and Phase 0 investigated:

- Current Road Closures;
- Projects Under Construction;
- official dataset schemas;
- full event geometries;
- incomplete optional fields;
- detail-page enrichment opportunities;
- approximately 24-hour caching.

Review relevant source evidence under:

- `docs/technical-design.md`;
- `docs/implementation-plan.md`;
- `docs/data-licensing-and-commercialization.md`;
- existing `docs/integration-notes/`;
- existing `fixtures/`;
- `PROJECT_STATE.md`.

Use the actual existing fixture names and records discovered in the repository.

Do not assume additional fixtures or endpoints exist without inspection.

Do not repeat broad provider research.

Targeted live verification of the implemented integration is required.

---

## 4. Road Ahead Dataset Integration

Integrate both approved official datasets.

Use a focused adapter consistent with the approved technical design.

The implementation roadmap identifies `road_ahead.py` as an expected module.

### Required behavior

- Fetch the two source datasets.
- Validate the expected response structure.
- Handle missing optional attributes.
- Normalize records conservatively.
- Preserve complete geographic geometry.
- Preserve source provenance.
- Handle upstream failures without crashing the application.
- Avoid re-fetching entire datasets for every selected journey.

### Source-specific rules

Do not assume:

- `street` is populated;
- `project` is complete;
- `location` is complete;
- `comp_date` establishes the authoritative final applicability date;
- every record contains usable detail-page information;
- every geometry has the same GeoJSON type.

Do not fabricate missing fields.

Do not convert unknown schedule or restriction details into definitive claims.

### Dataset completeness

A structurally valid provider response must not automatically be assumed complete.

Use source-specific evidence and validation rules appropriate to the actual feeds.

Do not overwrite a known valid cache with malformed or demonstrably incomplete content.

If a source introduces a material schema change, report it.

---

## 5. CityEvent Normalization

Normalize Road Ahead records into the approved `CityEvent` model.

Consult `APP_SPEC.md` and `docs/technical-design.md` for the authoritative contract.

Preserve:

- source identifier;
- source dataset/type;
- source URL;
- full geometry;
- representative geographic point;
- project or location description;
- available source timestamps;
- available status/schedule metadata;
- provenance needed for user-facing attribution.

Do not establish incompatible duplicate models.

### Geometry requirements

Support actual provider structures including:

- `LineString`;
- `MultiLineString`;
- `GeometryCollection`.

Preserve legitimate geographic components within these structures.

Handle missing, null, malformed, and unsupported geometry safely.

Do not silently replace unknown line geometry with an invented point.

A representative point is supplemental metadata, not a substitute for complete geographic geometry.

### Coordinate handling

GeoJSON geographic coordinates use:

`[longitude, latitude]`

Maintain the established RouteLens coordinate conventions.

Validate coordinate ranges and geometry usability.

Do not reverse axes.

### Data integrity

Retain meaningful provider metadata while avoiding unnecessary raw-response fields in the permanent application contract.

Distinct source records must not be aggressively merged solely because they have similar names or nearby geometry.

---

## 6. Validated Structured-Data Cache

Implement the approved approximately 24-hour Road Ahead cache.

### Required lifecycle

1. Check for an existing valid cached dataset.
2. Use it when fresh.
3. Attempt refresh when stale or missing.
4. Validate the newly downloaded response.
5. Replace the previous cache only after successful validation.
6. Retain the last valid dataset when refresh fails.
7. Expose appropriate freshness/stale status.

Use safe atomic replacement where practical.

### Cache requirements

- Both source datasets must be accounted for.
- One dataset's failure should not unnecessarily invalidate the other.
- The cache must not be treated as fresh merely because a fetch was attempted.
- Incomplete writes must not corrupt the last valid cache.
- Failed refreshes must not silently erase usable previous data.
- Missing cache and failed retrieval must be reported appropriately.

Prefer simple local persistence appropriate for the MVP.

Do not introduce Redis, distributed caching, background workers, or database infrastructure without a demonstrated requirement.

### Freshness metadata

Expose meaningful timestamps and status, consistent with the approved `SourceStatus` model.

Distinguish:

- fresh source data;
- valid but stale cached data;
- unavailable data.

Do not invent a successful refresh timestamp.

No portal modification-date checker is required.

---

## 7. Geospatial Route Relevance

Use the explicitly selected route geometry to determine which Road Ahead events are relevant.

### Coordinate reference system

Use an appropriate projected CRS for metre-based calculations in Vancouver.

Do not apply metre-valued distance thresholds directly to unprojected longitude/latitude degrees.

Use Shapely and justified projection tools consistent with the existing technical design.

### Direct overlaps

Determine whether event geometry directly intersects or overlaps the selected route.

Preserve the distinction between geometric contact and actual traffic impact.

A route intersection is evidence of geographic relevance; it does not automatically prove a currently active full road closure.

### Nearby supplemental events

Identify geographically nearby events even when their geometry does not directly intersect the route.

Apply deterministic proximity calculations and reasonable selection/ranking rules.

The precise distance threshold should follow any value already established in the approved technical design.

If no exact numeric threshold is authorized, use a clearly documented, configurable MVP choice consistent with the approved design rather than presenting it as a locked historical decision.

### Mandatory prioritization rule

**All direct route overlaps must survive candidate limiting.**

Only nearby supplemental events may be subject to a supplemental candidate limit.

For example, if a journey has eight direct overlaps and the nearby-event limit is five:

- all eight direct overlaps remain;
- up to five additional nearby candidates may be included.

Never reduce direct overlaps merely to satisfy a combined event-count cap.

### Matching outputs

Preserve enough information to distinguish:

- direct overlap;
- nearby context;
- irrelevant/distant records.

Where distance is reported, use actual projected geometry calculations.

Do not infer event severity or traffic disruption from proximity alone.

---

## 8. Selective Detail-Page Enrichment

Enrich geographically relevant Road Ahead candidates using official source detail pages where available.

Do not crawl every event detail page during ordinary dataset ingestion.

### Extraction

Use deterministic HTML parsing.

Extract supported information such as:

- full event title/location;
- description;
- status;
- work schedule;
- operating hours;
- exceptions;
- closure or restriction details.

Preserve source links and extraction timestamps.

Do not use an LLM to parse raw event pages.

### Failure handling

When a detail page is unavailable or parsing fails:

- retain the base normalized dataset record;
- mark unavailable enrichment fields unknown;
- continue analysis;
- report meaningful enrichment limitations where useful.

Do not discard a geographically relevant event because its detail page failed.

### Enrichment caching

Cache enrichment by source/event identity.

Avoid repeatedly requesting the same page during one user session.

The approved technical design does not lock an exact enrichment TTL.

Choose a modest documented MVP cache policy based on observed source behavior, or escalate if a material product decision is required.

Do not create a historical webpage archive.

### Licensing

Preserve provenance and attribution.

The approved licensing assessment treats the core Road Ahead datasets as suitable open-data inputs.

Do not assume every separately delivered detail-page element is automatically covered by the same reuse rights.

Avoid bulk republication of source webpage contents.

---

## 9. Initial Journey Analysis API

Implement or extend:

`POST /api/trips/analyze`

### Request context

The analysis must receive or reliably identify the explicitly selected journey route and the canonical locations required by the approved trip model.

Consult the approved `Trip`, `SelectedRoute`, and related model contracts before choosing request fields.

Do not invent database-backed trip identity.

Do not silently analyze an unselected candidate.

### Initial analysis behavior

The Phase 4 analysis may contain Road Ahead information only.

Required flow:

1. Validate incoming journey context.
2. Obtain the available Road Ahead datasets.
3. Normalize source records.
4. Determine route-relevant events.
5. Apply direct-overlap and nearby-supplemental selection rules.
6. Enrich relevant candidates where supported.
7. Produce application-owned structured results.
8. Return clear source availability/freshness status.

### Response

Preserve the approved analysis structure where defined.

Include sufficient information for:

- event identities;
- event source/dataset;
- descriptions;
- relevant geometry;
- source links;
- direct versus nearby classification;
- source freshness;
- optional enrichment;
- deterministic summary text.

Do not expose raw provider structures as the permanent application contract.

### Failure behavior

The analysis must handle:

- no matching road events;
- one unavailable Road Ahead dataset;
- both datasets unavailable;
- stale validated cached data;
- enrichment failure;
- invalid route geometry;
- malformed source responses;
- upstream timeouts.

A provider failure must not be represented as a successful finding of zero road events.

Keep errors and partial results understandable.

---

## 10. Frontend — Analyze Journey

Activate the existing Analyze Journey action for the initial Road Ahead analysis.

### Enablement

Enable Analyze Journey only after:

- origin and destination remain valid canonical selections;
- destination validation succeeded;
- a route candidate has been explicitly selected;
- no conflicting analysis request is active.

The action must remain unavailable if the selected route becomes invalid.

### User interaction

On activation:

1. Use the current canonical journey and selected route.
2. Call the approved analysis API.
3. Display loading/progress feedback.
4. Show actual Road Ahead findings.
5. Present source freshness or partial-failure status.
6. Preserve route selection and map interaction.

Do not trigger analysis automatically merely because a route is selected.

### Invalidation

Changing origin, destination, route candidates, or selected route must invalidate obsolete analysis.

Stale asynchronous responses must not restore findings from an earlier journey.

Use appropriate abort and request-identity safeguards, consistent with Phase 2–3 patterns.

---

## 11. Frontend — MapLibre Road Ahead Overlay

Display relevant Road Ahead events on the existing map.

### Requirements

- Use actual normalized event geometry or justified representative markers.
- Preserve existing route rendering.
- Keep the selected route identifiable.
- Visually distinguish Road Ahead events from route alternatives.
- Support direct-overlap versus nearby-context identification where practical.
- Preserve map controls, attribution, fitting, and resizing.
- Clear obsolete event overlays when analysis is invalidated.

Do not recreate the MapLibre instance whenever findings change.

### Presentation

Prefer a restrained layer/marker system consistent with the approved dark UI.

Do not create excessive visual clutter.

Use source-derived labels.

Do not imply that a plotted record proves active disruption at the present moment unless its source data supports that conclusion.

Do not add DriveBC, weather, transit, or camera overlays.

---

## 12. Frontend — Along Your Route

Add the initial Road Ahead intelligence section within the existing right-side panel.

### Information

Display useful data such as:

- Road Ahead event description;
- closure versus construction dataset;
- direct-overlap or nearby-context classification;
- geographic proximity when meaningful;
- supported schedule/restriction details;
- official source link;
- source timestamp/freshness status.

Clearly distinguish observations from interpretations.

### Summary

A deterministic summary may report actual counts, for example:

"3 Road Ahead events intersect this route. 1 additional nearby construction project was found."

Generate counts from actual matching results.

Do not fabricate events or traffic impact.

### Empty and failure states

Distinguish:

- no relevant events identified from available data;
- data loading;
- stale data;
- partial source failure;
- unavailable data;
- analysis failure.

Do not display "no road issues" merely because the source request failed.

### Existing placeholders

Preserve honest placeholders for:

- DriveBC;
- weather;
- cameras;
- transit;
- AI briefings.

Do not imply those capabilities have been implemented.

---

## 13. Source Provenance and Honest Interpretation

Source provenance must remain intact from ingestion through UI presentation.

### Principles

- A municipal event record is not automatically proof of an active obstruction at the user's travel time.
- An intersection with the route is geographic evidence, not proof of severity.
- Missing schedule information remains unknown.
- `comp_date` alone must not establish event completion.
- Stale cached events must be identified as stale.
- An enrichment failure must not erase the underlying event.
- Different source events must not be incorrectly merged.

The MVP may use straightforward deterministic language.

No LLM inference is required in this phase.

---

## 14. Expected Scope and Artifacts

Potential changes include:

- `backend/app/road_ahead.py`;
- backend event and source-status models;
- focused cache logic;
- geospatial relevance helpers;
- detail-enrichment parser;
- journey analysis API;
- backend tests and sanitized fixtures;
- relevant frontend state and components;
- MapLibre road-event layers;
- limited styles;
- `README.md` when setup changes;
- `PROJECT_STATE.md`.

Follow existing architecture and file naming conventions.

These are anticipated areas, not a strict filesystem allowlist.

Avoid unnecessary generalized ingestion frameworks.

Do not add future data-source adapters or create speculative database schemas.

---

## 15. Non-Goals

Phase 4 must not implement:

- DriveBC Open511 integration;
- ECCC SWOB weather observations;
- OpenWeather integration;
- Vancouver webcam image ingestion;
- camera AI interpretation;
- OpenRouter text or vision analysis;
- final AI-generated journey briefing;
- TransLink Service Alerts;
- transit route selection or routing;
- live traffic speeds;
- traffic-adjusted ETA;
- route recommendation or optimization;
- turn-by-turn navigation;
- road-condition forecasting;
- historical municipal event analytics;
- complex multi-source deduplication;
- database-backed saved journeys;
- user accounts;
- background continuous monitoring;
- generalized geospatial data platforms;
- wholesale application redesign.

Do not add fabricated telemetry to make the interface appear complete.

---

## 16. Verification Requirements

Each assignment must perform the tests appropriate to its scope.

### Source integration

Verify:

- both official Road Ahead datasets are retrievable;
- live response structures match normalization assumptions;
- missing optional fields are handled;
- source IDs and links are preserved;
- LineString, MultiLineString, and GeometryCollection normalize safely.

### Cache

Verify:

- valid fresh cache reuse;
- stale refresh;
- successful validated replacement;
- rejected malformed refresh;
- atomic replacement behavior;
- stale fallback;
- cache-missing source failure;
- independent dataset failure handling;
- source-status accuracy.

### Geometry

Verify:

- proper projected CRS handling;
- correct longitude/latitude interpretation;
- direct overlap;
- nearby supplemental event;
- distant irrelevant event;
- mixed geometry types;
- geometry collections;
- all direct overlaps retained when exceeding the supplemental limit.

### Enrichment

Verify:

- supported detail-page information can be extracted;
- unavailable fields remain unknown;
- page failure preserves base event;
- parse failure preserves base event;
- enrichment cache avoids unnecessary repeated fetching.

### API

Verify:

- valid selected-route analysis requests;
- invalid route rejection;
- correctly normalized event results;
- direct/nearby classifications;
- empty findings;
- stale source status;
- partial source failure;
- useful deterministic summary.

### Frontend

Verify:

- Analyze Journey requires a selected valid route;
- analysis is user initiated;
- real Road Ahead findings appear;
- event geometry/markers display;
- the selected route remains visible;
- panel information matches the API;
- source links work;
- empty, loading, stale, and failure states are understandable;
- route changes invalidate earlier intelligence;
- stale analysis responses cannot restore obsolete findings.

### Regression

Verify:

- backend health;
- geocoding/autocomplete;
- destination validation;
- ORS routing;
- route selection and highlighting;
- route invalidation;
- MapLibre navigation and attribution;
- desktop shell layout;
- disabled future capabilities.

### Tooling and repository

Run:

- applicable backend pytest;
- Ruff;
- frontend TypeScript verification;
- frontend production build;
- `git diff --check`;
- Git status and scope inspection;
- credential and `.env` checks.

Normal automated tests must not depend on live external services.

Classify every reported check as Passed, Failed, or Not run.

---

## 17. Phase 4 Acceptance Criteria

Phase 4 is ready for human acceptance when:

- [ ] Both Road Ahead datasets are integrated.
- [ ] Live source access works.
- [ ] Normalized `CityEvent` records preserve source provenance.
- [ ] Full supported geometries normalize correctly.
- [ ] Missing optional fields remain unknown.
- [ ] The structured-data cache uses the approved approximately 24-hour policy.
- [ ] Valid cache reuse works.
- [ ] Cache replacement follows validation.
- [ ] Failed refresh preserves valid stale data.
- [ ] Stale source status is exposed.
- [ ] Route-relevance calculations use a suitable projected CRS.
- [ ] Direct route overlaps are detected.
- [ ] Nearby supplemental events are identified.
- [ ] Distant events are excluded from relevant results.
- [ ] All direct overlaps survive candidate limiting.
- [ ] Relevant detail pages are enriched where supported.
- [ ] Enrichment failures preserve base event records.
- [ ] Enrichment caching works.
- [ ] The initial trip-analysis API exists.
- [ ] Analysis uses the explicitly selected route.
- [ ] Results distinguish direct overlaps from nearby context.
- [ ] Zero relevant events are handled honestly.
- [ ] Partial Road Ahead failures degrade gracefully.
- [ ] Analyze Journey is enabled only for a valid selected journey.
- [ ] Analysis is initiated by user action.
- [ ] Relevant Road Ahead geometry/markers appear on MapLibre.
- [ ] The initial Along Your Route panel displays useful source-grounded information.
- [ ] Factual event counts and deterministic summaries are accurate.
- [ ] Source freshness and limitations are visible where appropriate.
- [ ] Changing journey context invalidates obsolete analysis.
- [ ] Stale responses cannot restore previous journey findings.
- [ ] Existing Phase 1–3 functionality remains working.
- [ ] No unrelated telemetry sources or LLM features are introduced.
- [ ] Relevant automated tests and build checks pass.
- [ ] Representative live end-to-end behavior is manually verified.
- [ ] No credentials are exposed.
- [ ] `PROJECT_STATE.md` records actual evidence and limitations.
- [ ] Codex provides the required completion report.
- [ ] Codex performs no staging, commit, push, or history modification.

These checks establish eligibility for human acceptance.

They do not constitute automatic acceptance.

---

## 18. Blockers and Escalation

Stop affected work and report when:

- official Road Ahead endpoints or response formats materially differ from approved evidence;
- a required source cannot be accessed;
- the actual `CityEvent` contract cannot represent meaningful source geometry;
- a source schema change prevents reliable normalization;
- downloaded data cannot be distinguished from malformed or incomplete content;
- safe cache replacement cannot be achieved within the existing architecture;
- the geospatial matching approach requires an unapproved fundamental design change;
- a significant product decision is needed about relevance thresholds or event interpretation;
- event detail-page behavior materially contradicts previous research;
- the analysis API would require incompatible changes to accepted journey contracts;
- a substantial new infrastructure dependency is required;
- existing geographic validation must be weakened;
- implementing the phase would require unauthorized later-phase capabilities;
- destructive or unrelated repository modifications appear necessary.

For each blocker, report:

- observed issue;
- affected requirement;
- available evidence;
- reasonable options.

Continue independent in-scope work where safe.

Routine parser changes, cache implementation details, projection plumbing, focused test corrections, UI styling, and limited API organization may be handled autonomously.

Do not silently redesign the product.

---

## 19. Phase Completion and Handoff

After each bounded assignment:

- Run applicable verification.
- Update `PROJECT_STATE.md` factually.
- Record real source behavior and meaningful discoveries.
- Preserve previously accepted functionality.
- Report changed files and dependencies.
- Record failures and limitations.
- Provide the standard completion report required by `AGENTS.md`.
- Leave Git history untouched.

Phase 4 remains in progress until the human developer reviews and accepts its full implementation.

After acceptance:

1. Record human acceptance in `PROJECT_STATE.md`.
2. Create the human-controlled Git checkpoint.
3. Prepare and approve the next phase's `BUILD_PLAN.md`.
4. Do not begin the next phase without separate authorization.

Codex must not stage, commit, push, merge, rebase, amend, tag, or rewrite Git history.

---

## 20. Next Phase

**Phase 5 — Regional Road Context: DriveBC Open511**

The next phase adds regional road-event information beyond Vancouver's municipal Road Ahead datasets.

Its planned responsibilities include:

- regional Open511 ingestion;
- pagination;
- short-lived regional caching;
- road-event normalization;
- journey-specific relevance;
- regional event map presentation.

Do not implement Phase 5 during Phase 4.

**Phase 5 work is not authorized by this document.**
