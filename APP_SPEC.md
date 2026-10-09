# RouteLens AI — Application Specification

## 1. Purpose

RouteLens AI is a local, desktop-oriented web application that enriches an already-planned journey into the City of Vancouver with current public city telemetry.

Its central question is:

**What is happening around my journey that I should know before I leave?**

RouteLens combines road events, construction, destination cameras, weather, and transit advisories into an interactive map and concise AI-assisted journey briefing.

Core product principle:

**The route guides relevance; the telemetry provides the value.**

RouteLens is a companion to existing navigation applications, not a navigation replacement.

This document defines the approved intended MVP system. It does not indicate which functionality has already been implemented. Consult `PROJECT_STATE.md` for repository reality and `BUILD_PLAN.md` for the current authorized work.

## 2. Product Scope and User Workflow

### Geographic Scope

- Origins may be broadly within Metro Vancouver or the surrounding Lower Mainland.
- Destinations must be inside the City of Vancouver.
- Destinations outside Vancouver must be rejected with clear feedback.
- Journeys leaving Vancouver for destinations outside the city are unsupported.

### Travel Modes

The MVP supports:

- **Drive** — geographic route context and stronger emphasis on road conditions.
- **Transit** — approximate geographic journey context plus explicitly selected transit services.

Walking and cycling are excluded.

### Core User Workflow

1. User manually selects an origin through place autocomplete.
2. User selects a destination through autocomplete.
3. Application validates that the destination is inside Vancouver.
4. User selects Drive or Transit.
5. Application generates approximate journey corridor candidates.
6. User selects the corridor closest to their intended journey.
7. In Transit mode, user selects ordered bus/SkyTrain services and directions where useful.
8. Application gathers current and near-term telemetry.
9. Deterministic logic identifies geographically, temporally, and service-specifically relevant evidence.
10. Application selects the nearest usable Vancouver camera intersection and retrieves available directional images.
11. Multimodal AI interprets those camera views together.
12. Application presents the map, destination conditions, journey-specific findings, source statuses, and AI briefing.

### Usage Model

RouteLens is an on-demand, near-departure tool.

- No user accounts or persistent personal profiles.
- No saved journeys or recurring monitoring.
- No background notifications.
- No automatic current-location detection.
- No automatic continuous journey refresh.

Analysis remains static until the user explicitly re-runs or refreshes it.

## 3. Architecture and Technology Stack

### Frontend

Approved stack:

- React
- Vite
- TypeScript
- Tailwind CSS
- MapLibre
- Framer Motion
- Lucide

Responsibilities include:

- journey input and validation feedback;
- candidate route selection;
- transit-service selection;
- interactive map and telemetry overlays;
- destination-camera presentation;
- journey intelligence panel;
- loading, error, and partial-failure states;
- freshness and provenance presentation.

### Backend

Approved stack:

- Python
- FastAPI
- Pydantic
- httpx
- SQLAlchemy
- SQLite
- Shapely
- pytest
- Ruff

Responsibilities include:

- external-service access;
- validation and normalization;
- routing/geocoding coordination;
- source-specific caching;
- deterministic geospatial and transit relevance;
- camera catalogue enrichment and image handling;
- AI inference and structured-output validation;
- journey analysis orchestration;
- local persistence;
- API responses.

Additional lightweight libraries are permitted where justified by a current-phase requirement.

### External Services

| Service | Responsibility |
|---|---|
| MapTiler | Dark basemap, geocoding, autocomplete |
| openrouteservice | Approximate journey route candidates |
| OpenRouter | Camera multimodal inference and journey briefing |
| OpenWeather | Structured current and near-term weather |
| TransLink | GTFS Static and realtime Service Alerts |

OpenRouter model identifiers are configurable rather than permanently fixed.

All AI inference requests originate from the backend. Secret API credentials must not be exposed to the frontend.

### Local Execution

The MVP runs locally, with separate frontend and backend development servers.

SQLite provides lightweight local persistence when needed.

Do not introduce PostgreSQL/PostGIS, Redis, Celery, message queues, microservices, Kubernetes, mandatory Docker infrastructure, distributed caching, or background workers without an approved design change.

Infrastructure is introduced just in time, when the current functionality requires it.

## 4. Core Domain Contracts

The application operates on RouteLens-owned normalized models. External provider schemas must not propagate throughout the application.

