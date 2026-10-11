# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 5 — Regional Road Context: DriveBC Open511  
**Phase status:** Approved and in progress. Assignments 5A and 5B are accepted and committed. Assignment 5C is implemented and accepted by the human developer on 2026-10-11, pending its Git checkpoint. Assignment 5D has not started.
**Source:** `docs/implementation-plan.md`, Phase 5; `docs/technical-design.md`, DriveBC Open511 sections  
**Previous phase:** Phase 4 — Vancouver Road Ahead Vertical Slice, human accepted on 2026-10-11 and committed

### Objective

Extend RouteLens from Vancouver municipal Road Ahead evidence to **regional, source-attributed road incidents and advisories** through DriveBC Open511.

**Selected driving route + cached regional Open511 events → deterministic journey relevance → combined road context, with wider regional map visibility.**

The phase must deliver:

- evidence-backed access to DriveBC's supported Open511 event interface;
- a justified regional fetch envelope, all active event types/severities, and complete pagination;
- conservative normalization into the established `CityEvent` contract;
- a reusable validated regional cache with approximately 5–15-minute provisional freshness;
- deterministic route relevance including geometry, direction, schedule, and applicability qualifications where supported;
- integration with the existing `POST /api/trips/analyze` response without losing Road Ahead behavior;
- regional Open511 map visibility **independent from** journey briefing eligibility;
- source-aware panel presentation, freshness, partial failures, and live end-to-end verification.

Do not implement DriveBC cameras, traffic-speed estimates, ETA changes, route optimization, weather, transit, or LLM briefings.

---

## 2. Execution Scope and Authorization

Phase 5 consists of four **separately authorized** Codex assignments. Completing an assignment does not authorize the next one.

### Assignment 5A — Open511 Source Evidence, Ingestion, Normalization, and Cache

- Verify actual endpoint, query parameters, returned schema, status semantics, paging, license/attribution, and regional geographic coverage.
- Implement a bounded source adapter (expected `backend/app/drivebc_open511.py`), preserving validated original geometry, source identity, descriptive metadata, directions, schedules, and timestamps.
- Fetch active events of **all types and severities**, across all result pages, in one regional request scope.
- Implement a validated, reusable regional disk cache with independent freshness, atomic replacement, and stale fallback.
- Add sanitized live-derived fixtures, mocked tests, and limited authorized live checks.

**Boundary:** No journey relevance, analysis API integration, or frontend work.

### Assignment 5B — Open511 Journey Relevance

- Reuse/adapt the accepted projected geometry matcher rather than creating a second GIS engine.
- Evaluate route overlap and proximity; supplement geographic relevance with trustworthy road/direction/schedule evidence when available.
- Distinguish geographic intersection from current travel-time applicability; preserve unknown and future-scheduled conditions.
- Preserve deterministic ordering, event identities, source-specific explanations, and all qualifying direct overlaps ahead of any nearby supplemental cap.
- Provide an application-owned result callable and offline regression tests.

**Boundary:** No API orchestration or map/panel integration. Do not invent directional certainty or severities.

### Assignment 5C — Combined Road Analysis API

- Extend existing `POST /api/trips/analyze` to load both Road Ahead and Open511 independently and combine source-aware findings.
- Preserve the accepted `Trip`, `SelectedRoute`, `JourneyAnalysis`, Road Ahead matching/enrichment, statuses, and factual summaries.
- Return sufficient **regional map data** separately from the route-relevant Open511 findings; do not put every regional event into the briefing.
- Handle absent/stale/failing Open511 without suppressing Road Ahead, and vice versa.
- Add focused contract/orchestration tests and representative API verification.

**Boundary:** No frontend/map implementation; no aggressive cross-source deduplication.

### Assignment 5D — Regional Map/Panel Integration and Human Acceptance

- Extend MapLibre with regional Open511 event geometry/markers; support source-aware styling and inspectable selected-event highlights.
- Keep the selected driving route prominent, maintain Road Ahead overlay behavior, and distinguish all-region map events from route-matched findings.
- Extend Along Your Route with source, status, severity when actually provided, affected direction, timing, provenance, and safe official links.
- Present stale, partial, and unavailable states accurately; protect against stale journey responses.
- Complete frontend/backend regression tests and a representative live regional journey, followed by human visual acceptance.

**Boundary:** No Phase 6 work; no broad shell redesign or new map framework.

