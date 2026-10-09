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

Current implementation state should be recorded separately in:

> `PROJECT_STATE.md`

---

# 2. Implementation Philosophy

RouteLens should be built using **vertical slices / tracer-bullet development**.

Avoid a horizontal sequence such as:

```text id="0d8f4d"
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

```text id="49cb17"
real source / user action
        ↓
validation
        ↓
normalization
        ↓
deterministic matching
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
- functionality can be tested behaviorally;
- the phase can become one logical human-created Git commit.

A phase should not attempt several unrelated systems at once.

---

# 4. Human-Controlled Git Checkpoints

Codex does not own Git history.

For every implementation phase:

```text id="5771af"
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

- commit;
- push;
- merge;
- tag;
- rewrite Git history.

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

```text id="708903"
inspect live source
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

# 7. Source-Specific Validation Principle

The data-source research has already reduced substantial uncertainty.

Implementation should preserve those findings rather than rediscovering everything from scratch.

Examples:

- Road Ahead uses two datasets and benefits from detail-page enrichment;
- Open511 is fetched regionally and paginated;
- SWOB is sparse and must be interpreted conservatively;
- Vancouver camera image URLs require catalogue enrichment;
- TransLink Service Alerts require GTFS identifier matching;
- OpenWeather still needs practical endpoint/schema validation.

When live behavior contradicts the documented design, report the discrepancy rather than silently inventing a new architecture.

---

# 8. Architecture Evolution Rule

Do not construct all infrastructure before it is needed.

Use **just-in-time implementation**.

Examples:

- introduce SQLite/SQLAlchemy when caching/persistence becomes useful;
- add Road Ahead detail caching only when enrichment is implemented;
- add camera image caching when the camera slice arrives;
- add GTFS parsing only in the Transit phase;
- add structured AI contracts when each AI capability arrives.

Do not pre-build speculative subsystems merely because they appear in the final technical design.

---

# 9. Planned Phase Overview

The roadmap is:

```text id="483031"
Phase 0   Integration Readiness
Phase 1   Application Shell + Map
Phase 2   Journey Input + Geocoding
Phase 3   Drive Route Candidates + Selection
Phase 4   Road Ahead Vertical Slice
Phase 5   Regional Road Context — DriveBC Open511
Phase 6   Current + Near-Term Weather
Phase 7   Vancouver Camera Pipeline
Phase 8   Multi-View Camera AI Analysis
Phase 9   Journey Relevance + Timeline Refinement
Phase 10  Transit Mode — GTFS Static + Service Alerts
Phase 11  AI Journey Briefing
Phase 12  Integration Hardening
Phase 13  Presentation + Demo Polish
```

Phases 0–6 are relatively firmly defined.

Later phases may be adjusted based on discoveries from the working application.

---

# 10. Phase 0 — Integration Readiness

## Objective

Resolve remaining external-service uncertainty before substantial implementation begins.

Much of the original discovery work has already been completed during planning.

This phase should therefore confirm, capture, and close the remaining integration gaps rather than repeat all previous exploration.

## Already Investigated

Planning/research has already established:

### Vancouver Webcams

- structured geolocated camera metadata exists;
- dataset provides camera page URLs;
- directional JPEG URLs require page enrichment;
- one-nearest-intersection / multi-view strategy is locked.

### Vancouver Road Ahead

- both Current Road Closures and Projects Under Construction were inspected;
- full geometry is available;
- geometry types include `LineString`, `MultiLineString`, and `GeometryCollection`;
- short dataset fields can be incomplete;
- detail pages provide useful schedule/restriction context;
- daily validated cache strategy is locked.

### DriveBC Open511

- active regional event strategy is defined;
- regional bbox approach is defined;
- pagination is required;
- map-wide visibility and journey-specific matching are separate;
- 5–15 minute initial cache policy is agreed.

### ECCC SWOB

- live feasibility has been tested;
- Vancouver-area observations were successfully retrieved;
- station coverage is sparse;
- missing measurements must remain unknown;
- station catalogue may not contain every realtime station;
- 10–15 minute initial cache is reasonable.

### TransLink

- API key has been obtained and tested;
- GTFS Static files were inspected;
- Service Alerts feed was successfully decoded/explored;
- route/direction matching is viable;
- selector specificity rules are understood;
- request-header behavior requires explicit client handling;
- Trip Updates and Vehicle Positions are deferred.

## Remaining High-Priority Readiness Work

### OpenWeather

This is the largest unresolved source integration.

Before Phase 6:

- test the existing API key;
- determine accessible endpoint(s);
- inspect actual schema;
- confirm current-condition fields;
- confirm forecast fields;
- determine practical lookahead granularity;
- determine request/cache strategy;
- save representative fixtures.

### MapTiler

Confirm:

- autocomplete/geocoding access;
- key behavior;
- basemap/style integration.

### openrouteservice

Confirm:

- route endpoint access;
- route-alternative behavior;
- representative Metro Vancouver journeys.

### OpenRouter

Confirm:

- chosen candidate vision model accepts multiple images;
- chosen text model supports reliable structured output;
- actual model identifiers/configuration.