### Journey and Routing

- `Location` — canonical selected place with coordinates and identifying information.
- `Trip` — origin, destination, travel mode, and associated journey context.
- `RouteCandidate` — approximate route geometry and descriptive information.
- `SelectedRoute` — user-chosen corridor used for geographic relevance.
- `TransitLeg` — ordered, user-selected transit service with authoritative identifiers and optional direction context.

### City Telemetry

- `CityEvent` — normalized construction, closure, road incident, or advisory, preserving relevant geometry and applicability information.
- `CameraIntersection` — Vancouver camera location and associated views.
- `CameraView` — directional camera image reference and retrieval context.
- `CameraObservation` — structured assessment of available directional views at one intersection.
- `WeatherObservation` — measured weather evidence, including source, location, time, and measurement semantics.
- `WeatherForecast` — structured forecast evidence for an appropriate location and future interval.
- `TransitAlert` — normalized GTFS-Realtime service advisory with affected-entity and temporal context.
- `TransitAlertMatch` — deterministic result describing applicability and specificity against user-selected transit services.

### Evidence and Analysis

- `SourceMetadata` — source identity, record provenance, and relevant timestamps.
- `SourceStatus` — availability, success/failure, freshness, and stale-source context.
- `JourneyBriefing` — structured, evidence-grounded AI synthesis.
- `JourneyAnalysis` — primary analysis result aggregating journey context, selected evidence, source statuses, timeline information, and briefing.

These are conceptual model contracts. Exact fields, relationships, and API schemas are defined or refined through the technical design and authorized implementation phases.

Do not independently alter established cross-component contracts.

## 5. Source Adapter Boundaries

Each external data source must have a clear adapter boundary.

Adapters are responsible for:

- external requests and source-specific access requirements;
- response validation;
- source-schema interpretation;
- normalization into RouteLens models;
- provenance and timestamp preservation;
- appropriate local error reporting.

Source-specific API field names and payload formats should remain isolated from general services, geospatial logic, frontend contracts, and LLM prompts.

Normal automated tests should use representative fixtures rather than relying on live upstream availability.

## 6. MVP Data-Source Contracts

The MVP has six external information-source groups.

### 6.1 Vancouver Traffic Webcams

Purpose: provide near-current visual conditions close to the destination.

Required behavior:

- Ingest the official geolocated Vancouver camera catalogue.
- Enrich catalogue records through official camera pages to discover directional image URLs.
- Find nearby camera intersections and select the nearest usable intersection.
- An intersection is usable when at least one valid current directional image can be retrieved.
- Retrieve all usable directional views from the selected intersection.
- Perform one combined multimodal assessment across the available views.
- Associate the assessment with the selected intersection and contributing views.

Camera AI may assess:

- visible precipitation;
- wet/dry-looking pavement;
- visibility, fog, haze, and glare;
- image quality and uncertainty.

Camera AI must not infer authoritative traffic speeds, congestion metrics, or precise meteorological measurements from images alone.

If no usable camera exists, report camera evidence as unavailable and continue using other sources.

Raw images are ephemeral/cache-only. Do not create a permanent historical image archive or repeated image time series.

Derived structured observations may be retained with provenance.

### 6.2 Vancouver Road Ahead

Purpose: construction, road restrictions, and municipal closures.

Use both official datasets:

- Current Road Closures.
- Projects Under Construction.

Required behavior:

- Preserve complete source geometry, including complex or multipart geometry.
- Normalize records conservatively; incomplete source fields remain incomplete.
- Use deterministic geometric matching for journey relevance.
- Distinguish direct geographic overlap from nearby contextual events.
- Selectively retrieve official detail pages for geographically relevant candidates.
- Parse detail-page information deterministically for schedules, restrictions, status, and other useful context.
- Do not use an LLM for raw webpage extraction.
- Preserve base dataset evidence if detail enrichment fails.

Both core datasets use an approximately 24-hour validated cache policy.

Refresh only when needed, validate replacement data, and retain the last valid cache if refresh fails. Mark stale fallback explicitly.

Detail-page enrichment is cached separately, with its precise TTL determined during implementation.

### 6.3 DriveBC Open511

Purpose: active regional road incidents, closures, and advisories.

Required behavior:

- Retrieve active events for a configured Greater Vancouver regional bounding box.
- Follow pagination until the relevant regional result set is complete.
- Cache the regional dataset rather than fetching separately for every selected route.
- Normalize events with usable geometry and provenance.
- Make regional events available for broad map exploration.
- Deterministically filter journey-specific candidates for automated insights and briefing.

The selected route must not hide other regional road events from the map.

The initial regional cache interval is approximately 5–15 minutes, subject to practical tuning.

Cross-source road-event handling should avoid misleading duplication without introducing an elaborate deduplication system.

### 6.4 ECCC GeoMet / SWOB

Purpose: supplementary measured weather observations.

Required behavior:

- Retrieve recent Vancouver-area observations.
- Group observations by station identifier.
- Validate timestamps and select recent useful observations.
- Preserve station coordinates, measurement semantics, and observation timestamps.
- Use station-catalogue metadata where available without requiring every station to exist in that catalogue.
- Select useful evidence based on proximity, freshness, and available measurements.

Important interpretation constraints:

- Missing precipitation does not mean zero precipitation.
- Zero accumulated precipitation at one station does not prove nearby areas are dry.
- Previous precipitation does not prove rain is falling now.
- Sparse stations must not be used for unsupported neighborhood-scale interpolation.

The initial cache interval is approximately 10–15 minutes and remains provisional.

SWOB supports weather interpretation; it is not the sole weather source.

### 6.5 OpenWeather

Purpose: structured current conditions and near-term forecast information for the journey/destination.

Required behavior:

- Obtain coordinate-based current and near-term weather data.
- Normalize conditions and forecast intervals separately from measured SWOB observations.
- Preserve observation/forecast timestamps and source attribution.
- Represent unavailable fields and unsupported lookahead intervals as unknown.

The exact accessible endpoints, schemas, forecast granularity, cache policy, and practical sampling strategy remain subject to live validation.

Do not invent endpoint capabilities or assume desired fields exist before verification.

OpenWeather provides the structured weather foundation; SWOB contributes measured station observations; cameras contribute visual evidence.

These three evidence types must retain separate provenance even when synthesized into one briefing.

### 6.6 TransLink GTFS Static + GTFS-Realtime

Purpose: allow users to select intended transit services and identify applicable service advisories.

**GTFS Static**

- Build route lookup from official GTFS identifiers and passenger-friendly names.
- Support bus routes and SkyTrain lines.
- Derive direction/headsign options using relevant trip information.
- Preserve route identifiers and selected direction context.
- Do not interpret numeric `direction_id` values as universal compass directions.
- Allow users to construct an ordered list of intended transit legs.

**GTFS-Realtime**

The MVP uses **Service Alerts only**.

- Fetch and decode the official Protocol Buffer alert feed.
- Normalize affected entities, time periods, and advisory content.
- Match alerts deterministically against selected GTFS identifiers.
- Preserve the specificity of route-wide, direction-specific, stop-specific, and trip-specific selectors.
- Exclude alerts explicitly applicable only to the opposite selected direction.
- Do not promote stop-specific notices into route-wide disruptions.
- Do not assume trip-specific applicability without sufficient journey information.
- Respect active periods and temporal uncertainty.

Matching should distinguish confirmed applicability from possible or unresolved relevance.

Do not infer exact delays, arrival times, or service reliability when the source does not support those claims.

Trip Updates, Vehicle Positions, exact trip resolution, and realtime vehicle tracking are outside MVP scope.

Transit advisories primarily appear in the journey intelligence panel; transit network map overlays are not required.

## 7. Deterministic Journey Relevance

Deterministic application logic owns source discovery, normalization, filtering, and relevance.

### Geographic Relevance

Use Shapely and appropriate coordinate projection for distance-based calculations.

- Do not use unprojected longitude/latitude degrees as metre distances.
- Match road-event geometries against the selected approximate corridor.
- Distinguish direct overlaps from proximity-based supplemental context.
- Preserve directly applicable events rather than losing them to ordinary candidate limits.
- Prioritize useful, timely evidence without claiming every nearby event affects the journey.

### Temporal Relevance

- Use source timestamps and known applicability periods.
- Preserve unknown schedules and missing time values.
- Do not treat missing schedules as continuous active restrictions.
- Distinguish current, future, expired, stale, and uncertain evidence where supported.