Assignment boundaries are organizational, not grounds for speculative abstractions. Codex must stop after its authorized assignment and leave staging/commit/push to the human developer.

---

## 3. Established Accepted Baseline

### 3.1 Application and journey

Preserve Phases 1–3:

- FastAPI backend, React/Vite/TypeScript frontend, MapLibre/MapTiler dark basemap, ~65/35 desktop layout, Vite `/api` proxy;
- canonical geocoded locations and City of Vancouver destination validation;
- ORS driving alternatives with **explicit user route selection**;
- original selected GeoJSON LineString geometry, distance in metres, duration in seconds, request-scoped route identity;
- request cancellation/identity safeguards and correct map selection/invalidation;
- backend credential boundaries, pytest, Ruff, frontend tests and production build.

Never select a route automatically or make analysis reroute using ORS.

### 3.2 Accepted Phase 4 Road Ahead pipeline

- `backend/app/road_ahead.py`: official closures/construction ingestion, complete geometry, source identity, ~24-hour validated cache, independent `SourceStatus` and stale fallback;
- `backend/app/route_relevance.py`: Shapely/pyproj, EPSG:26910 metre-distance calculation, exact overlap vs nearby context, full mixed geometry, uncapped direct matches, provisional 500 m nearby threshold and nearby-only limit 10;
- `backend/app/detail_enrichment.py`: selective official detail enrichment, cautious source text, safe URLs, bounded requests, validated ~6-hour detail cache and failure fallback;
- `backend/app/analysis.py` and `backend/app/routes.py`: validated explicit `Trip`/`SelectedRoute`, `POST /api/trips/analyze`, structured `JourneyAnalysis`, honest data availability and deterministic summary;
- frontend analysis types/helpers, Road Ahead panel and MapLibre event layers, selected-event highlight above route, manual Analyze Journey interaction, stale-result invalidation.

Inspect actual files/models before proposing extensions; these paths and model summaries describe the accepted baseline, not permission to rewrite it. Preserve Phase 4 performance, source-status behavior and tests.

### 3.3 Source separation

Road Ahead municipal construction and DriveBC regional advisories may describe nearby or overlapping conditions without being duplicate records. Preserve distinct source identities, provenance, and source-specific freshness. No geometry-only merge or aggressive cross-source deduplication.

---

## 4. Open511 Source Discovery and Geographic Coverage

### 4.1 Evidence-first integration

Before coding 5A, inspect authoritative DriveBC Open511 documentation, previously captured Phase 0 evidence, approved license notes, and a small bounded number of real responses. Verify:

- official endpoint, HTTPS behavior, permitted usage and attribution;
- actual Open511 field names and schema/version;
- regional filtering parameters and supported bbox syntax;
- `status=ACTIVE` availability and whether status filtering is exhaustive for intended records;
- source event identifiers, timestamps, dates/schedules, direction fields and nested geography;
- pagination form (next links, offsets/limits or other actual provider mechanism);
- reported collection totals, completeness indicators, and possible service limits;
- event geometry types, missing fields, and invalid records;
- whether provider event detail links are trustworthy and usable.

Do not build against guessed query parameters or speculative fields. Preserve sanitized provider evidence; never commit credentials.

### 4.2 Regional scope

**Provisional bounding box:** `-123.45,48.99,-122.45,49.49` (west,south,east,north).

This comes from the approved roadmap and **is not yet locked**. Verify against intended Metro Vancouver → City of Vancouver trips, especially eastern approaches and highway corridors. If the approved box excludes significant intended origins or creates unusable coverage, document measured evidence and a proposed adjustment before locking a new default. Do not silently claim universal Lower Mainland coverage.

Request a reusable regional feed, **not a new provider dataset per chosen journey**. Keep bounds configurable and ensure cache identity includes the actual regional query scope.

### 4.3 Inclusion policy

Initial ingestion requests `ACTIVE` events, all event types, and all severities. Do not filter out `MINOR` or `UNKNOWN`, or discard future-scheduled ACTIVE events during ingestion. Retain the original source semantics and separate fetch inclusion from route/time relevance.

---

## 5. Pagination, Completeness, and Normalization

### 5.1 Pagination

Retrieve every matching page using the **actual verified Open511 paging contract**. Do not assume `limit=100` is complete. Bound page counts, runtime and payload size defensively while retaining completeness requirements. Detect and reject or mark incomplete:

- repeated next-page pointers/cycles;
- invalid pagination metadata;
- truncated or missing pages;
- internally inconsistent totals;
- unexpectedly invalid mass record loss;
- transport errors mid-pagination.

Never replace a known good cache with a demonstrably incomplete download. An empty valid dataset is allowed only when justified by source response validation.

### 5.2 `CityEvent` normalization

Reuse the existing normalized model, extending it narrowly only if required by an observed Open511 field that cannot be represented safely otherwise. Preserve:

- stable source-scoped event ID, source name, Open511 URL/record ID;
- headline, description, event category/subtypes;
- severity and source status **without interpreting unknown as clear**;
- actual full GeoJSON geography and representative point when provided;
- affected roads, named intersections/segments, direction or lane restrictions when supplied;
- raw schedule text or supported structured temporal data;
- created/updated/observed timestamps with correct timezone interpretation;
- official evidence URL and attribution.

Keep provider-native values in source metadata where needed, rather than inventing cross-source enums. Do not treat source representative points as replacements for supplied full geometry. Do not fabricate impact, direction, applicability, or closure state.

### 5.3 Malformed records

One isolated bad event should not necessarily invalidate the entire dataset. Count and report skipped records and source coverage honestly. Reject systemic schema drift or large unexplained record loss. Avoid hidden silent mass filtering.

---

## 6. Regional Validated Cache and Source Status

Use a configurable **initial 5–15-minute TTL**, selecting and documenting one concrete default at 5A after observing the feed. This is provisional, unlike Road Ahead's accepted ~24-hour TTL.

Cache should:

1. Reuse a fresh, validated **regional** snapshot for repeated analysis and route changes.
2. Refresh when stale or missing.
3. Fetch all pages and validate the complete replacement before activation.
4. Atomically replace the previous good snapshot.
5. Preserve the last valid snapshot on timeout, malformed response, interrupted pagination, or other refresh failure.
6. Return appropriate `SourceStatus` availability, success, cache hit, fetched time, age, stale state, received/normalized/skipped counts and bounded errors.
7. Report true unavailability when no usable cache exists.

Avoid overlapping redundant refreshes within the process. Reuse established 4A cache patterns where appropriate; avoid a generalized caching framework or new database infrastructure solely for Phase 5. Keep generated data Git-ignored and cache files validated before use.

Road Ahead and Open511 source freshness must remain independent. A successful Open511 refresh must not update Road Ahead timestamps or statuses, and vice versa.

---

## 7. Open511 Geospatial and Journey Relevance

### 7.1 Reuse deterministic geometry

Feed accepted valid Open511 geometry into the existing geographic projection/matching approach. EPSG:26910 is the established local projected CRS. Reuse and extend 4B logic where appropriate; avoid a second implementation of projection, intersection and distance ranking.

Classify geometry relationship conservatively:

- actual direct intersection/overlap;
- nonintersecting nearby context;
- geographically distant/not selected;
- missing/unusable geometry, explicitly unknown where it prevents matching.

A point-only Open511 event may require its own explicit point-distance rule; verify actual provider geometry and record its weaker specificity. Do not invent line segments or classify near points as exact road intersections.

**Preserve all qualifying direct route overlaps before limiting nearby supplemental findings.** Any supplemental limit is separate from the direct list. Existing 500 m/10 Road Ahead defaults are not automatically binding on Open511; reuse only with documented rationale, keep tuning explicit.

### 7.2 Road, direction and schedule qualifications

Use trustworthy source evidence where available to assess:

- affected road identity and segments;
- source-provided travel direction or carriageway;
- start/end periods or recurrence;
- whether an ACTIVE record describes an ongoing, planned or uncertain restriction;
- severity/type for presentation and cautious prioritization.

**ACTIVE status is not proof that a restriction is occurring at the instant of analysis.** Do not exclude a geometrically relevant event solely because a missing schedule/direction cannot be resolved. Instead preserve uncertainty and annotate applicability appropriately.

Do not claim lane blockage, delay, detour or direction-specific impact without suitable evidence. Do not invent geospatial matching certainty if geometry is inadequate. Keep temporal decisions deterministic and testable; defer complex event timelines and predictive impact to later phases.

### 7.3 Output