## Configuration Work

Create/update:

```text id="2f6359"
.env.example
```

with names for required configuration.

Ensure:

```text id="1bdc86"
.env
```

is Git-ignored.

No secret value should enter fixtures or logs.

## Acceptance Criteria

- every core MVP source has a known access path;
- all required credentials are available or confirmed unnecessary;
- OpenWeather has undergone actual API exploration;
- MapTiler and ORS access are verified;
- OpenRouter candidate models can be called successfully;
- representative fixtures exist for sources needed in early phases;
- no major source-access blocker remains undiscovered.

## Non-Goals

Do not build application features during this phase.

The purpose is integration certainty.

---

# 11. Phase 1 — Application Shell + Map

## Objective

Create the RouteLens application foundation and establish the polished desktop visual shell.

The phase should end with a real interactive map visible inside the intended desktop layout.

## Backend

Create minimal FastAPI application.

Include:

```text id="adeb4c"
GET /api/health
```

No major domain logic yet.

## Frontend

Create:

- React;
- Vite;
- TypeScript;
- Tailwind;
- MapLibre;
- Framer Motion;
- Lucide.

Build the primary desktop shell:

```text id="0db85f"
top journey controls area
left map area
right intelligence panel area
```

Integrate a dark MapTiler basemap.

## Initial Visual Standard

The UI should already establish:

- dark city-intelligence aesthetic;
- correct map/panel proportions;
- clean typography;
- elevated panel styling;
- basic loading/status design language.

Do not defer all styling until the final phase.

Deep polish is not required yet.

## Acceptance Criteria

- frontend starts locally;
- FastAPI starts locally;
- frontend can reach backend health endpoint;
- MapLibre renders the MapTiler basemap;
- full desktop shell is visible;
- right panel placeholder exists;
- project runs without unnecessary infrastructure.

## Verification

- health endpoint test;
- Ruff;
- frontend build;
- manual map interaction/layout verification.

---

# 12. Phase 2 — Journey Input + Geocoding

## Objective

Allow the user to enter and select a real origin and Vancouver destination.

This establishes the first real user interaction.

## Backend / Integration

Add MapTiler geocoding/autocomplete support.

Normalize selected places into:

```text id="60340f"
Location
```

Implement deterministic destination validation.

The backend must reject unsupported destinations outside the City of Vancouver.

## Frontend

Implement:

```text id="979675"
JourneyInput
AddressAutocomplete
ModeSelector
Analyze/continue control
```

For this phase:

- Drive is the primary active mode;
- Transit can be visible but does not need transit-service selection yet.

Origin must be manually selected.

No current-location permission.

## UX

The user should:

1. type an origin;
2. select a suggestion;
3. type a destination;
4. select a suggestion;
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
- manual test with representative Metro Vancouver origins and Vancouver/non-Vancouver destinations.

---

# 13. Phase 3 — Drive Route Candidates + Selection

## Objective

Turn selected origin/destination into visible approximate driving-route context.

At the end of this phase, RouteLens supports:

> enter trip → see plausible routes → select closest route

## Backend

Add openrouteservice integration.

Normalize into:

```text id="d6afe3"
RouteCandidate
SelectedRoute
```

Return:

- up to three candidates where available;
- one candidate where alternatives are unavailable.

## Frontend

Implement:

```text id="854b27"
RouteSelector
RouteLayer
```

Display:

- candidate routes;
- selected route;
- muted alternatives.

Ask:

> Which route most closely matches your planned trip?

Do not imply that RouteLens recommends the optimal route.

## Acceptance Criteria

- route request works for real Metro Vancouver → Vancouver journeys;
- at least one route is returned for supported examples;
- alternatives appear where ORS provides them;
- user can select a route;
- selected route becomes visually prominent;
- selected route is represented in application state.

## Verification

Test representative journeys such as:

- New Westminster → downtown Vancouver;
- Burnaby → UBC;
- Richmond → downtown Vancouver;
- North Vancouver → Vancouver;
- Surrey → Vancouver.

Exact Google Maps reproduction is not required.

---

# 14. Phase 4 — Vancouver Road Ahead Vertical Slice

## Objective

Build the first complete telemetry slice.

This phase proves the central RouteLens pipeline:

```text id="82a9f4"
live municipal source
→ validated cache
→ normalization
→ projected geometry
→ route relevance
→ selective detail enrichment
→ API
→ map
→ journey interpretation
```

## Data Sources

Integrate both:

- Road Ahead — Current Road Closures;
- Road Ahead — Projects Under Construction.

## Backend

Implement:

```text id="aef9df"
road_ahead.py
```

Normalize into:

```text id="74ba45"
CityEvent
```

Preserve:

- source ID;
- source URL;
- full geometry;
- representative point;
- project/location text;
- source timestamps/metadata.

Do not depend on `street` being populated.

Do not treat `comp_date` as authoritative proof of event end.

## Geometry

Support:

- `LineString`;
- `MultiLineString`;
- `GeometryCollection`.

Use a suitable projected CRS for metre-based distance/buffer calculations.

## Cache

Implement the locked approximate 24-hour structured-dataset cache.

