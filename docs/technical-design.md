# RouteLens AI — Technical Design

## 1. Purpose

This document defines the technical architecture for the RouteLens AI MVP.

The Product Requirements Document defines **what RouteLens must do and why**.

This technical design defines **how the MVP will implement those requirements**.

The design intentionally prioritizes:

- small architecture;
- rapid iteration;
- clear component boundaries;
- deterministic relevance logic;
- source-specific data handling;
- graceful degradation;
- easy local development;
- presentation quality;
- compatibility with coding-agent-assisted implementation.

The MVP is a local desktop web application.

Public deployment is not required.

---

# 2. High-Level Architecture

RouteLens consists of:

- a React frontend;
- a FastAPI backend;
- lightweight local persistence;
- geospatial route-relevance logic;
- source-specific public-data adapters;
- source-specific cache policies;
- a Vancouver camera catalogue-enrichment pipeline;
- ephemeral camera-image caching;
- deterministic transit-service matching;
- OpenRouter-backed AI inference.

High-level flow:

```text
User
 │
 ▼
React / Vite frontend
 │
 │ origin / destination / mode
 │ selected route
 │ optional transit-service selections
 ▼
FastAPI backend
 │
 ├── MapTiler geocoding/autocomplete
 ├── openrouteservice routing
 │
 ▼
Canonical Trip / Selected Route
 │
 ▼
Journey Analysis Orchestrator
 │
 ├── Vancouver webcams
 ├── Vancouver Road Ahead
 ├── DriveBC Open511
 ├── ECCC SWOB
 ├── OpenWeather
 └── TransLink GTFS Static + Service Alerts
 │
 ▼
Validation / Normalization / Provenance
 │
 ▼
Deterministic Relevance
 │
 ├── geospatial matching
 ├── temporal applicability
 ├── transit route/direction matching
 └── freshness / source status
 │
 ▼
Destination Camera Selection
 │
 ▼
Directional Image Fetch
 │
 ▼
OpenRouter Multimodal Assessment
 │
 ▼
Structured Journey Evidence
 │
 ▼
OpenRouter Journey Briefing
 │
 ▼
JourneyAnalysis response
 │
 ▼
Map + Journey Intelligence UI
```

---

# 3. Architectural Principles

## 3.1 Routing Is Context, Not the Product

RouteLens does not own route optimization.

Routing exists to define an approximate geographic corridor for telemetry relevance.

The application must not drift toward becoming:

- a navigation application;
- a route optimizer;
- a turn-by-turn directions system;
- a transit itinerary planner.

---

## 3.2 Normalize External Data Early

External schemas must remain isolated inside source adapters.

The rest of the application should operate on RouteLens-owned normalized models.

Avoid spreading upstream API field names and response structures throughout:

- services;
- geospatial logic;
- database code;
- frontend API contracts;
- LLM prompts.

---

## 3.3 Deterministic Logic Before AI

AI does not decide:

- what route is relevant;
- which road event intersects the route;
- which camera is nearest;
- which camera image directions exist;
- whether a source is fresh;
- which transit route ID the user selected;
- whether an alert selector matches the selected service;
- whether a source value is missing.

Those responsibilities belong to deterministic code.

AI receives a compact, already-filtered evidence set.

---

## 3.4 Preserve Provenance

Normalized data must retain enough metadata to answer:

- where did this fact come from?
- what source record produced it?
- when was it observed or published?
- when did RouteLens retrieve it?
- why was it selected as relevant?
- is the source fresh, stale, or unavailable?

Normalization must not erase provenance.

---

## 3.5 Missing Means Unknown

Missing values must not be silently interpreted as normal or zero.

Examples:

- missing precipitation is not zero precipitation;
- missing transit direction is not a known direction;
- missing schedule is not 24-hour applicability;
- absent delay information is not on-time service;
- unavailable imagery is not evidence of clear weather.

Unknown values remain unknown.

---

## 3.6 Partial Success

Every external integration is independently fallible.

One failed source must not invalidate the entire analysis unless the failure makes the core journey impossible to evaluate.

The orchestrator should return:

- successful source results;
- failed source statuses;
- stale source statuses where applicable;
- a usable `JourneyAnalysis` where possible.

---

## 3.7 Validated Cache Replacement

For cacheable feeds:

1. retain the last valid cache;
2. fetch new data when stale;
3. validate the new payload;
4. only replace the old cache after validation succeeds;
5. preserve the previous valid cache if refresh fails;
6. expose stale age to the application.

Prefer atomic replacement where practical.

---

## 3.8 Map Coverage and Briefing Relevance Are Separate

A record may appear on the map without qualifying for the journey briefing.

Examples:

- an Open511 incident elsewhere in Metro Vancouver may appear on the regional map;
- only events relevant to the selected journey become briefing candidates.

Likewise, transit alerts may be highly relevant to the briefing without any transit map visualization.

---

## 3.9 Simplicity Over Infrastructure

The MVP deliberately avoids infrastructure that is not required.

Not planned:

- PostgreSQL;
- PostGIS;
- Redis;
- Celery;
- Docker requirements;
- message queues;
- microservices;
- Kubernetes;
- background workers;
- distributed caching;
- cloud observability stacks.

---

# 4. Technology Stack

## 4.1 Frontend

Locked frontend stack:

- React;
- Vite;
- TypeScript;
- Tailwind CSS;
- MapLibre;
- Framer Motion;
- Lucide.

Responsibilities:

- user input;
- autocomplete UI;
- route candidate selection;
- transit-service selection;
- map rendering;
- telemetry visualization;
- journey intelligence panel;
- destination-camera presentation;
- animation / transitions;
- loading states;
- partial-failure presentation;
- source freshness presentation.

No component library is initially required.

Libraries such as shadcn/ui should only be introduced if a concrete need arises.

---

## 4.2 Backend

Locked backend stack:

- Python;
- FastAPI;
- Pydantic;
- httpx;
- SQLAlchemy;
- SQLite;
- Shapely;
- pytest;
- Ruff.

Additional lightweight libraries may be introduced where clearly justified, for example:

- GTFS-Realtime Protocol Buffer decoding;
- HTML parsing for deterministic Road Ahead detail-page enrichment.

Responsibilities:

- external API access;
- source normalization;
- routing/geocoding coordination;
- source-specific cache management;
- geospatial relevance;
- transit selector matching;
- camera-catalogue enrichment;
- camera selection;
- image proxy/cache;
- AI calls;
- journey analysis orchestration;
- persistence;
- structured API responses.

---

## 4.3 Mapping

Locked:

- MapLibre for rendering;
- MapTiler for basemap/style;
- MapTiler for geocoding/autocomplete.

The basemap should use a dark, low-clutter style.

RouteLens overlays must visually dominate the basemap.

---

## 4.4 Routing

Locked routing provider:

- openrouteservice.

Primary use:

- generate plausible drive-route geometry;
- return up to three candidate routes where available.

RouteLens does not expect exact Google Maps parity.

Transit mode may still use an approximate generic corridor, but no transit-routing engine is required.

---

## 4.5 AI

Locked inference gateway:

- OpenRouter.

Specific models are intentionally not fixed.

Separate models may be selected for:

### Vision

Optimized for:

- multiple directional camera images in one request;
- structured JSON output;
- conservative visual interpretation;
- low latency;
- acceptable cost.

### Text

Optimized for:

- concise synthesis;
- structured journey briefing;
- evidence-grounded output;
- readable recommendations.

All OpenRouter calls must originate from the backend.

No AI API key may be exposed to the frontend.

---

# 5. Local Execution Model

The MVP is designed for local execution.

Development model:

```text
frontend/
  Vite dev server

backend/
  FastAPI / uvicorn
```

The frontend and backend run separately during development.

Example:

```text
Frontend:
http://localhost:5173

Backend:
http://localhost:8000
```