Produce source-attributed match results with classifications, computed distance where meaningful, match rationale, and temporal/directional qualifiers as supported. Preserve original event geometry, metadata, and identity. Stable sorting and duplicate suppression apply **within the same source event identity**, not across unrelated sources.

---

## 8. Regional Map Coverage Versus Journey Findings

This Phase 5 distinction is **mandatory**:

- **Map visibility:** show eligible active Open511 regional events in the supported area, even when distant from the currently selected route.
- **Journey analysis:** include only a deterministic route-relevant subset in the Along Your Route intelligence and summary.

A map-visible event is not automatically a briefing candidate. A source's `ACTIVE` inclusion is not a guarantee of present road obstruction.

The backend/API must expose an economical means for the frontend to obtain the current regional map snapshot separately from relevant findings. Reuse the same regional cache for both purposes. In 5C, choose a small contract consistent with existing API conventions (for example a regional events endpoint or appropriately separated analysis response field); document and test the choice. Do not overload `findings` with all regional events.

Frontend should distinguish DriveBC regional context from Road Ahead municipal findings, avoid unnecessary re-fetching when route selection changes, and tolerate unavailable/partial map datasets. All relevant geometry remains in original GeoJSON geographic coordinates for MapLibre.

---

## 9. Combined Journey Analysis API

Extend the accepted `POST /api/trips/analyze` rather than replacing it.

### Request

Preserve validated canonical origin/destination, driving mode, explicit selected route identity and original geometry. Do not rerun ORS or infer which route the user intended. Preserve existing request limits and destination eligibility.

### Orchestration

- Load Road Ahead and Open511 through independent source adapters and caches.
- Match each source using its appropriate deterministic relevance logic.
- Continue Road Ahead selective detail enrichment only for Road Ahead events.
- Do not fetch unrelated DriveBC webpages just to match events.
- Build source-aware findings with provenance and applicability qualifications.
- Preserve source-specific `SourceStatus` and combined coverage status.
- Produce factual deterministic summaries reflecting both sources and partial/unavailable coverage.

### Compatibility

Keep existing frontend Road Ahead functionality and the accepted response contract usable. Narrow additive fields/models are preferable to breaking renames; update frontend types in 5D. Avoid creating a parallel Open511-only analysis endpoint unless a concrete requirement justifies it.

### Degradation

- Road Ahead available, Open511 unavailable → keep Road Ahead findings; identify regional coverage gap.
- Open511 available, Road Ahead unavailable → retain regional findings; identify municipal coverage gap.
- Both unavailable → communicate unavailable, not "no road issues".
- Available sources with zero matches → say none identified **in available data**, not that the journey is clear.
- Stale cached sources → use with clearly surfaced age/stale flags.
- Unmatchable records → do not fabricate relevance or silence a material loss of coverage.

### Cross-source deduplication

Do not merge Open511 and Road Ahead events merely because geometries, roads or descriptions overlap. Show clearly attributed independent records over a falsely unified event.

---

## 10. Frontend — Regional Open511 Map

Extend the existing MapLibre implementation rather than replacing it.

- Render supported regional Open511 geometry/markers from the regional snapshot, not only from matched analysis findings.
- Use source-specific restrained styling, separate from Road Ahead coral/amber/highlight behavior.
- Keep the selected driving route prominent and selected-event overlays inspectable above coincident route geometry.
- Support only observed geometry types; use safe fallback/skip for unusable geometry.
- Avoid treating a source representative point as an exact road restriction unless explicitly labeled as approximate.
- Preserve existing map controls, route fits, bounds, dark basemap and attribution.
- Avoid repeated full map recreation or unnecessary network requests when merely switching route alternatives.
- Ensure regional map events are not mistaken for route warnings.

If source-level zoom filters, clustering or feature-count safeguards become necessary for actual regional volume, implement only the minimum supported by measured data and document the visibility tradeoff. Do not invent a generalized layer management interface.

---

## 11. Frontend — Along Your Route and Source Presentation

Preserve the accepted Road Ahead panel and add source-distinguishable DriveBC findings.

Present where grounded:

- event title, type and official source;
- direct/intersecting versus nearby/context relationship;
- source-reported severity and status;
- direction/affected road/schedule and whether applicability is known;
- source updated/retrieved time, cache age, stale/partial warning;
- official link only when safely validated;
- concise source-aware deterministic summary.