Behavior:

1. use fresh valid cache when available;
2. refresh when stale;
3. validate downloaded payload;
4. replace old cache only after validation;
5. retain stale valid cache on refresh failure;
6. expose stale status.

## Geospatial Relevance

Implement:

- direct route intersection;
- nearby supplemental candidates.

Locked rule:

> Preserve **all direct route overlaps** before applying a limit to nearby supplemental events.

## Selective Detail Enrichment

For geographically relevant candidates:

- fetch the Road Ahead detail page;
- deterministically extract useful schedule/restriction information;
- cache enrichment;
- retain base dataset event if enrichment fails.

Useful enrichment may include:

- full title/location;
- description;
- status;
- work schedule;
- exceptions;
- closure/restriction information.

Do not use an LLM for HTML parsing.

## API

Begin or extend:

```text id="269819"
POST /api/trips/analyze
```

For now, the analysis may primarily contain Road Ahead evidence.

## Frontend

Add:

- Road Ahead geometry/markers to map;
- initial Along Your Route section.

The UI should distinguish:

- direct overlaps;
- nearby context

where useful.

## Placeholder Summary

A deterministic summary may be used.

Example:

```text id="004a2b"
3 Road Ahead events intersect the selected journey.
1 additional nearby construction project was found.
```

Do not add final LLM briefing yet.

## Acceptance Criteria

Given a selected route:

- both Road Ahead datasets are loaded;
- validated cache works;
- full geometries normalize correctly;
- direct intersections are detected;
- all direct intersections survive candidate limiting;
- nearby candidates can be ranked separately;
- relevant detail pages enrich successfully where supported;
- parser failure falls back to base event;
- map displays relevant geometry;
- route panel displays useful event information;
- Road Ahead failure does not crash the whole analysis.

## Tests

Include fixtures for:

- valid closure;
- valid construction project;
- `LineString`;
- `MultiLineString`;
- `GeometryCollection`;
- null/missing optional fields;
- direct overlap;
- nearby event;
- distant event;
- more direct overlaps than supplemental candidate limit;
- valid detail-page enrichment;
- failed detail-page parse;
- stale-cache fallback.

This is the first major architectural proof point.

---

# 15. Phase 5 — Regional Road Context: DriveBC Open511

## Objective

Extend road awareness beyond City of Vancouver municipal data using DriveBC Open511.

This phase provides regional road context for journeys approaching Vancouver.

DriveBC cameras are **not** part of this phase or the MVP.

## Backend

Implement:

```text id="ac368f"
drivebc_open511.py
```

Normalize events into:

```text id="28a21f"
CityEvent
```

Preserve:

- source event ID;
- headline/description;
- event type/subtypes;
- severity;
- status;
- full geography;
- road/direction information where available;
- schedule;
- created/updated timestamps.

## Regional Fetch Strategy

Fetch a regional dataset rather than querying only around the selected route.

Initial provisional bbox:

```text id="bd7f23"
-123.45,48.99,-122.45,49.49
```

Before locking it in code, verify it covers the intended Metro Vancouver region sufficiently.

Fetch:

- `status=ACTIVE`;
- all event types;
- all severities.

Do not discard `MINOR` or `UNKNOWN` severity at ingestion.

## Pagination

Retrieve all matching pages.

Do not assume a single `limit=100` request is complete.

## Cache

Implement regional Open511 caching.

Initial TTL:

> approximately 5–15 minutes.

Reuse the same regional dataset across route changes.

If refresh fails:

- retain last valid cache;
- mark it stale;
- continue where practical.

## Map Behavior

Show active Open511 events throughout the supported regional area.

Map visibility is not equivalent to journey relevance.

The user may see events that do not qualify for the briefing.

## Journey Relevance

Filter briefing candidates deterministically using, where available:

- route geometry;
- proximity;
- affected roads;
- direction;
- schedule;
- temporal applicability;
- severity;
- event type.

An `ACTIVE` event may still be scheduled for a future time.

Do not assume current applicability solely from status.

## Cross-Source Behavior

Road Ahead and Open511 should coexist through normalized `CityEvent` models.

Do not implement aggressive cross-source deduplication.

Preserve source attribution.

## Frontend

Add:

- regional Open511 event layer;
- event details;
- route-relevant emphasis.

## Acceptance Criteria

- regional Open511 events fetch successfully;
- pagination retrieves all pages;
- all active severities/types remain available;
- regional events appear on map;
- route-relevant subset is identified separately;
- distant map-visible events do not automatically enter briefing candidates;
- Open511 cache is reused across route changes;
- stale-cache fallback works;
- failure remains isolated;
- no DriveBC camera functionality is introduced.

---

# 16. Phase 6 — Current + Near-Term Weather

## Objective

Add destination weather context while preserving the distinction between:

- measured station observations;
- structured current/forecast data;
- later camera-derived visual evidence.

This phase combines:

- ECCC SWOB;
- OpenWeather.

## Phase 6A — OpenWeather Validation

Before final adapter implementation:

- test the existing API key;
- identify the actual accessible endpoint/product;
- inspect real response schema;
- confirm available current fields;
- confirm forecast fields;
- confirm timestamp granularity;
- determine useful lookahead;
- determine cache/refresh policy;
- save fixtures.

Do not implement speculative fields that the actual endpoint does not provide.

## Backend — SWOB

Implement:

```text id="a0f682"
eccc_swob.py
```

Fetch recent observations for a Vancouver-area bbox.

Initial tested bbox:

```text id="b46af4"
-123.30,49.15,-122.85,49.35
```

Group by station.

Select latest valid observation per station.

Do not assume the separate station catalogue contains every realtime station.

Use embedded coordinates where possible.

Normalize useful fields such as:

- temperature;
- precipitation measurements;
- visibility;
- wind where actually available;
- snow depth where available;
- timestamps.

## SWOB Selection

Select useful evidence using:

- proximity;
- freshness;
- measurement availability.

The nearest station is not automatically the most useful.

Missing precipitation remains unknown.

Zero measured precipitation means zero for that station/time window only.

No neighborhood interpolation.

## SWOB Cache

Initial TTL:

> approximately 10–15 minutes.

Stale fallback may be used with clear age/status.

## Backend — OpenWeather

Implement the final adapter only after validation.

Normalize actual supported fields into the RouteLens weather models.

Potential information may include:

- current temperature;
- current conditions;
- precipitation probability/amount if available;
- forecast timestamps;
- near-term conditions.

## Frontend

Add destination weather UI that clearly separates:

```text id="9423e6"
Measured observation
Structured current/forecast
```

Do not call both simply “current weather” without provenance.

Example:

```text id="f6b7f9"
ECCC observation · 8m ago
11°C · 0 mm hourly precipitation

OpenWeather
Light rain possible later in the near term
```

## Acceptance Criteria

- OpenWeather actual endpoint/schema has been validated;
- OpenWeather adapter reflects real available fields;
- SWOB latest observations group correctly by station;
- realtime stations absent from catalogue are not discarded automatically;
- useful station selection considers measurement availability;
- missing values remain unknown;
- SWOB and OpenWeather remain structurally separate;
- source timestamps/freshness appear in UI;
- either source may fail independently;
- journey remains usable with one weather source unavailable.

---

# 17. Phase 7 — Vancouver Camera Pipeline

## Objective

Implement the signature camera data pipeline without AI interpretation yet.

This phase introduces:

- Vancouver camera metadata ingestion;
- standalone camera-catalogue enrichment;
- directional image extraction;
- nearest usable intersection selection;
- multi-view image retrieval;
- ephemeral image cache;
- destination camera UI;
- SQLite/SQLAlchemy where justified.

## Camera Catalogue Enrichment

Implement a standalone enrichment script.

Conceptual:

```text id="d2aa75"
official Vancouver camera metadata
        ↓
validate
        ↓
visit each camera webpage
        ↓
extract directional image URLs
        ↓
validate image endpoints
        ↓
write enriched local catalogue
```

Do not guess JPEG filenames.

The enriched catalogue should retain:

- camera/intersection ID;
- name;
- coordinates;
- page URL;
- available directional views;
- image URLs;
- catalogue fetch/enrichment time.

## Catalogue Cache

Initial policy:

> infrequent refresh, approximately 24 hours as a starting point.

Retain the last valid catalogue if refresh/enrichment fails.

## Destination Camera Selection

For each journey:

1. sort camera intersections by destination distance;
2. inspect the nearest candidate;
3. verify at least one usable image;
4. if unusable, try the next-nearest candidate;
5. select the first usable intersection.

The MVP selects:

> one nearest usable camera intersection.

No multiple-intersection analysis.

## Image Retrieval

Fetch all usable directional views from the selected intersection.

Typical count may be 2–4, but the code must tolerate fewer.

## Image Storage

Locked:

- ephemeral/cache-only;
- overwrite current cached frames;
- no historical archive;
- no time-series accumulation.

Suggested structure:

```text id="9052c6"
data/cache/cameras/{intersection_id}/{view_id}.jpg
```

## Persistence

Introduce SQLite/SQLAlchemy only as needed for:

- source cache metadata;
- camera catalogue metadata;
- current image metadata.

Do not build unrelated persistence abstractions.

## Frontend

Implement:

```text id="b97d07"
DestinationConditions
CameraDetail
```

Prominently display:

- selected intersection;
- all usable directional views;
- image retrieval freshness.

Map may show Vancouver camera intersections where useful.

Alternative intersection browsing is optional rather than core.

## Acceptance Criteria

- official camera metadata loads;
- enrichment script extracts real directional image URLs;
- broken/missing views are tolerated;
- enriched catalogue is persisted locally;
- nearest usable camera is selected;
- fallback to next candidate works;
- all usable directional images fetch successfully;
- images are served through RouteLens/backend;
- current frames overwrite prior frames;
- no historical archive is created;
- destination-condition UI displays multi-view imagery.

---

# 18. Phase 8 — Multi-View Camera AI Analysis

## Objective

Add multimodal interpretation to the selected Vancouver camera intersection.

This is the first major AI capability.

## Backend