The frontend calls backend `/api/...` endpoints.

A later simple packaging option may allow FastAPI to serve the built frontend.

That is optional and not required for initial development.

---

# 6. Repository Structure

Recommended structure:

```text
RouteLens/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── sources/
│   │   ├── services/
│   │   ├── db/
│   │   ├── core/
│   │   └── main.py
│   │
│   ├── scripts/
│   │   └── enrich_vancouver_cameras.py
│   │
│   ├── tests/
│   │   ├── fixtures/
│   │   ├── unit/
│   │   └── integration/
│   │
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── map/
│   │   ├── services/
│   │   ├── types/
│   │   ├── hooks/
│   │   └── styles/
│   │
│   ├── index.html
│   └── package.json
│
├── data/
│   ├── cache/
│   │   ├── cameras/
│   │   └── sources/
│   └── catalogs/
│       └── vancouver_cameras.json
│
├── docs/
│   ├── prd.md
│   ├── technical-design.md
│   ├── implementation-plan.md
│   ├── development-workflow.md
│   └── data-licensing-and-commercialization.md
│
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

This structure is recommended, not immutable.

Do not add directories or abstraction layers without a concrete need.

---

# 7. Core Domain Models

The application should define a small normalized model family.

Conceptual models include:

- `Location`
- `Trip`
- `RouteCandidate`
- `SelectedRoute`
- `TransitLeg`
- `CityEvent`
- `CameraIntersection`
- `CameraView`
- `CameraObservation`
- `WeatherObservation`
- `WeatherForecast`
- `TransitAlert`
- `TransitAlertMatch`
- `SourceStatus`
- `SourceMetadata`
- `JourneyBriefing`
- `JourneyAnalysis`

Exact structures may evolve during implementation.

Source-specific raw payloads remain inside adapters or cache storage.

---

# 8. SourceMetadata Model

Normalized records should retain provenance.

Conceptual:

```python
class SourceMetadata(BaseModel):
    source: str
    source_id: str | None = None
    source_url: str | None = None

    observed_at: datetime | None = None
    updated_at: datetime | None = None
    fetched_at: datetime

    stale: bool = False