### Transit Relevance

Transit service matching uses official GTFS identifiers, selector specificity, user-selected direction, and temporal applicability.

Geographic proximity is not a substitute for transit-service matching.

### Map Visibility vs Briefing Relevance

These are separate concerns:

- The map may expose broadly relevant regional telemetry.
- The automated briefing should receive only selected, journey-relevant evidence.
- Transit advisories may qualify for the briefing without corresponding geographic map overlays.

The selected corridor prioritizes interpretation; it must not unnecessarily suppress nearby map exploration.

## 8. AI Responsibilities and Boundaries

RouteLens uses OpenRouter for two distinct AI capabilities.

### Camera Multimodal Assessment

Input:

- available directional images from one selected Vancouver intersection;
- associated image/view context.

Output:

- structured `CameraObservation`;
- conservative visual interpretation;
- uncertainty and image-quality indicators;
- contributing-view provenance.

Perform one combined assessment for the selected intersection rather than independent full inference calls per directional view.

Do not present visual inference as direct instrument measurement.

### Journey Briefing

Input:

- normalized, deterministically selected evidence;
- journey context;
- source freshness and uncertainty;
- relevant observations and advisories.

Output:

- concise, readable journey intelligence;
- destination and route conditions;
- significant issues and useful expectations;
- uncertainty where evidence is weak, missing, stale, or conflicting.

The briefing should not fabricate incidents, precipitation, travel delays, or unsupported causal relationships.

An uneventful journey is a valid result. Do not manufacture warnings merely to make the briefing appear useful.

### Prohibited AI Responsibilities

The LLM must not perform first-pass:

- route generation or route optimization;
- geographic intersection or distance matching;
- source pagination or event discovery;
- camera intersection selection;
- camera directional-view discovery;
- GTFS route/direction resolution;
- transit alert selector matching;
- source freshness determination;
- missing-data substitution;
- deterministic webpage extraction.

AI interprets and synthesizes already-selected evidence.

Structured AI outputs must be validated by the backend.

## 9. Data Integrity, Freshness, and Reliability

### Provenance

Normalized records and derived findings must preserve sufficient metadata to identify:

- original source and source record;
- observation/publication time where available;
- retrieval time;
- relevance or matching basis;
- freshness and availability;
- applicable attribution context.

AI-generated findings must not erase underlying evidence provenance.

### Missing and Conflicting Evidence

**Missing means unknown.**

Do not interpret missing measurements, absent transit updates, unavailable images, or failed API responses as evidence of normal conditions.

When evidence conflicts, preserve the differing sources and express appropriate uncertainty rather than arbitrarily declaring certainty.

### Caching

Use source-specific cache policies.

For refreshable structured sources:

1. Check whether a valid cache exists.
2. Reuse it while fresh.
3. Refresh when required.
4. Validate incoming data before replacement.
5. Replace valid cached data only after successful validation.
6. Retain the previous valid cache on refresh failure where appropriate.
7. Surface stale fallback and age through source status.

Different data sources do not need identical cache implementations.

### Failure Isolation

Each external integration is independently fallible.

- Use explicit HTTP timeouts.
- Handle expected source failures locally.
- Preserve usable evidence from successful sources.
- Return partial journey analysis where possible.
- Expose unavailable/stale sources to the frontend.
- Do not silently swallow unexpected programming errors.

A single unavailable source should not normally invalidate the entire journey analysis.

## 10. Frontend and Presentation Contract

### Desktop Layout

The MVP is desktop-only.

Primary layout:

- **Top:** origin, destination, travel mode, relevant transit selections, and analysis action.
- **Left (~65%):** interactive MapLibre map.
- **Right (~35%):** journey intelligence panel.

Use a dark, polished city-intelligence visual style with a low-clutter MapTiler basemap.

Telemetry overlays and journey information should remain visually prominent.

### Information Hierarchy

Prioritize:

1. Destination camera/current conditions.
2. Overall journey status.
3. Route-related issues.
4. Transit advisories where applicable.
5. Supporting telemetry, provenance, and source freshness.

The panel may present a journey overview, destination conditions, along-route findings, timeline, and AI briefing.

Do not overwhelm users with every available source record.

### Interaction Principles