Add OpenRouter vision integration.

All calls originate from FastAPI.

Input:

- all usable current directional images from the selected intersection;
- constrained structured prompt;
- minimal camera metadata if useful.

Output:

```text id="4b748e"
CameraObservation
```

validated through Pydantic.

## One Inference Per Intersection

Locked behavior:

> one multimodal request analyzes all usable views together.

Do not make one model call per directional image unless implementation evidence demonstrates a clear need.

## Structured Fields

Core fields include:

- precipitation visible;
- precipitation type where supportable;
- road surface;
- visibility;
- image-quality assessment;
- confidence;
- concise notes.

Traffic density is optional and should not expand the scope into traffic-speed inference.

## Prompt Behavior

The model must:

- use only supplied imagery;
- distinguish wet pavement from active precipitation;
- avoid inferring dry conditions solely from no visible rainfall;
- explicitly represent uncertainty;
- note glare/obstruction/poor resolution;
- avoid identifying individuals;
- avoid invented meteorological values.

## Cache / Reuse

Reuse current analysis where it corresponds to the same cached image set and remains fresh enough.

A newly fetched image set invalidates the old current-frame analysis.

## Failure Behavior

If AI analysis fails:

- camera imagery remains visible;
- weather/road/transit data remain usable;
- camera analysis is marked unavailable;
- invalid LLM output does not break journey analysis.

## Acceptance Criteria

- all usable intersection views can be sent in one OpenRouter request;
- structured output validates;
- uncertainty/null values are supported;
- wet-road vs active-rain distinction is reflected;
- analysis is associated with the current image set;
- duplicate calls are avoided where reusable;
- malformed output fails safely;
- frontend displays the normalized camera observation.

---

# 19. Phase 9 — Journey Relevance + Timeline Refinement

## Objective

Turn the growing telemetry set into a coherent deterministic journey model before adding the final text LLM briefing.

This phase refines:

- event relevance;
- applicability;
- importance;
- evidence density;
- timeline ordering;
- Journey Status foundation;
- provenance/freshness presentation.

## Backend

Combine:

- Road Ahead;
- Open511;
- SWOB;
- OpenWeather;
- camera observations.

Transit is added in Phase 10.

Refine deterministic ranking using:

- direct route overlap;
- route distance;
- destination proximity;
- freshness;
- source-reported severity;
- temporal applicability;
- travel direction where available;
- source type.

## Candidate Handling

Preserve:

- all directly applicable road overlaps;
- top supplemental nearby events.

Do not impose a global N limit that removes direct overlaps.

## Evidence Categories

Keep evidence types distinct:

- source-reported road condition;
- measured weather;
- structured weather forecast/current data;
- camera AI observation.

## Timeline

Build normalized timeline events.

Order geographic events approximately along the route.

Example:

```text id="c82c3c"
START
  │
  ● road construction
  │
  ● regional incident
  │
  ● changing weather context
  │
DESTINATION
  ● camera observation
```

Do not ask the LLM to invent route order.

## Frontend

Implement/refine:

```text id="ae8744"
JourneyTimeline
JourneyStatus
AlongYourRoute
SourceFreshness
```

Map may expose more regional telemetry than the timeline.

## Insight Density

Target approximately:

> 3–6 important automated findings

while retaining all direct route overlaps when necessary.

The 3–6 target applies to the interpreted/highlighted experience, not necessarily every map item.

## Acceptance Criteria

- direct overlaps remain preserved;
- nearby supplemental events are ranked deterministically;
- temporal/directional caveats remain available;
- weather evidence categories remain distinguishable;
- timeline is deterministic;
- regional map data does not automatically become briefing data;
- source provenance/freshness is retained;
- missing values remain unknown.

---

# 20. Phase 10 — Transit Mode: GTFS Static + Service Alerts

## Objective

Add useful service-specific Transit mode while deliberately avoiding full transit routing.

Drive/geographic behavior should already be stable.

## MVP Transit Scope

Include:

- GTFS Static route/direction reference data;
- user-selected ordered transit legs;
- GTFS-Realtime Service Alerts.

Explicitly do not include:

- Trip Updates;
- Vehicle Positions;
- exact transit itinerary generation;
- boarding/exiting stop selection;
- transit map visualization.

---

## Phase 10A — GTFS Static Preprocessing

Implement GTFS Static ingestion.

Required files:

- `routes.txt`;
- `trips.txt`.

`stops.txt` may be retained for future use but is not required for core MVP selection.

Build searchable route index containing:

- `route_id`;
- `route_short_name`;
- `route_long_name`;
- `route_type`.

Build direction/headsign index from `trips.txt`.

Do not expose every trip row.

Derive passenger-friendly direction choices.

Do not assume `direction_id=0/1` has a universal directional meaning.

## GTFS Static Cache

Initial operational policy:

> approximately weekly or on new official feed publication.

Use validated replacement.

---

## Phase 10B — Transit Selection UI

When Transit mode is selected, allow the user to build ordered legs.

Example:

```text id="380e2c"
Leg 1
R5 Hastings
Toward Downtown Vancouver

Leg 2
Expo Line
```