```

Additional fields may include:

- source licence identifier;
- raw-asset persistence policy;
- relevance reason.

The exact licensing fields may remain documentation-only for MVP if implementation overhead is not justified.

---

# 9. Location Model

Conceptual:

```python
class Location(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str | None = None
    provider_id: str | None = None
```

Responsibilities:

- canonical origin/destination representation;
- geocoding result;
- map placement;
- destination validation.

---

# 10. Trip Model

Conceptual:

```python
class Trip(BaseModel):
    origin: Location
    destination: Location
    mode: Literal["drive", "transit"]
    selected_route: SelectedRoute

    transit_legs: list[TransitLeg] = []

    estimated_duration_seconds: int | None = None
    estimated_arrival_at: datetime | None = None
```

The downstream system should operate on this model regardless of how origin/destination were entered.

Transit legs are populated only for Transit mode.

---

# 11. RouteCandidate Model

Conceptual:

```python
class RouteCandidate(BaseModel):
    id: str
    geometry: dict
    distance_meters: float | None
    duration_seconds: int | None
    label: str | None
```

The geometry should use a consistent GeoJSON-compatible representation.

Driving mode may expose up to three candidates.

---

# 12. SelectedRoute Model

Conceptual:

```python
class SelectedRoute(BaseModel):
    candidate_id: str
    geometry: dict
    mode: Literal["drive", "transit"]
```

The route geometry is used to produce a Shapely line and buffered relevance corridor.

---

# 13. TransitLeg Model

Conceptual:

```python
class TransitLeg(BaseModel):
    order: int

    route_id: str
    route_short_name: str | None
    route_long_name: str | None

    route_type: int | None

    direction_id: int | None
    direction_label: str | None
```

The UI exposes human-friendly names.

The backend preserves GTFS identifiers.

Exact boarding/exiting stops are not required for MVP.

---

# 14. CityEvent Model

Normalized structure for:

- construction;
- closures;
- incidents;
- maintenance;
- related road events.

Conceptual:

```python
class CityEvent(BaseModel):
    id: str
    source: str
    event_type: str

    title: str
    description: str | None

    geometry: dict | None
    latitude: float | None
    longitude: float | None

    severity: str | None
    status: str | None

    schedule_text: str | None
    restriction_text: str | None

    observed_at: datetime | None
    updated_at: datetime | None

    source_url: str | None

    relevance_reason: str | None
```

The application must not depend on source-specific event field names after normalization.

Source-specific fields may remain available internally when needed during enrichment.

---

# 15. CameraIntersection Model

The Vancouver camera dataset represents camera intersections rather than a single normalized image per camera.

Conceptual:

```python
class CameraIntersection(BaseModel):
    id: str
    source: str

    name: str

    latitude: float
    longitude: float

    page_url: str

    views: list[CameraView]

    metadata_fetched_at: datetime | None
```

An intersection may expose multiple directional image views.

---

# 16. CameraView Model

Conceptual:

```python
class CameraView(BaseModel):
    id: str
    direction: str | None

    upstream_image_url: str
    local_image_url: str | None

    fetched_at: datetime | None
    captured_at: datetime | None

    usable: bool = True
```

Directional labels should come from page extraction where possible rather than being guessed from URL naming conventions.

---

# 17. CameraObservation Model

The multimodal model produces one combined observation for the selected intersection.

Conceptual:

```python
class CameraObservation(BaseModel):
    camera_intersection_id: str
    analyzed_at: datetime

    view_ids: list[str]

    precipitation_visible: bool | None
    precipitation_type: str | None

    road_surface: str | None
    visibility: str | None

    image_quality: str | None
    confidence: float | None
    notes: str | None
```

Traffic density may be added if useful, but it is not a core MVP requirement.

Values should be conservative.

Unknown or unclear values should remain `None` or explicit uncertainty rather than being invented.

---

# 18. WeatherObservation Model

Used for ECCC SWOB.

Conceptual:

```python
class WeatherObservation(BaseModel):
    station_id: str
    source: str

    latitude: float
    longitude: float

    observed_at: datetime

    temperature_c: float | None

    precipitation_10min_mm: float | None
    precipitation_hourly_mm: float | None

    humidity_pct: float | None

    wind_speed_kph: float | None
    wind_direction_deg: float | None

    visibility_km: float | None
    snow_depth_cm: float | None

    source_metadata: SourceMetadata
```

Only fields required by the product should be normalized.

Do not model the entire SWOB schema unless necessary.

Missing measurements remain `None`.

---

# 19. WeatherForecast Model

Used for OpenWeather current/near-term weather.

Conceptual:

```python
class WeatherForecast(BaseModel):
    source: str
    location: Location

    forecast_at: datetime

    temperature_c: float | None
    precipitation_probability_pct: float | None
    precipitation_amount_mm: float | None
    precipitation_type: str | None
    wind_speed_kph: float | None

    summary: str | None

    source_metadata: SourceMetadata
```

The final fields depend on actual OpenWeather API exploration.

Do not implement fields that the selected endpoint does not provide.

---

# 20. TransitAlert Model

Conceptual:

```python
class TransitAlert(BaseModel):
    id: str
    source: str

    header: str
    description: str | None
    url: str | None

    cause: str | None
    effect: str | None

    active_periods: list[dict]

    selectors: list[dict]

    source_metadata: SourceMetadata
```

The normalized model must preserve enough selector detail to distinguish:

- route-level;
- direction-specific;
- stop-specific;
- trip-specific

scope.

Do not flatten these distinctions away.

---

# 21. TransitAlertMatch Model

Matching results should be represented separately from the raw normalized alert.

Conceptual:

```python
class TransitAlertMatch(BaseModel):
    alert_id: str

    matched_leg_order: int

    match_scope: Literal[
        "route",
        "route_direction",
        "stop_specific",
        "trip_specific",
    ]

    match_strength: str

    reason: str

    temporally_applicable: bool | None
```

This allows the LLM to receive both:

- the alert;
- why RouteLens considered it relevant.

---

# 22. SourceStatus Model

Each external source should report its own state.

Conceptual:

```python
class SourceStatus(BaseModel):
    source: str

    success: bool
    fetched_at: datetime | None

    cache_hit: bool = False
    stale: bool = False

    cache_age_seconds: int | None = None

    error: str | None = None
```

This supports:

- partial success;
- stale-data fallback;
- troubleshooting;
- UI status;
- logging.

---

# 23. JourneyBriefing Model

Locked structure:

```python
class JourneyBriefing(BaseModel):
    status: str
    summary: str
    highlights: list[str]
    recommendation: str | None
```

Possible status values:

- `clear`
- `minor_conditions`
- `attention`
- `disrupted`

Exact enum values may be refined during implementation.

The frontend should not depend on a raw prose blob.

---

# 24. JourneyAnalysis Model

Primary API result.

Conceptual:

```python
class JourneyAnalysis(BaseModel):
    trip: Trip

    selected_camera: CameraIntersection | None
    camera_observation: CameraObservation | None

    construction_events: list[CityEvent]
    road_events: list[CityEvent]

    weather_observations: list[WeatherObservation]
    weather_forecasts: list[WeatherForecast]

    transit_alerts: list[TransitAlert]
    transit_matches: list[TransitAlertMatch]

    timeline_events: list[dict]

    briefing: JourneyBriefing | None

    source_statuses: list[SourceStatus]
```

Additional fields may be introduced where justified.

---

# 25. Source Adapter Architecture

Every external source should be isolated behind its own adapter or ingestion module.

Recommended directory:

```text
backend/app/sources/
├── vancouver_cameras.py
├── road_ahead.py
├── drivebc_open511.py
├── eccc_swob.py
├── translink_static.py
├── translink_realtime.py
├── openweather.py
├── maptiler.py
└── openrouteservice.py
```

DriveBC camera integration is not part of the MVP.

Each source module should follow the same conceptual pattern where applicable:

```text
fetch
  ↓
validate upstream response
  ↓
normalize
  ↓
preserve provenance
  ↓
return normalized models
  ↓
report source status
```

Some sources additionally require:

- catalogue enrichment;
- pagination;
- HTML detail enrichment;
- Protocol Buffer decoding.

---

# 26. Source Adapter Contract

Every adapter should:

1. own its upstream URL/API details;
2. own authentication requirements;
3. use configured timeout settings;
4. use source-appropriate caching;
5. validate upstream data;
6. normalize into RouteLens models;
7. preserve provenance;
8. expose freshness;
9. distinguish missing data from zero/default values;
10. report failure without crashing the orchestrator;
11. avoid leaking raw source schema into unrelated modules.

A formal inheritance hierarchy is optional.

Avoid unnecessary abstraction if simple modules/functions are clearer.

---

# 27. MapTiler Integration

MapTiler provides:

- autocomplete;
- geocoding;
- basemap/style.

Frontend interaction:

```text
typed query
   ↓
frontend/backend MapTiler integration
   ↓
suggestions
   ↓
user selects result
   ↓
canonical Location
```

Requirements:

- destination must be validated as inside Vancouver;
- API-key handling should follow MapTiler's supported model;
- sensitive credentials must not be exposed unnecessarily.

---

# 28. Vancouver Destination Validation

The backend should enforce destination support.

Do not rely solely on frontend checks.

Possible implementations:

- City of Vancouver boundary polygon;
- bounding box plus administrative metadata;
- geocoder administrative result.

Preferred:

> use a simple City of Vancouver polygon/boundary check if easily available.

If implementation cost is disproportionate, a practical geographic approximation is acceptable for MVP.

The check must remain deterministic.

---

# 29. Driving Route Generation

For Drive mode:

```text
origin
 + destination
      ↓
openrouteservice
      ↓
1–3 candidate routes
      ↓
frontend displays candidates
      ↓
user selects closest match
```

Requirements:

- return up to three routes where possible;
- allow one route when alternatives are unavailable;
- normalize route geometry;
- visually distinguish selected/unselected candidates.

---

# 30. Transit Corridor Generation

Transit mode does not reconstruct real transit routing.

Instead:

```text
origin
 + destination
      ↓
approximate geographic corridor
      ↓
road/weather/camera context
      +
user-selected GTFS services
      ↓
TransLink Service Alert matching
```

The approximate corridor is for environmental/geographic context.

It must not be used as the sole mechanism for transit-alert matching.

---

# 31. Geospatial Engine

Locked library:

- Shapely.

Responsibilities:

- route geometry conversion;
- route buffers;
- distance to route;
- distance to destination;
- geometry intersection;
- road-event relevance;
- camera-intersection proximity.

No geospatial database is required.

---

# 32. Coordinate Projection for Distance Operations

Road Ahead and Open511 source geometries may arrive in geographic longitude/latitude coordinates.

Accurate meter-based distance calculations should use a suitable projected coordinate system.

Preferred approach:

- convert relevant geometries from WGS84 into an appropriate local projected CRS;
- use a Vancouver-region UTM projection where practical.

Do not treat raw latitude/longitude degrees as metres.

Shapely performs geometry operations; coordinate transformation may use an appropriate lightweight projection library if required.

---

# 33. Route Buffer

Concept:

```text
route geometry
      ↓
project coordinates
      ↓
Shapely LineString
      ↓
buffer(radius_meters)
      ↓
route relevance polygon
```

Different sources may use different configured radii.

Exact values remain implementation-tunable.

Direct intersections must be identified separately from nearby supplemental events.

---

# 34. Direct Overlap Preservation

For road events:

```text
all direct route overlaps
        +
top N supplemental nearby events
```

Direct overlaps must not be discarded merely because more than N exist.

This is especially important for Road Ahead.

Candidate limits should be applied primarily to non-intersecting nearby features.

---

# 35. General Relevance Scoring

MVP scoring should remain deterministic.

Potential factors:

- direct intersection;
- distance;
- distance to destination;
- freshness;
- source-reported severity;
- temporal applicability;
- affected direction;
- source type;
- travel mode.

Conceptual:

```text
direct overlap
     ↓
strong relevance

nearby candidate
     ↓
distance
+ freshness
+ severity
+ schedule
+ direction
```

No ML ranking is required.

---

# 36. Vancouver Camera Catalogue Ingestion

The City dataset provides camera intersection metadata including:

- ID;
- name;
- page URL;
- coordinates.

It does not necessarily provide the final directional JPEG URLs required for image analysis.

Therefore RouteLens uses a two-stage catalogue process.

---

# 37. Camera Catalogue Enrichment Script

A standalone script should:

1. download the official Vancouver camera metadata dataset;
2. validate records;
3. visit each camera webpage;
4. parse the actual directional image URLs from the page;
5. identify direction labels where available;
6. validate image responses;
7. tolerate missing/broken directions;
8. produce an enriched local catalogue.

Conceptual:

```text
City camera dataset
      ↓
intersection metadata
      ↓
visit each camera page
      ↓
extract actual image URLs
      ↓
validate image availability
      ↓
write enriched camera catalogue
```

Do **not** guess image URLs from naming conventions.

---

# 38. Camera Catalogue Refresh

The enriched camera catalogue is not rebuilt for every journey.

Initial policy:

- check catalogue age;
- refresh infrequently;
- approximately 24 hours is a reasonable initial TTL.

This interval is provisional.

The catalogue should retain the last valid version if refresh/enrichment fails.

---

# 39. Destination Camera Selection

MVP selection logic:

```text
destination
   ↓
nearby camera intersections
   ↓
sort by distance
   ↓
check nearest candidate
   ↓
usable directional images?
   ├── yes → select
   └── no  → try next nearest
```

The result is:

> one nearest usable camera intersection.

The MVP does not automatically analyze multiple intersections.

---

# 40. Directional Camera Views

Once an intersection is selected:

1. retrieve all known directional views;
2. validate image responses;
3. keep usable images;
4. pass all usable images to one multimodal request.

Typical intersections may expose 2–4 images.

The system must tolerate fewer.

---

# 41. Camera Image Proxy

The backend should proxy camera imagery.

Frontend flow:

```text
React
  ↓
RouteLens camera-image endpoint
  ↓
FastAPI
  ↓
ephemeral local cache
  ↓
upstream Vancouver JPEG
```

Benefits:

- avoids CORS issues;
- ensures UI and AI use the same frame;
- centralizes validation;
- isolates upstream URLs;
- supports ephemeral storage policy.

---

# 42. Camera Image Cache

Camera images are ephemeral.

Suggested layout:

```text
data/cache/cameras/{intersection_id}/{view_id}.jpg
```

Behavior:

```text
journey analysis
      ↓
fetch current directional views
      ↓
validate image responses
      ↓
overwrite existing cached frame
      ↓
display + analyze
```

No historical archive.

A new journey may fetch fresh frames according to source freshness policy.

Repeated high-frequency polling is not required.

---

# 43. Camera Cache Metadata

SQLite may store:

- intersection ID;
- view ID;
- fetched timestamp;
- capture timestamp if known;
- file path;
- upstream URL metadata;
- latest analysis timestamp.

Raw image binaries do not need to be stored in SQLite.

---

# 44. Multi-View Camera Analysis Pipeline

Flow:

```text
selected camera intersection
       ↓
fetch all usable current views
       ↓
temporary cache
       ↓
one constrained multimodal request
       ↓
structured JSON
       ↓
Pydantic validation
       ↓
CameraObservation
       ↓
persist normalized observation
```

The model should be explicitly instructed to:

- evaluate all supplied views together;
- describe observable evidence only;
- distinguish wet pavement from active rainfall;
- return unknown/null where unclear;
- note image-quality limitations;
- avoid identifying individuals;
- avoid unsupported meteorological certainty.

---

# 45. Camera Structured Output

Target contract:

```json
{
  "precipitation_visible": true,
  "precipitation_type": "rain",
  "road_surface": "wet",
  "visibility": "good",
  "image_quality": "usable",
  "confidence": 0.84,
  "notes": "Wet pavement is visible across multiple views; light falling precipitation may be visible in one view."
}
```

The backend must validate output before storing or returning it.

Invalid AI output should:

- be logged;
- fail gracefully;
- not break journey analysis.

---

# 46. Road Ahead Data Sources

Road Ahead uses two official datasets:

- Current Road Closures;
- Projects Under Construction.

Both should be ingested.

The datasets may contain:

- `LineString`;
- `MultiLineString`;
- `GeometryCollection`;
- representative point coordinates;
- project/location metadata;
- detail-page URLs.

The complete geometry should be preserved.

---

# 47. Road Ahead Dataset Cache

Locked initial policy:

> approximately 24-hour refresh.

Workflow:

```text
source requested
      ↓
valid cache exists?
      ↓
fresh (<24h)?
  ├── yes → use
  └── no
        ↓
     download
        ↓
     validate
        ↓
valid?
 ├── yes → atomically replace cache
 └── no  → retain last valid cache
```

If stale fallback is used, expose it through `SourceStatus`.

No portal modification-date checker is required.

---

# 48. Road Ahead Normalization

The dataset record is sufficient for:

- map geometry;
- candidate discovery;
- basic labels;
- source provenance.

Do not assume:

- `street` is always populated;
- `project` is always complete;
- `location` is always complete;
- `comp_date` is the authoritative final applicability date.

Normalize conservatively.

---

# 49. Road Ahead Detail-Page Enrichment

For geographically relevant candidates, RouteLens may fetch the source detail page.

Deterministically extract where available:

- full title/location;
- description;
- status;
- work schedule;
- operating hours;
- exceptions;
- closure/restriction details.

Use deterministic HTML parsing.

Do not use the LLM for raw webpage extraction.

If parsing fails:

- retain the dataset record;
- mark unavailable details unknown;
- continue analysis.

---

# 50. Road Ahead Enrichment Cache

Detailed event-page enrichment should be cached by event/source identifier.

Exact TTL is not yet locked.

The cache should:

- avoid repeated page fetches during one session;
- retain provenance;
- expose fetched time;
- tolerate parser/source failure.

TTL may be tuned after observing real source behavior.

---

# 51. DriveBC Open511 Regional Ingestion

Open511 is fetched regionally, not separately per selected route.

Initial strategy:

```text
GET active events
within Greater Vancouver bbox
all event types
all severities
all result pages
```

Provisional bbox:

```text
-123.45,48.99,-122.45,49.49
```

The exact bounds should be verified during implementation.

---

# 52. Open511 Pagination

Do not assume one request with `limit=100` contains the full regional result set.

Follow pagination until all matching active events are retrieved.

The regional dataset can then be reused across journey selections.

---

# 53. Open511 Cache

Initial policy:

> approximately 5–15 minutes.

Open511 changes more frequently than Road Ahead.

The backend should reuse one regional cached dataset rather than refetching whenever route selection changes.

If refresh fails:

- retain last valid cache where available;
- mark source stale;
- continue.

---

# 54. Open511 Map vs Briefing

Map:

> show active regional events throughout the supported area.

Briefing:

> include only events deterministically relevant to the selected journey.

This separation is intentional.

---

# 55. Open511 Relevance

Evaluate, where available:

- geometry overlap/proximity;
- affected road;
- travel direction;
- schedule;
- current applicability;
- severity;
- event type;
- source description.

`ACTIVE` does not necessarily mean:

> restriction is happening at this exact moment.

Scheduled future events may also be active records.

Temporal interpretation should remain conservative.

---

# 56. Cross-Source Road Event Deduplication

Road Ahead and Open511 may overlap conceptually.

Do not implement aggressive deduplication in MVP.

Prefer:

```text
two clearly sourced events
```

over:

```text
one incorrectly merged event
```

A conservative deduplication system may be added later.

---

# 57. ECCC SWOB Fetch Strategy

Fetch recent SWOB observations for a Vancouver-area bounding box.

Tested initial bbox:

```text
-123.30,49.15,-122.85,49.35
```

This may be adjusted if implementation testing shows coverage gaps.

Fetch a recent time window sufficient to identify each station's latest observation.

---

# 58. SWOB Station Handling

Do not assume the SWOB station catalogue is exhaustive.

The realtime observation feed may contain station identifiers that are absent from the separate catalogue.

The adapter should therefore:

- group realtime observations by station identifier;
- use embedded coordinates where available;
- enrich with station-catalogue metadata when possible;
- not discard realtime observations solely because catalogue metadata is missing.

---

# 59. SWOB Latest Observation Selection

Workflow:

```text
recent observations
      ↓
group by station
      ↓
validate timestamps
      ↓
select latest valid reading per station
      ↓
normalize useful measurements
```

Then select one or more useful observations based on:

- proximity to destination/route;
- freshness;
- measurement availability.

The nearest station is not automatically the best station.

---

# 60. SWOB Interpretation

Important rules:

- zero accumulated precipitation at a station does not prove surrounding neighborhoods are dry;
- recent precipitation does not prove precipitation is falling now;
- missing measurement data is not zero;
- sparse station coverage should not be spatially interpolated in MVP;
- retain measurement time windows where known.

Wind-field mapping remains an implementation investigation item.

---

# 61. SWOB Cache

Initial cache policy:

> approximately 10–15 minutes.

This is provisional and should be tuned against actual station reporting intervals.

Stale fallback may be used with an explicit age warning.

---

# 62. OpenWeather Role

OpenWeather provides:

- coordinate-based current conditions;
- near-term forecast information.

It complements:

- SWOB measured station evidence;
- Vancouver camera visual evidence.

The exact endpoint/product is not yet locked because live API exploration remains pending.

---

# 63. OpenWeather Validation Before Final Adapter Design

Before finalizing the adapter:

1. test the existing API key;
2. identify available endpoint(s);
3. inspect actual returned schema;
4. confirm current-condition fields;
5. confirm forecast fields;
6. determine useful lookahead granularity;
7. determine request limits;
8. define practical cache TTL;
9. decide whether destination-only sampling is sufficient.

Do not assume desired fields exist until verified.

---

# 64. Weather Evidence Separation

The normalized data layer must distinguish:

## SWOB

Measured physical observations.

## OpenWeather

Structured current/forecast information.

## Camera AI

Visual observations/inference.

These should not be merged into a single ambiguous `weather_state`.

The briefing may synthesize them, but provenance remains separate.

---

# 65. Weather Disagreement Handling

If sources disagree:

- preserve the discrepancy;
- do not force consensus;
- allow the LLM to explain uncertainty using the normalized evidence.

Example:

```text
camera: wet pavement
SWOB: no measured recent rain at nearby station
OpenWeather: rain forecast
```

may indicate localized/changing conditions.

---

# 66. TransLink Static Data

GTFS Static provides the lookup/index layer for Transit-mode selections.

Required files for MVP:

- `routes.txt`;
- `trips.txt`.

`stops.txt` may be parsed or retained for future work but is not required for the locked service-selection flow.

---

# 67. GTFS Static Route Index

Build a searchable route index containing:

- `route_id`;
- `route_short_name`;
- `route_long_name`;
- `route_type`.

Support:

- buses;
- SkyTrain lines.

Do not assume `route_short_name` is always populated.

SkyTrain services may rely on `route_long_name`.

---

# 68. GTFS Direction Index

Use `trips.txt` to derive passenger-friendly direction choices.

Group by route and derive useful combinations of:

- `direction_id`;
- `trip_headsign`.

Do not display hundreds of scheduled trip rows.

Do not treat `direction_id` as a universal compass/inbound meaning.

Passenger-facing labels come from source headsign context.

---

# 69. GTFS Static Cache

GTFS Static changes much less frequently than realtime alerts.

Initial operational policy:

> refresh approximately weekly or when a new official feed is published.

The exact mechanism may remain simple for MVP.

Validated cache replacement applies.

---

# 70. TransLink Realtime Scope

MVP uses:

> **Service Alerts only.**

Deferred:

- Trip Updates;
- Vehicle Positions.

This removes the need for exact trip resolution, delay prediction, and vehicle tracking.

---

# 71. GTFS-Realtime Decoding

The Service Alerts feed is Protocol Buffer encoded.

Backend flow:

```text
HTTP request
      ↓
binary protobuf payload
      ↓
GTFS-Realtime decode
      ↓
normalized TransitAlert objects
```

Use a well-established GTFS-Realtime protobuf library rather than implementing binary decoding manually.

---

# 72. TransLink HTTP Client Behavior

Testing showed that request headers can affect whether TransLink accepts requests.

The backend client should:

- send a stable explicit `User-Agent`;
- use appropriate `Accept` headers;
- handle HTTP 403 explicitly;
- handle rate-limit responses explicitly;
- never log the API key.

Do not assume default `httpx`/`requests` headers will always be accepted.

---

# 73. GTFS-Realtime Cache

Initial Service Alerts cache policy:

> approximately 30–60 seconds.

This is provisional.

The purpose is to:

- avoid redundant calls during repeated route analysis;
- respect API limits;
- keep data sufficiently fresh.

---

# 74. Transit Alert Matching

Matching is deterministic.

For each selected transit leg:

```text
route_id
+
optional direction_id
      ↓
compare against alert selectors
      ↓
classify applicability
```

A single alert may contain multiple selectors.

Treat selectors as alternative affected entities within the same alert.

---

# 75. Transit Selector Rules

Locked principles:

### Route + matching direction

Strong service-level match.

### Route without direction restriction

Potentially relevant to either direction.

### Route + specific stop(s)

Location-specific.

Do not automatically describe this as line-wide.

### Specific trip selector

Applicability cannot be assumed without trip identity.

### Opposite direction only

Exclude if no other selector matches the selected service.

---

# 76. Transit Alert Match Specificity

Preserve specificity in the normalized evidence.

Example:

```text
alert:
Route 9 detour

match:
route_id = 6619
direction_id = 0
scope = route_direction
```

versus:

```text
alert:
Burrard Station elevator unavailable

match:
scope = stop_specific
```

The LLM must receive this distinction.

---

# 77. Transit Alert Temporal Applicability

Preserve:

- structured active periods;
- source text describing timing.

Old start dates do not automatically imply staleness.

Open-ended active periods may represent ongoing advisories.

The system should:

- test broad active-period overlap with expected journey timing;
- avoid claiming a recurring restriction is continuously active unless deterministic evidence supports it;
- preserve source qualifications.

---

# 78. Transit Alert Classification

Do not rely only on GTFS cause/effect enums.

Preserve:

- header text;
- description text;
- cause/effect where available.

Alerts with `UNKNOWN_EFFECT` or `NO_EFFECT` may still contain important passenger information.

The LLM may summarize source text but must not invent:

- delay minutes;
- cancellations;
- geographic scope;
- severity

that the source does not provide.

---

# 79. Transit Map Policy

No transit-map visualization is required.

Do not build:

- bus markers;
- train markers;
- transit network overlays;
- station clusters;
- realtime vehicle tracking;
- transfer-path rendering.

Transit is primarily a briefing/panel information source.

---

# 80. Main Journey Analysis Endpoint

Primary orchestration endpoint:

```text
POST /api/trips/analyze
```

Responsibilities:

1. validate input;
2. construct canonical `Trip`;
3. verify selected route;
4. load Road Ahead data;
5. load regional Open511 data;
6. load SWOB observations;
7. load OpenWeather data;
8. select/fetch Vancouver camera views;
9. analyze camera views;
10. if Transit mode, load/match TransLink Service Alerts;
11. normalize source data;
12. perform deterministic relevance filtering;
13. build journey timeline;
14. prepare structured briefing evidence;
15. call journey-briefing model;
16. return `JourneyAnalysis`.

---

# 81. Synchronous Orchestration

The MVP should use one main synchronous orchestration flow.

Do not introduce:

- job queues;
- worker processes;
- polling architecture;
- WebSocket requirements.

The frontend may show progressive loading stages, but the backend may still treat analysis as one request.

If actual latency becomes unacceptable, staged loading may later be revisited.

---

# 82. Concurrent Fetching

Independent source requests should execute concurrently where practical.

Example:

```text
Road Ahead ──────────┐
Open511 ─────────────┤
SWOB ────────────────┤
OpenWeather ─────────┼── concurrent where safe
Vancouver camera ────┤
TransLink alerts ────┘
```

Not every step is fully independent.

For example:

- camera selection requires destination coordinates;
- transit alert matching requires selected service IDs;
- Road Ahead detail enrichment occurs after route relevance is known.

Concurrency should follow data dependencies.

---

# 83. Manual Refresh

No automatic whole-journey refresh is required.

After analysis completes, state remains static until the user:

- re-runs analysis;
- manually refreshes/re-analyzes.

Individual source cache TTLs still apply when the next analysis occurs.

---

# 84. Source-Specific Cache Policy

Initial consolidated strategy:

| Source | Initial policy | Status |
|---|---:|---|
| Vancouver camera catalogue | ~24h | provisional |
| Vancouver camera images | on demand / ephemeral | locked |
| Road Ahead datasets | ~24h | locked |
| Road Ahead detail pages | cached selectively | TTL pending |
| DriveBC Open511 | ~5–15m | agreed initial |
| ECCC SWOB | ~10–15m | provisional |
| GTFS Static | ~weekly / new feed | provisional |
| GTFS-Realtime Service Alerts | ~30–60s | provisional |
| OpenWeather | TBD after API validation | pending |

Do not force every source into exactly the same cache mechanism.

---

# 85. Generic Validated Cache Flow

For cacheable structured sources:

```text
source requested
      ↓
valid cache?
  ├── no → fetch
  └── yes
        ↓
      fresh?
      ├── yes → use
      └── no  → fetch
                  ↓
               validate
                  ↓
            ┌─────┴─────┐
          valid       invalid
            │             │
        replace       retain old
            │             │
        return new     return stale
```

Stale fallback must be visible in `SourceStatus`.

---

# 86. Source Timeouts

Every external HTTP adapter should use an explicit timeout.

A source should not hang indefinitely.

Use modest source-appropriate values.

Exact values remain configuration-driven.

---

# 87. Retry Strategy

Retries should remain minimal.

Preferred:

- zero or one retry;
- retry only transient failures.

Do not create long backoff behavior inside a user-facing synchronous request.

Fast partial failure is preferable to blocking the whole analysis.

---

# 88. Raw vs Normalized Data

Raw source payloads may be cached.

However:

> normalized models are the application contract.

Business logic must not directly depend on arbitrary cached source JSON.

Flow:

```text
raw source response
      ↓
validate
      ↓
optional raw cache
      ↓
normalize
      ↓
RouteLens model
      ↓
application logic
```

---

# 89. SQLite Responsibilities

SQLite may store:

- generic source cache metadata;
- raw payload cache where appropriate;
- camera catalogue metadata;
- camera image metadata;
- camera-analysis results;
- normalized events where useful;
- normalized weather observations where useful;
- transit static indexes where useful;
- trip-analysis results if useful.

SQLite is not intended to become:

- a historical telemetry warehouse;
- a camera archive;
- a long-term city-data mirror;
- a user-account database.

---

# 90. SQLAlchemy

SQLAlchemy remains locked.

Use it for:

- persistence;
- database access;
- schema clarity.

Avoid unnecessary repository/service abstractions if they do not improve clarity.

---

# 91. API Endpoints

Likely endpoints:

```text
GET  /api/health

GET  /api/places/search
POST /api/routes

GET  /api/transit/routes
GET  /api/transit/routes/{id}/directions

POST /api/trips/analyze

GET  /api/cameras/{intersection_id}
GET  /api/cameras/{intersection_id}/views/{view_id}/image
```

Exact endpoint shape may evolve.

Keep the API surface small.

---

# 92. Place Search Endpoint

Possible:

```text
GET /api/places/search?q=...
```

Responsibilities:

- MapTiler search;
- geographic bias;
- normalized results.

Use the simplest supported secure integration.

---

# 93. Route Endpoint

Possible:

```text
POST /api/routes
```

Input:

```json
{
  "origin": {},
  "destination": {},
  "mode": "drive"
}
```

Response:

```json
{
  "routes": []
}
```

Drive mode may return up to three candidates.

Transit may return a simple contextual corridor if needed.

---

# 94. Transit Selection Endpoints

Possible:

```text
GET /api/transit/routes?q=R5
GET /api/transit/routes/{route_id}/directions
```

The frontend uses these to build ordered `TransitLeg` selections.

These endpoints are backed by preprocessed GTFS Static data.

---

# 95. Camera Endpoints

Possible:

```text
GET /api/cameras/{intersection_id}
GET /api/cameras/{intersection_id}/views/{view_id}/image
```

Camera AI analysis does not necessarily need a public standalone endpoint if it is always performed during `/api/trips/analyze`.

Keep endpoint design minimal.

---

# 96. Journey Briefing Pipeline

After deterministic relevance filtering:

```text
Trip
+
Selected Route
+
Relevant CityEvents
+
CameraObservation
+
SWOB observations
+
OpenWeather current/forecast
+
Selected Transit Legs
+
Matched Transit Alerts
+
Source freshness / limitations
      ↓
compact evidence payload
      ↓
OpenRouter
      ↓
structured briefing
      ↓
Pydantic validation
      ↓
JourneyBriefing
```

Do not send raw API payloads.

---

# 97. Journey Briefing Structured Output

Required shape:

```json
{
  "status": "minor_conditions",
  "summary": "Your journey is mostly clear, with wet roads near the destination.",
  "highlights": [
    "Recent camera views show wet pavement downtown.",
    "One construction restriction overlaps the selected route."
  ],
  "recommendation": "Allow for localized road work and be prepared for possible light rain."
}
```

Target:

- concise;
- evidence-based;
- no invented events;
- no unsupported delays;
- 3–6 important points maximum.

---

# 98. Journey Timeline Generation

Timeline events should be generated primarily deterministically.

Potential categories:

- construction;
- incident;
- weather condition;
- camera destination condition;
- transit service alert;
- destination condition.

Order road/geographic events by approximate route position where meaningful.

Transit alerts may be associated with journey order through selected transit-leg order rather than map location.

---

# 99. Frontend Component Boundaries

Recommended components:

```text
App
├── JourneyInput
│   ├── AddressAutocomplete
│   ├── ModeSelector
│   ├── TransitServiceSelector
│   └── AnalyzeButton
│
├── RouteSelector
│
├── MapPanel
│   ├── RouteLayer
│   ├── CameraLayer
│   ├── RoadAheadLayer
│   └── Open511Layer
│
└── IntelligencePanel
    ├── JourneyOverview
    │   ├── JourneyStatus
    │   ├── DestinationConditions
    │   ├── RouteIssues
    │   ├── TransitAlerts
    │   ├── JourneyTimeline
    │   ├── JourneyBriefing
    │   └── SourceFreshness
    │
    └── CameraDetail
```

These are light boundaries.

Do not over-componentize trivial markup.

---

# 100. Frontend State

Likely top-level state:

```text
origin
destination
mode

routeCandidates
selectedRoute

transitLegs

analysis

selectedCameraIntersection

analysisLoading
sourceErrors
```

No Redux or advanced global-state framework is required.

React state/hooks are sufficient unless implementation proves otherwise.

---

# 101. Route Selection UX

Drive flow:

```text
user inputs trip
      ↓
route candidates fetched
      ↓
MapLibre displays up to 3 routes
      ↓
user selects closest match
      ↓
selected route highlighted
      ↓
Analyze Journey
```

Unselected routes should be muted.

---

# 102. Transit Selection UX

Transit flow:

```text
origin + destination
      ↓
select approximate journey corridor
      ↓
add transit legs
      ↓
search GTFS route
      ↓
choose route/line
      ↓
choose direction if useful
      ↓
repeat for additional legs
      ↓
Analyze Journey
```

The UI stores canonical GTFS identifiers beneath friendly labels.

---

# 103. Journey Analysis UX

After submission:

- selected route remains visible;
- route reveal animation may run;
- loading states appear;
- map telemetry appears;
- destination camera becomes prominent;
- matched transit alerts appear in Transit mode;
- timeline appears;
- briefing appears after evidence is ready.

Animation must not block data display.

---

# 104. Destination Camera UX

The destination-condition panel should display:

- selected intersection name;
- all usable directional views;
- freshness;
- AI observation;
- relevant weather context.

A dedicated CameraDetail panel may be used.

Alternative intersection browsing is optional and not a core MVP workflow.

---

# 105. Map Layers

Likely MapLibre layers:

- selected route;
- alternative route candidates;
- Vancouver camera intersection markers;
- Road Ahead geometry;
- Open511 regional road events;
- optional weather station markers.

Removed from MVP:

- DriveBC camera layer;
- transit route layer;
- transit vehicle layer;
- transit-stop layer.

---

# 106. Open511 Regional Visualization

Open511 map rendering should not depend on journey relevance.

All active regional events may be shown subject to:

- marker clustering;
- category filters;
- severity styling

if required for readability.

The briefing uses a smaller journey-specific subset.

---

# 107. Visual Priority

Map styling should make:

1. selected route;
2. direct route disruptions;
3. Vancouver camera location;
4. regional incidents

immediately understandable.

Avoid visual clutter.

---

# 108. Framer Motion Usage

Use Framer Motion for:

- card entrance;
- panel transitions;
- subtle loading/reveal;
- route-analysis state changes.

Do not use motion for:

- simulated traffic;
- moving transit vehicles;
- decorative continuous animation.

---

# 109. Logging

Use lightweight structured/application logging.

Log:

- source fetch start/result;
- source failures;
- cache hits/misses;
- cache stale fallback;
- source latency;
- pagination counts;
- number of normalized records;
- LLM call latency;
- LLM validation failures;
- total analysis timing.

No external observability platform required.

---

# 110. Error Isolation

Each adapter should convert expected source-specific failures into local source errors.

Example:

```text
TransLink timeout
      ↓
SourceStatus(success=False)
      ↓
orchestrator continues
      ↓
JourneyAnalysis returned
```

Unexpected programming errors should remain visible during development.

Do not broadly swallow exceptions.

---

# 111. Frontend Failure Presentation

Examples:

```text
Transit alerts unavailable

Camera imagery unavailable

SWOB observation temporarily unavailable

Road Ahead data is 31 hours old

OpenWeather temporarily unavailable
```

The UI should emphasize useful successful data rather than converting partial failure into a full-screen error.

---

# 112. Configuration

Environment variables may include:

- API keys;
- source URLs;
- cache TTLs;
- regional bounding boxes;
- relevance radii;
- request timeout settings;
- OpenRouter model identifiers;
- debug flags.

Local development:

```text
.env
```

Repository:

```text
.env.example
```

`.env` must be excluded from Git.

---

# 113. Example Environment Variables

Conceptual:

```text
MAPTILER_API_KEY=
OPENROUTESERVICE_API_KEY=
OPENWEATHER_API_KEY=
TRANSLINK_API_KEY=
OPENROUTER_API_KEY=

OPENROUTER_VISION_MODEL=
OPENROUTER_TEXT_MODEL=

VANCOUVER_CAMERA_CATALOG_TTL_SECONDS=
ROAD_AHEAD_CACHE_TTL_SECONDS=
ROAD_AHEAD_DETAIL_CACHE_TTL_SECONDS=
OPEN511_CACHE_TTL_SECONDS=
SWOB_CACHE_TTL_SECONDS=
TRANSLINK_ALERT_CACHE_TTL_SECONDS=
OPENWEATHER_CACHE_TTL_SECONDS=

OPEN511_BBOX=
SWOB_BBOX=

ROUTE_EVENT_RADIUS_METERS=
DESTINATION_CAMERA_RADIUS_METERS=
```

Exact names may evolve.

---

# 114. Secret Handling

Rules:

- never hardcode API keys;
- never commit `.env`;
- never return secret keys to frontend;
- all OpenRouter calls are backend-only;
- backend logs must avoid printing credentials;
- `.env.example` contains placeholders only.

---

# 115. Testing Strategy

Testing should emphasize deterministic behavior.

Primary tool:

- pytest.

External-source tests should use:

- saved fixtures;
- mocked HTTP responses.

Do not depend on live APIs for routine automated tests.

---

# 116. Vancouver Camera Tests

Test:

- metadata parsing;
- webpage directional-image extraction;
- missing directions;
- broken image URLs;
- nearest-camera selection;
- fallback to next-nearest usable intersection;
- multiple usable views;
- no usable camera case;
- cache overwrite behavior.

---

# 117. Road Ahead Tests

Fixtures should cover both datasets.

Test:

- `LineString`;
- `MultiLineString`;
- `GeometryCollection`;
- missing `street`;
- incomplete project/location fields;
- direct route overlap;
- nearby event;
- distant event;
- preservation of all direct overlaps;
- detail-page parsing;
- failed detail parsing fallback;
- stale-cache fallback.

---

# 118. Open511 Tests

Test:

- valid event;
- optional missing fields;
- pagination;
- active regional fetch;
- all severities retained;
- line/point geometry;
- direction metadata;
- schedule metadata;
- route-near and route-distant events;
- cache reuse;
- stale fallback.

---

# 119. SWOB Tests

Test:

- repeated observations from same station;
- latest-observation selection;
- station absent from catalogue;
- missing precipitation;
- zero precipitation;
- missing wind;
- measurement-time preservation;
- proximity vs measurement availability;
- stale observation handling.

---

# 120. OpenWeather Tests

After endpoint validation, test:

- successful current response;
- forecast response;
- missing optional fields;
- timestamp handling;
- normalized precipitation fields;
- cache behavior;
- failure isolation.

Do not write tests for fields the actual selected endpoint does not expose.

---

# 121. GTFS Static Tests

Test:

- route index creation;
- bus route lookup;
- SkyTrain lookup with missing short name;
- trip grouping;
- headsign extraction;
- multiple headsigns per direction;
- direction labels;
- no assumption that direction ID has universal meaning.

---

# 122. GTFS-Realtime Alert Tests

Test:

- protobuf decoding;
- route-only selector;
- matching route + direction;
- opposite direction;
- route + stop selector;
- trip-specific selector;
- multiple selectors in one alert;
- missing description;
- unknown effect;
- open-ended active period;
- stale/old start date that remains active;
- API 403 handling;
- rate-limit handling.

---

# 123. Geospatial Tests

Test:

- coordinate projection;
- event direct intersection;
- event inside buffer;
- event outside buffer;
- distance in metres;
- camera-intersection ranking;
- destination proximity;
- configured-radius behavior.

These should remain deterministic and lightweight.

---

# 124. Camera Analysis Tests

Do not require live LLM calls in automated tests.

Test:

- valid structured response;
- invalid JSON;
- missing fields;
- out-of-range confidence;
- null/uncertain values;
- multi-image input preparation;
- fallback behavior.

Live multimodal checks remain manual/integration-level.

---

# 125. Journey Briefing Tests

Given mocked OpenRouter output:

- valid briefing accepted;
- malformed output rejected;
- missing highlights handled;
- recommendation nullable if allowed.

Also test evidence construction so that:

- only relevant road events are included;
- transit specificity is preserved;
- source provenance survives;
- stale/unavailable sources are represented;
- raw API payloads are excluded.

---

# 126. Integration Tests

Use controlled mocked sources to test:

```text
POST /api/trips/analyze
```

Expected:

- multiple sources combine correctly;
- one source can fail;
- stale source may fall back;
- result still returns;
- source statuses are accurate;
- nearest usable camera is selected;
- correct route events are included;
- relevant transit alerts match selected legs;
- unmatched alerts are excluded.

---

# 127. Manual Live Integration Checks

Manual checks should validate:

- MapTiler autocomplete;
- openrouteservice routes;
- Vancouver camera dataset;
- Vancouver camera-page enrichment;
- actual camera JPEGs;
- Road Ahead datasets;
- multiple Road Ahead detail pages;
- Open511 regional bbox/pagination;
- ECCC SWOB;
- OpenWeather;
- GTFS Static preprocessing;
- TransLink Service Alerts;
- TransLink request headers;
- OpenRouter camera analysis;
- OpenRouter journey briefing.

DriveBC cameras are not part of the MVP checklist.

---

# 128. Ruff / Type Checking

Ruff should be used for:

- linting;
- import cleanup;
- simple consistency checks.

Additional typing checks may be added if useful, but should not become a major project burden.

Frontend should pass:

```text
npm run build
```

before a phase is considered complete.

---

# 129. Development Boundaries

Avoid:

- unnecessary repository abstractions;
- deep inheritance hierarchies;
- elaborate dependency injection;
- speculative generic adapters;
- premature interfaces;
- generalized “city telemetry platform” architecture.

Favor concrete readable code.

---

# 130. Git Control

The human owns Git history.

Coding agents may:

- inspect repository state;
- inspect diffs;
- modify files;
- run tests/builds;
- report changes.

Coding agents must not:

- commit;
- push;
- force-push;
- rewrite history;
- create tags;
- merge;
- decide that a phase is accepted.

Phase flow:

```text
Codex implements
      ↓
Codex verifies
      ↓
Codex reports
      ↓
Human reviews
      ↓
Human requests fixes OR accepts
      ↓
Human commits
```

---

# 131. Phase Completion Expectations

A meaningful development phase should leave:

- working implementation;
- passing relevant tests;
- successful frontend/backend build where applicable;
- no obvious broken repository state;
- clear report of changed files;
- clear report of verification performed;
- no Git commit made by the coding agent.

---

# 132. Security Scope

RouteLens is not a security-focused project.

Normal application hygiene still applies:

- backend-only secret storage;
- input validation;
- no secrets in logs;
- safe image handling;
- bounded external request timeouts;
- dependency discipline;
- reasonable error handling.

Do not spend MVP time on heavyweight security architecture.

---

# 133. Performance Expectations

Expected workload:

- one interactive user;
- one selected route;
- modest regional telemetry;
- one selected Vancouver camera intersection;
- typically 2–4 directional camera images;
- one multimodal camera AI call;
- one journey-briefing AI call.

Prioritize perceived latency.

Useful optimizations:

- concurrent source fetching;
- shared source caches;
- no route-specific Open511 refetch;
- no repeated camera-analysis calls;
- small LLM evidence payloads.

---

# 134. Analysis Latency

The target is not a fixed SLA.

The UI should communicate progress while:

- caches load;
- source APIs respond;
- camera images download;
- AI calls complete.

A slower optional source should not make the application appear frozen.

---

# 135. AI Cost Control

Cost-control strategies:

- one camera intersection per journey;
- one multimodal request across all usable views;
- no repeated time-series camera polling;
- cache current analysis where useful;
- send compact normalized evidence to text model;
- avoid raw API payloads;
- allow independent vision/text model selection.

---

# 136. Data Retention

Persist only what helps:

- cache;
- debugging;
- normalized current data;
- current analysis;
- demo reliability.

Camera images:

> ephemeral current frames only.

Do not create:

- historical camera archive;
- telemetry warehouse;
- long-term transit feed archive.

---

# 137. DriveBC Cameras — Deferred Architecture

DriveBC camera integration is explicitly outside the MVP.

If added later, it should reuse:

- camera-provider abstraction;
- image validation;
- ephemeral caching;
- multimodal classification.

A future DriveBC adapter should not require a separate AI pipeline.

No DriveBC camera code should be implemented during MVP phases unless scope is explicitly reopened.

---

# 138. Technical Non-Goals

This architecture does not include:

- exact Google Maps route import;
- Google Maps SDK;
- exact transit itinerary reconstruction;
- transit Trip Updates;
- transit Vehicle Positions;
- exact trip selection;
- stop-level journey planning;
- transit vehicle animation;
- transit map overlays;
- DriveBC camera integration;
- multiple camera intersections per journey;
- historical camera storage;
- camera time-series analysis;
- image upscaling;
- camera traffic-speed estimation;
- complex cross-source deduplication;
- weather interpolation;
- PostGIS;
- historical telemetry warehouse;
- realtime push subscriptions;
- WebSockets;
- background worker system;
- mobile architecture;
- authentication;
- accounts;
- personalization;
- city simulation;
- complex ML ranking;
- model training.

---

# 139. Initial Technical Success Criteria

The technical design is realized when:

1. React/Vite loads with a dark MapTiler/MapLibre map.
2. Origin/destination autocomplete works.
3. Vancouver destination validation works.
4. Drive mode returns route candidates.
5. User can select a candidate route.
6. Transit mode can retain an approximate geographic corridor.
7. FastAPI orchestrates all MVP source adapters.
8. Normalized models preserve source provenance.
9. Geographic calculations use meter-appropriate projection.
10. Road Ahead ingests both official datasets.
11. Road Ahead preserves full source geometry.
12. Relevant Road Ahead detail pages can be deterministically enriched.
13. Direct Road Ahead overlaps are preserved before nearby-event limits.
14. Open511 fetches all active regional pages within the configured bbox.
15. Open511 events render regionally.
16. Journey-specific Open511 relevance is filtered deterministically.
17. SWOB recent observations are grouped by station.
18. SWOB selects useful fresh observations without treating missing data as zero.
19. OpenWeather endpoint/schema has been validated against the actual API key.
20. OpenWeather current/near-term data is normalized.
21. Vancouver camera catalogue enrichment extracts real directional image URLs.
22. Nearest usable camera intersection is selected.
23. All available usable directional views are fetched ephemerally.
24. One multimodal inference analyzes those views.
25. Camera output validates through Pydantic.
26. GTFS Static powers bus/SkyTrain selection.
27. Passenger-friendly transit directions derive from GTFS trip/headsign data.
28. GTFS-Realtime Service Alerts decode successfully.
29. Route/direction alert matching works deterministically.
30. Stop-/trip-specific scope is preserved rather than treated as route-wide.
31. Journey timeline is built from normalized relevant evidence.
32. Journey briefing validates through Pydantic.
33. `JourneyAnalysis` reaches the frontend.
34. Partial source failures produce useful results.
35. Stale structured caches can fall back safely.
36. automated tests use fixtures/mocks for external sources.
37. frontend and backend builds/tests succeed locally.

---

# 140. Technical Mental Model

The system should remain understandable as:

```text
INPUT
origin / destination / mode
optional transit services
        ↓
ROUTE CONTEXT
approximate corridor
        ↓
INGESTION
source-specific cached feeds
        ↓
VALIDATION + NORMALIZATION
RouteLens models + provenance
        ↓
DETERMINISTIC RELEVANCE
geometry + timing + identifiers
        ↓
OBSERVATION
road + weather + camera + transit
        ↓
AI INTERPRETATION
multi-view camera assessment
+
journey briefing
        ↓
PRESENTATION
MapLibre map + journey panel
```

If implementation becomes substantially more complicated than this model, reconsider the architecture before adding infrastructure.

---

# 141. Source Responsibility Summary

| Source | Primary technical responsibility |
|---|---|
| Vancouver Webcams | Destination visual evidence |
| Vancouver Road Ahead | Municipal construction / closure geometry + selective detail enrichment |
| DriveBC Open511 | Regional active road-event context |
| ECCC SWOB | Measured weather-station evidence |
| OpenWeather | Coordinate-based current / near-term weather |
| GTFS Static | Transit route/direction selection index |
| GTFS-Realtime Service Alerts | Service-specific transit advisories |

DriveBC cameras are deferred.

---

# 142. Implementation Guidance

This design should be implemented using vertical slices.

Do not build every source, table, and frontend component before testing end-to-end behavior.

Preferred pattern:

```text
one source/capability
  ↓
real input
  ↓
normalization
  ↓
deterministic relevance
  ↓
API output
  ↓
visible frontend result
  ↓
verification
```

Examples:

```text
Road Ahead feed
→ geometry
→ route matching
→ detail enrichment
→ map overlay
→ journey card
```

or:

```text
GTFS Static
→ service selector
→ selected route_id/direction_id
→ Service Alert matching
→ transit briefing card
```

Then expand.

The detailed phase order belongs in:

> `docs/implementation-plan.md`

The coding-agent execution rules belong in:

> `docs/development-workflow.md`

This document remains the architecture-level source of truth.