Do not treat `UNKNOWN` severity as minor, or `ACTIVE` as an ongoing physical obstruction without a matching schedule. Do not fabricate traffic speeds, delay minutes or detour recommendations. Preserve Road Ahead enrichment and safe-link messaging.

The interface must distinguish a regional map-only event from a relevant finding and avoid presenting map counts as journey findings counts. Preserve loading/error/empty/manual refresh states and request invalidation when origin, destination or selected route changes.

Do not redesign the 65/35 desktop layout or implement a general telemetry dashboard.

---

## 12. Provenance, Licensing, and Honest Interpretation

Use `docs/data-licensing-and-commercialization.md` and provider-specific evidence to verify Open511 terms, attribution and permitted uses before committing external content to fixtures or providing user-visible source reproductions.

Preserve data lineage from official event record through cache, normalized event, relevance result, response and map/panel. Sanitize fixtures; do not include secrets, tokens, personal account data, or bulk republished content beyond what testing requires.

The following are distinct and must not be conflated:

1. Event appears in an ACTIVE Open511 response.
2. Event is located within the regional map bounds.
3. Event is geographically relevant to the selected route.
4. The event applies to the intended travel direction and time.
5. It actually causes congestion or delay.

Only make claims supported by available data. Missing information remains unknown. Preserve source wording without treating it as a verified prediction.

---

## 13. Non-Goals

Phase 5 does **not** authorize:

- DriveBC highway or bridge camera image feeds;
- Vancouver camera integrations or image understanding;
- ECCC SWOB, OpenWeather or weather forecasts (Phase 6);
- GTFS Static, TransLink alerts or transit routing;
- OpenRouter text/vision inference, LLM interpretation or final AI briefing;
- turn-by-turn navigation or route optimization;
- traffic-aware rerouting, live speeds, computed delay/ETA changes;
- speculative event impact/severity inference;
- complex temporal prediction or historical telemetry warehousing;
- aggressive Road Ahead/Open511 deduplication;
- job queues, polling services, WebSockets, background monitoring;
- Redis, unrelated database migrations or abstract source-plugin platforms;
- new user accounts, saved journeys or application-wide frontend redesign;
- fabricated map markers or example telemetry represented as live data.

---

## 14. Verification Requirements

Each assignment must perform scope-appropriate checks and report **Passed / Failed / Not run** separately for mocked, fixture-based and live verification.

### 5A — Source and cache

- Actual HTTPS endpoint, query shape, region, status/type/severity policy and paging verified.
- Bbox coverage decision documented against representative route geography.
- One page, multiple pages, final partial page, pagination cycle, truncated response and provider total mismatch covered.
- All severity/type records retained; explicit ACTIVE inclusion tested; future-scheduled ACTIVE event retained.
- Null/malformed optional fields and actual observed geometry types normalized conservatively.
- Stable source IDs/provenance, source timestamps and detail URLs validated.
- Fresh cache reuse, stale refresh, atomic replacement, corrupted cache and source failure fallback tested.
- Region/parameter changes cannot accidentally reuse an incompatible cached snapshot.
- Bounded authorized live sanity verification captured without credentials.

### 5B — Relevance

- Exact overlap, nearby, distant, point-only and unusable geometry handled per approved rules.
- Projected metres and coordinate ordering verified.
- Road, direction and schedule evidence retained; missing/ambiguous qualifiers stay unknown.
- ACTIVE future schedule does not become "happening now".
- All direct intersections survive nearby limits.
- Stable results and source identity preserved.
- Existing Road Ahead geospatial tests remain passing.

### 5C — API

- Existing Road Ahead-only behavior remains intact.
- Combined response distinguishes each source and separates regional map dataset from journey findings.
- One-source failure, both-source failure, stale-source fallback and no-relevant-events results are honest.
- Explicit selected route is respected; no automatic rerouting.
- Two independently attributed overlapping events are not automatically merged.
- Stable serialized models and tests support later frontend integration.

### 5D — Frontend and end to end

- Regional events appear on the map independently of briefing eligibility.
- Source-specific markers/lines and selected-event highlights are legible.
- Road Ahead and route-selection layers still work.
- Along Your Route shows relevant Open511 events with conservative status, direction, schedule and provenance.
- Distant map-only events do not inflate analysis counts.
- Source cache freshness, partial and unavailable states remain distinct.
- Journey changes clear obsolete findings; late responses cannot restore them.
- Representative Metro Vancouver → Vancouver live analysis and browser visual check performed where available.
- No DriveBC camera functionality introduced.