Support:

- buses;
- SkyTrain lines;
- multiple legs;
- direction where meaningful.

Preserve official IDs beneath friendly labels.

---

## Phase 10C — Service Alerts

Implement TransLink GTFS-Realtime Service Alerts.

Decode binary Protocol Buffers.

Use explicit HTTP headers known to work with the endpoint.

Handle:

- 403;
- rate limits;
- malformed payload;
- API unavailability.

Never log the API key.

## Alert Cache

Initial policy:

> approximately 30–60 seconds.

Reuse feed across repeated analyses.

---

## Alert Normalization

Preserve:

- header text;
- description text;
- cause/effect;
- active periods;
- all informed-entity selectors;
- source URL where available.

Do not depend only on enums.

---

## Deterministic Matching

For each selected transit leg, compare:

- `route_id`;
- optional `direction_id`.

Classify matches.

### Route + matching direction

Strong service-level match.

### Route without direction restriction

Potentially relevant to either direction.

### Route + stop selector

Location-specific; do not call it route-wide automatically.

### Trip-specific selector

Do not assume applicability without trip identity.

### Opposite direction only

Exclude unless another selector independently matches.

Multiple selectors in one alert are alternatives within that alert.

---

## Temporal Applicability

Use active periods where available.

Preserve source text for schedule qualifications.

Do not mark an old-start-date alert stale merely because the start date is old.

Do not assume an open-ended active period means a restriction applies continuously.

---

## Frontend

Transit mode should:

- retain road/weather/camera geographic context;
- show the ordered selected transit legs;
- display matching service alerts;
- communicate alert scope clearly;
- avoid implying exact transit routing;
- avoid unsupported delay estimates.

No transit map overlays.

---

## Acceptance Criteria

- GTFS Static route index builds successfully;
- SkyTrain routes with empty short names remain searchable;
- direction choices derive from trip/headsign data;
- user can add ordered transit legs;
- canonical GTFS IDs are preserved;
- Service Alerts decode successfully;
- explicit request headers work;
- route/direction matching works;
- opposite-direction-only alert is excluded;
- directionless route alert remains potentially relevant;
- stop-specific scope is preserved;
- trip-specific applicability is not overstated;
- open-ended active periods are handled conservatively;
- Transit failure remains isolated;
- no Trip Updates/Vehicle Positions/transit visualization are introduced.

---

# 21. Phase 11 — AI Journey Briefing

## Objective

Add the final text-model synthesis after the structured evidence pipeline is stable.

## Backend

Build a compact evidence payload containing only normalized relevant information.

Possible input:

```text id="d13fbf"
Trip
SelectedRoute

Important Road Ahead Events
Relevant Open511 Events

CameraObservation

SWOB Observations
OpenWeather Current/Forecast

Selected Transit Legs
Matched Transit Alerts

Source freshness / unavailable sources

JourneyTimeline
```

Do not send:

- raw JSON feeds;
- entire GTFS feed;
- raw HTML;
- every regional Open511 event;
- unrelated telemetry.

## OpenRouter

Call the selected text model.

Require:

```text id="51cc5a"
JourneyBriefing
```

with:

```text id="252a26"
status
summary
highlights[]
recommendation
```

Validate through Pydantic.

## Behavioral Requirements

The LLM must:

- use only supplied evidence;
- distinguish source-reported, measured, forecast, and visually inferred conditions;
- remain concise;
- avoid invented disruptions;
- avoid invented travel times;
- avoid invented delay durations;
- preserve uncertainty;
- allow “journey looks clear” outcomes;
- avoid unnecessary urgency.

## Frontend

Replace temporary deterministic summary with:

```text id="fa6dad"
RouteLens AI Briefing
```

Maintain structured UI control over:

- status;
- summary;
- highlights;
- recommendation.

## Acceptance Criteria

- valid structured briefing is produced;
- malformed output fails safely;
- clear journeys receive calm output;
- findings correspond to supplied evidence;
- evidence disagreements can be expressed;
- transit specificity is not lost;
- no unsupported delay/closure/weather claim is introduced;
- output remains concise.

---

# 22. Phase 12 — Integration Hardening

## Objective

Improve reliability after all major MVP capabilities exist.

This is not a new-feature phase.

## Partial Failure

Test combinations such as:

```text id="5a4eab"
Road Ahead refresh fails
Open511 unavailable
SWOB unavailable
OpenWeather unavailable
camera catalogue stale
camera image unavailable
camera AI unavailable
TransLink unavailable
OpenRouter text call unavailable
```

The remaining application should still work where possible.

---

## Cache Behavior

Verify:

- Road Ahead 24-hour cache;
- Road Ahead stale fallback;
- detail-page cache;
- Open511 5–15 minute cache;
- SWOB 10–15 minute cache;
- camera catalogue cache;
- ephemeral image overwrite behavior;
- GTFS Static cache;
- Service Alert short cache;
- OpenWeather cache once finalized.

---

## Cache Integrity

Confirm:

- malformed new payload does not replace valid cache;
- stale age is reported;
- cached provenance is retained;
- atomic replacement is used where practical.

---

## Geometry