- Use familiar autocomplete and clear selection states.
- Make route candidates explicitly approximate.
- Allow exploration of surrounding geographic telemetry.
- Distinguish selected/relevant events from broader map context.
- Display loading, empty, stale, and partial-failure states clearly.
- Make uncertainty and unavailable evidence visible without overwhelming successful results.
- Preserve readable visual hierarchy and restrained animation.

Exact styling, component organization, and motion details remain implementation-flexible within this design.

Human review retains authority over visual quality and presentation acceptance.

## 11. Data Use and Licensing Constraints

RouteLens uses information from sources with different licence and contractual conditions.

Preserve clear boundaries between sources.

### Government Open Data

Vancouver Road Ahead, Vancouver webcam metadata, DriveBC Open511, and ECCC SWOB have applicable open-government-data licensing foundations.

- Preserve provenance and attribution information.
- Respect applicable source conditions.
- Keep data transformations traceable.

### Vancouver Camera Images

Camera metadata and image assets have distinct rights considerations.

- Treat raw directional JPEGs as ephemeral/cache-only.
- Do not create a historical image archive.
- Do not redistribute images as a standalone image dataset or service.
- Do not accumulate images for model training.
- Preserve provenance for derived camera observations.

Ephemeral use reduces retention exposure but does not independently establish unrestricted display, proxying, AI processing, or commercialization rights.

### TransLink and OpenWeather

These sources have additional contractual and attribution considerations.

- Keep their provider-specific handling isolated.
- Respect API access and usage limits.
- Preserve applicable attribution.
- Avoid assuming unrestricted redistribution or commercialization rights.

Do not build a separately redistributed weather database or transit data product as part of the MVP.

### Deployment Boundary

The approved MVP is a local/portfolio application.

Public or commercial deployment requires review of current provider terms, attribution obligations, and image/AI processing rights.

Detailed research and unresolved legal questions remain in `docs/data-licensing-and-commercialization.md`.

## 12. Explicit MVP Non-Goals

Do not implement the following without an approved scope change:

**Navigation and transit planning**
- Turn-by-turn navigation or authoritative route optimization.
- Exact Google Maps route reproduction.
- Full transit itinerary planning, automatic transfers, exact boarding/alighting stops, or exact trip prediction.
- Vehicle Positions, Trip Updates, or realtime vehicle tracking.
- Transit network/stop map overlays.

**Accounts and product expansion**
- User accounts, authentication, or persistent user profiles.
- Saved journeys, recurring monitoring, or push notifications.
- Mobile/responsive-mobile implementation.
- Walking or cycling modes.
- Trips whose destination is outside the City of Vancouver.

**Advanced telemetry and AI**
- DriveBC Cameras.
- ECCC weather radar, Vancouver 311, Metro Vancouver AirMap, or other deferred datasets.
- Multiple Vancouver camera intersections per journey.
- Historical camera archives or camera time-series analysis.
- Camera-based traffic-speed measurement.
- Weather-station interpolation or citywide weather interpolation.
- Complex cross-source road-event deduplication.
- Citywide traffic simulation or digital twins.

**Unnecessary infrastructure**
- Distributed services, complex worker systems, cloud infrastructure, or heavyweight databases not required by the local MVP.

Deferred ideas may remain in planning documents but must not be implemented merely because they are documented.

## 13. Specification Authority and Evolution

This document is a condensed operational specification, not a replacement for the authoritative planning artifacts.

| Document | Authority |
|---|---|
| `docs/prd.md` | Product behavior, scope, requirements, non-goals |
| `docs/technical-design.md` | Technical architecture, detailed contracts, source handling |
| `docs/implementation-plan.md` | Overall development roadmap and phase ordering |
| `docs/development-workflow.md` | Development roles, process, and verification philosophy |
| `docs/data-licensing-and-commercialization.md` | Source rights research and commercialization considerations |
| `AGENTS.md` | Codex operating rules and authority boundaries |
| `BUILD_PLAN.md` | Current authorized implementation assignment |
| `PROJECT_STATE.md` | Actual repository state and verified implementation facts |

If this specification conflicts materially with an authoritative planning document, report the discrepancy instead of silently overriding either source.

If implementation reveals facts requiring changes to product intent, architecture, source strategy, or scope, escalate the discovery for human/planning review.

Update this specification deliberately when approved design decisions change.

**Implementation reality does not automatically redefine intended architecture.**