### General regression and hygiene

Run applicable backend pytest, Ruff, frontend `npm test`, TypeScript/production build, backend health and API smoke checks, `git diff --check`, status/scope inspection, and `.env`/cache/secret hygiene checks. Do not require browser interaction for backend-only assignments. A build is not proof of visual browser acceptance.

---

## 15. Phase 5 Human Acceptance Criteria

Phase 5 is eligible for human acceptance only when:

- [ ] Open511 official endpoint and license/attribution are verified against actual evidence.
- [ ] The regional bbox is tested and its coverage/limitations documented.
- [ ] Regional ACTIVE ingestion retains all source severities and types.
- [ ] All pages are fetched and incomplete replacements rejected.
- [ ] Normalized CityEvents preserve source identity, geometry, road/direction/schedule metadata and timestamps.
- [ ] Regional validated cache is reused across selected routes.
- [ ] The chosen 5–15-minute provisional TTL is documented and functions.
- [ ] Cache corruption, stale fallback and unavailable source behavior are tested.
- [ ] Open511 relevance is deterministic, spatially sound and conservative about applicability.
- [ ] Direct overlaps are not truncated by nearby limits.
- [ ] Existing Road Ahead ingestion, enrichment and findings remain functional.
- [ ] Analysis integrates both source families with independent statuses.
- [ ] No aggressive cross-source deduplication occurs.
- [ ] Map shows regional Open511 events, including events not relevant to the selected route.
- [ ] Route-relevant Open511 events are distinguished from map-only events.
- [ ] Along Your Route communicates source, event type, status, direction and timing where available.
- [ ] Partial, unavailable, stale and empty states are truthfully conveyed.
- [ ] Selected-route identity and invalidation safeguards remain functional.
- [ ] Representative live regional analysis and meaningful visual review are documented.
- [ ] Relevant automated tests, builds and lint pass.
- [ ] Credentials and generated caches remain protected.
- [ ] No Phase 6, DriveBC camera or LLM scope is introduced.
- [ ] `PROJECT_STATE.md` reflects evidence, limitations and human-review status.
- [ ] Codex completes the required report and does not modify Git history.

These conditions establish review eligibility, **not automatic acceptance**.

---

## 16. Blockers and Escalation

Stop the affected assignment and report evidence if:

- the real Open511 endpoint, licensing terms or schema materially contradict the approved roadmap;
- status, bbox or pagination semantics cannot be safely verified;
- validated pagination cannot establish a sufficiently complete regional snapshot;
- planned region omits intended journey corridors and adjustment requires product approval;
- the accepted `CityEvent` or analysis response cannot represent essential source data without a significant breaking change;
- geometry types or direction/schedule semantics require redesigning the established matcher;
- a critical safety, credential, security or transport boundary cannot be met;
- a provider error cannot be represented honestly without extensive unrelated refactoring;
- a major new runtime service or architecture is required;
- completing the task would require unauthorized later-phase work.

For blockers, provide: observed issue, requirement affected, relevant evidence, reasonable alternatives and independent in-scope work completed. Routine pagination fixes, narrow model additions, cache configuration, field normalization, tests and small UI adjustments may proceed autonomously when compatible with existing contracts.

---

## 17. Phase Completion and Handoff

After each assignment:

1. Run focused and regression checks.
2. Update `PROJECT_STATE.md` with factual implementation, real evidence, test counts and limitations.
3. Report changed files, source behavior, deviations and remaining work.
4. Stop for human review; do not proceed to the next assignment automatically.
5. Leave Git staging, commits, pushes, merges, rebases, tags and history rewriting to the human developer.

After human Phase 5 acceptance:

1. Record acceptance and supporting evidence in `PROJECT_STATE.md`.
2. Create the human-controlled final Git checkpoint.
3. Prepare and approve the next `BUILD_PLAN.md`.
4. Do not begin Phase 6 until separately authorized.

This build plan is a **planning contract**. It does not itself authorize a blanket implementation of Phase 5.

---

## 18. Next Phase

**Phase 6 — Current + Near-Term Weather**

The approved roadmap next adds destination-context weather through ECCC SWOB observations and OpenWeather products, preserving the distinction between observations, current/forecast data and later camera-derived evidence. Phase 6 is outside this build plan and is not authorized by it.