Verify:

- projection correctness;
- `LineString`;
- `MultiLineString`;
- `GeometryCollection`;
- direct overlap preservation;
- regional Open511 matching.

---

## Transit

Verify:

- route index freshness;
- GTFS Static and realtime IDs align;
- direction matching;
- missing direction handling;
- stop-specific alerts;
- trip-specific alerts;
- active-period edge cases.

---

## Weather

Verify:

- missing SWOB measurements;
- zero vs missing precipitation;
- stale station observations;
- disagreement between SWOB/OpenWeather/camera;
- OpenWeather field absence.

---

## Camera

Verify:

- broken camera page;
- missing direction;
- broken JPEG;
- nearest camera unusable;
- next-nearest fallback;
- partial view availability;
- multimodal failure.

---

## Logging

Confirm logging for:

- source fetch success/failure;
- cache hit/miss/stale fallback;
- pagination counts;
- number of records normalized;
- LLM call latency/errors;
- total analysis time.

No secrets in logs.

---

## Empty States

Test:

- no Road Ahead match;
- no journey-relevant Open511 event;
- no usable camera;
- no useful SWOB reading;
- no matching Transit alert;
- no significant findings.

## Acceptance Criteria

- individual source failures remain isolated;
- validated caches behave predictably;
- stale data is labeled;
- no common edge case unnecessarily crashes analysis;
- missing values remain unknown;
- source statuses reach frontend;
- error messages are understandable.

---

# 23. Phase 13 — Presentation + Demo Polish

## Objective

Turn the functioning MVP into a presentation-ready product.

This phase is protected from feature creep.

Do not add new major integrations.

---

## Loading UX

Improve analysis-state feedback.

Example:

```text id="3114ab"
Analyzing journey…

✓ route loaded
✓ municipal road data checked
✓ regional road events checked
✓ weather checked
✓ destination camera checked
✓ transit alerts checked
✓ generating briefing
```

Exact wording may differ.

---

## Freshness UX

Ensure clear source-specific labels.

Examples:

```text id="04126a"
Camera · retrieved 4m ago

ECCC · observed 9m ago

DriveBC · refreshed 3m ago

Road Ahead · dataset fetched 6h ago

TransLink · refreshed 35s ago

OpenWeather · refreshed 8m ago
```

Stale sources should look distinct.

---

## Failure UX

Ensure partial-source errors are visible without overwhelming the interface.

Examples:

```text id="61794a"
Camera observation unavailable

TransLink alerts unavailable

Road Ahead using cached data from 27h ago
```

---

## Motion

Refine:

- route reveal;
- card entrance;
- destination camera presentation;
- panel transition;
- Live indicator;
- loading states.

Avoid decorative excess.

---

## Visual Cleanup

Review:

- spacing;
- hierarchy;
- destination-condition prominence;
- multi-view camera layout;
- marker design;
- route contrast;
- typography;
- transit alert presentation;
- source/freshness badges;
- empty states;
- panel balance;
- scroll behavior.

---

## Demo Routes

Identify several reliable scenarios that exercise different capabilities.

Examples:

### Drive

Regional journey into downtown with:

- ORS route;
- Road Ahead event;
- Open511 context;
- camera intersection;
- weather.

### Transit

Journey with:

- approximate geographic route;
- one or more selected transit services;
- Service Alert behavior;
- weather/camera context.

Exact routes should be chosen near presentation time based on live conditions.

---

## Demo Smoke Test

Perform end-to-end rehearsal:

```text id="3f8099"
fresh application start
→ origin/destination
→ mode
→ route selection
→ optional transit-service selection
→ analysis
→ Road Ahead
→ Open511
→ weather
→ multi-view camera
→ camera AI
→ transit alerts if applicable
→ timeline
→ briefing
```

Verify no developer-only intervention is needed during the demo.

---

## Acceptance Criteria

- primary drive demo works reliably;
- primary transit demo works reliably;
- loading states are clear;
- errors degrade gracefully;
- no major visual rough edges remain;
- destination camera feature is visually strong;
- final experience communicates RouteLens within seconds;
- no new major feature is introduced.

---

# 24. Expected Evolution of Later Phases

Phases 0–6 are deliberately defined more tightly.

Phases 7 onward may change based on:

- camera-page consistency;
- directional image availability;
- image quality;
- OpenRouter vision performance;
- GTFS preprocessing realities;
- alert selector edge cases;
- OpenWeather API behavior;
- runtime latency;
- UI feedback.

Changes should preserve product requirements unless real implementation evidence shows a requirement itself needs reconsideration.

If architecture changes materially:

> update `docs/technical-design.md`

If product behavior changes materially:

> update `docs/prd.md`

If only build sequence changes:

> update this implementation plan.

---

# 25. Deferred Features Must Stay Deferred

The following are explicitly outside MVP implementation unless scope is deliberately reopened:

- DriveBC cameras;
- multiple Vancouver camera intersections per journey;
- historical camera archive;
- camera time-series analysis;
- image upscaling;
- camera traffic-speed estimation;
- GTFS-Realtime Trip Updates;
- GTFS-Realtime Vehicle Positions;
- exact transit trip selection;
- boarding/exiting stop selection;
- full transit routing;
- transit network map;
- vehicle markers;
- weather-station interpolation;
- complex cross-source event deduplication.

Codex should not implement these opportunistically.

---

# 26. Development Artifacts Created From This Plan

This document is not intended to be Codex's complete working context.

Before implementation begins, derive the project SDD harness.

Recommended root files:

```text id="ad086e"
AGENTS.md
APP_SPEC.md
BUILD_PLAN.md
PROJECT_STATE.md
```

---

# 27. Relationship to APP_SPEC.md

`APP_SPEC.md` should become the concise Codex-facing implementation specification.

It should derive relevant truths from:

```text id="f2d7df"
docs/prd.md
+
docs/technical-design.md
```

while omitting unnecessary planning rationale and discussion history.

Focus on:

- system invariants;
- architecture;
- expected behavior;
- model boundaries;
- core source responsibilities;
- important constraints;
- deferred scope.

---

# 28. Relationship to BUILD_PLAN.md

`BUILD_PLAN.md` converts the current roadmap phase into an operational coding task.

For example:

```text id="07f2dc"
docs/implementation-plan.md

Phase 4
Road Ahead Vertical Slice
```

becomes:

```text id="ea680d"
BUILD_PLAN.md

CURRENT PHASE
Road Ahead Vertical Slice

Objective
...

Relevant source behavior
...

Scope
...

Non-goals
...

Acceptance criteria
...

Verification
...

Stop conditions
...
```

The build plan may evolve more frequently than this implementation roadmap.

---

# 29. Relationship to PROJECT_STATE.md

`PROJECT_STATE.md` tracks reality.

It should answer:

- which phase has completed;
- which phase is current;
- what functionality actually exists;
- what real source behaviors were discovered;
- important implementation decisions;
- known issues;
- deferred work;
- verification status;
- next recommended action.

Do not turn `implementation-plan.md` into a progress log.

---

# 30. Relationship to AGENTS.md

`AGENTS.md` should define project-wide coding-agent behavior.

Likely rules include:

- inspect existing code before changing it;
- read the SDD harness;
- respect documented architecture;
- remain within current phase;
- avoid unrelated refactoring;
- preserve source provenance;
- do not convert missing data into defaults;
- do not implement deferred features;
- run required verification;
- report uncertainty;
- never commit or push;
- stop/report when live source behavior materially invalidates the design.

---

# 31. Planning-Agent Role During Implementation

The planning agent remains active throughout development.

For each phase:

```text id="53adf4"
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
- incorporate relevant source-specific research;
- identify only necessary architecture/context;
- produce a tightly scoped implementation prompt;
- define acceptance criteria;
- define verification;
- prevent scope expansion.

The planning agent does not redesign RouteLens before every phase.

---

# 32. Codex Role During Implementation

For a given phase, Codex should:

1. inspect current repository state;
2. read project instructions;
3. understand current bounded task;
4. implement only the required capability;
5. use available feedback loops;
6. add/update tests;
7. run verification;
8. perform safe live integration checks where required;
9. update `PROJECT_STATE.md` where appropriate;
10. report changes/deviations;
11. leave Git history untouched.

Codex should not autonomously move into future phases.

---

# 33. Human Role During Implementation

The human remains responsible for:

- phase acceptance;
- architecture/product judgment;
- significant dependency approval;
- review of source adapters;
- review of geospatial logic;
- review of caching/data integrity;
- review of transit matching;
- review of AI contracts/prompts;
- behavioral QA;
- visual QA;
- deciding whether discoveries require design changes;
- Git commits;
- deciding when to advance.

Ordinary React/CSS/helpers may receive lighter review where behavior is correct.

---

# 34. Implementation Mental Model

The development path should remain:

```text id="a4c5a4"
VERIFY DEPENDENCIES
        ↓
CREATE VISUAL SHELL
        ↓
ENTER A REAL JOURNEY
        ↓
DRAW A REAL ROUTE
        ↓
ADD MUNICIPAL ROAD DATA
        ↓
ADD REGIONAL ROAD CONTEXT
        ↓
ADD STRUCTURED + MEASURED WEATHER
        ↓
ADD VANCOUVER CAMERA PIPELINE
        ↓
ADD MULTI-VIEW CAMERA AI
        ↓
REFINE JOURNEY RELEVANCE
        ↓
ADD TRANSIT SERVICE SELECTION + ALERTS
        ↓
ADD FINAL AI SYNTHESIS
        ↓
HARDEN
        ↓
POLISH
```

At every step, RouteLens should become more visibly real.

Avoid long periods where infrastructure exists without user-visible value.

---

# 35. Final Implementation Principle

The purpose of this plan is not to predict every implementation detail perfectly.

It is to provide a disciplined path toward a working RouteLens MVP while allowing real source behavior to inform later decisions.

The guiding rule is:

> **Build the smallest real slice, verify it against reality, preserve what works, and use what is learned to shape the next slice.**

The roadmap should remain stable enough to guide development while flexible enough to respond to genuine implementation evidence.
