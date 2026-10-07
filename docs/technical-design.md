# RouteLens AI — Technical Design

## 1. Purpose

This document defines the technical architecture for the RouteLens AI MVP.

The Product Requirements Document defines **what RouteLens must do and why**.

This technical design defines **how the MVP will implement those requirements**.

The design intentionally prioritizes:

- small architecture
- rapid iteration
- clear component boundaries
- deterministic relevance logic
- graceful degradation
- easy local development
- presentation quality
- compatibility with coding-agent-assisted implementation

The MVP is a local desktop web application.

Public deployment is not required.

---

# 2. High-Level Architecture

RouteLens consists of:

- a React frontend
- a FastAPI backend
- lightweight local persistence
- geospatial route-relevance logic
- source-specific public-data adapters
- temporary camera-image caching
- OpenRouter-backed AI inference

High-level flow:

```text
User
 │
 ▼
React / Vite frontend
 │
 │ origin / destination / mode
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
 ├── DriveBC cameras
 ├── ECCC SWOB
 ├── OpenWeatherMap
 └── TransLink GTFS-Realtime
 │
 ▼
Normalization
 │
 ▼
Geospatial relevance engine
 │
 ▼
Camera selection + temporary image cache
 │
 ▼
OpenRouter multimodal analysis
 │
 ▼
Structured journey evidence
 │
 ▼
OpenRouter journey briefing
 │
 ▼
JourneyAnalysis response
 │
 ▼
Map + journey intelligence UI
```

---

# 3. Architectural Principles

## 3.1 Routing Is Context, Not the Product

RouteLens does not own route optimization.

Routing exists only to define an approximate geographic corridor for telemetry relevance.

The application must not drift toward becoming:

- a navigation application
- a route optimizer
- a turn-by-turn directions system

---

## 3.2 Normalize External Data Early

External schemas must remain isolated inside source adapters.

The rest of the application should operate on RouteLens-owned normalized models.

Avoid spreading upstream API field names and response structures throughout:

- services
- geospatial logic
- database code
- frontend API contracts

---

## 3.3 Deterministic Logic Before AI

AI does not decide:

- what route is relevant
- which event intersects the route
- which camera is geographically nearby
- whether a source is fresh
- which transport mode is active

Those responsibilities belong to deterministic code.

AI receives a small, already-filtered evidence set.

---

## 3.4 Partial Success

Every external integration is independently fallible.

One failed data source must not invalidate the entire analysis unless the failure makes the core journey impossible to evaluate.

The orchestrator should return:

- successful source results
- failed source statuses
- a usable JourneyAnalysis where possible

---

## 3.5 Simplicity Over Infrastructure

The MVP deliberately avoids infrastructure that is not required.

Not planned:

- PostgreSQL
- PostGIS
- Redis
- Celery
- Docker requirements
- message queues
- microservices
- Kubernetes
- background workers
- distributed caching
- cloud observability stacks

---

# 4. Technology Stack

## 4.1 Frontend

Locked frontend stack:

- React
- Vite
- TypeScript
- Tailwind CSS
- MapLibre
- Framer Motion
- Lucide

Responsibilities:

- user input
- autocomplete UI
- route candidate selection
- map rendering
- telemetry visualization
- journey intelligence panel
- camera-detail experience
- animation / transitions
- loading states
- partial-failure presentation

No component library is initially required.

Libraries such as shadcn/ui should only be introduced if a concrete need arises.

---

## 4.2 Backend

Locked backend stack:

- Python
- FastAPI
- Pydantic
- httpx
- SQLAlchemy
- SQLite
- Shapely
- pytest
- Ruff

Responsibilities:

- external API access
- source normalization
- routing/geocoding coordination
- cache management
- route relevance
- camera selection
- image proxy/cache
- AI calls
- journey analysis orchestration
- persistence
- structured API responses

---

## 4.3 Mapping

Locked:

- MapLibre for rendering
- MapTiler for basemap/style
- MapTiler for geocoding/autocomplete

The basemap should use a dark, low-clutter style.

RouteLens overlays must visually dominate the basemap.

---

## 4.4 Routing

Locked routing provider:

- openrouteservice

Primary use:

- generate plausible drive-route geometry
- return up to three candidate routes where available

RouteLens does not expect exact Google Maps parity.

---

## 4.5 AI

Locked inference gateway:

- OpenRouter

Specific models are intentionally not fixed.

Separate models may be selected for:

### Vision

Optimized for:

- camera-image interpretation
- structured JSON output
- low latency
- acceptable cost

### Text

Optimized for:

- concise synthesis
- structured journey briefing
- readable recommendations

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
│   └── cache/
│       └── cameras/
│
├── docs/
│   ├── prd.md
│   ├── technical-design.md
│   ├── implementation-plan.md
│   └── development-workflow.md
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

Locked conceptual models:

- `Location`
- `Trip`
- `RouteCandidate`
- `SelectedRoute`
- `CityEvent`
- `Camera`
- `CameraObservation`
- `WeatherObservation`
- `WeatherForecast`
- `TransitAlert`
- `SourceStatus`
- `JourneyBriefing`
- `JourneyAnalysis`

Source-specific raw payloads remain inside adapters or cache storage.

---

# 8. Location Model

Conceptual structure:

```python
class Location(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str | None = None
    provider_id: str | None = None
```

Responsibilities:

- canonical origin/destination representation
- geocoding result
- map placement
- destination validation

---

# 9. Trip Model

Conceptual structure:

```python
class Trip(BaseModel):
    origin: Location
    destination: Location
    mode: Literal["drive", "transit"]
    selected_route: SelectedRoute
    estimated_duration_seconds: int | None = None
    estimated_arrival_at: datetime | None = None
```

The downstream system should operate on this model regardless of how origin/destination were entered.

---

# 10. RouteCandidate Model

Conceptual:

```python
class RouteCandidate(BaseModel):
    id: str
    geometry: dict
    distance_meters: float | None
    duration_seconds: int | None
    label: str | None
```

The geometry should use a consistent internal representation, preferably GeoJSON-compatible.

Driving mode may expose up to three candidates.

---

# 11. SelectedRoute Model

Conceptual:

```python
class SelectedRoute(BaseModel):
    candidate_id: str
    geometry: dict
    mode: Literal["drive", "transit"]
```

The route geometry is used to produce a Shapely line and buffered relevance corridor.

---

# 12. CityEvent Model

Normalized structure for:

- construction
- closures
- incidents
- maintenance
- related road events

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

    observed_at: datetime | None
    updated_at: datetime | None

    source_url: str | None
```

The application must not depend on source-specific event field names after normalization.

---

# 13. Camera Model

Conceptual:

```python
class Camera(BaseModel):
    id: str
    source: str

    name: str | None

    latitude: float
    longitude: float

    upstream_image_url: str | None
    local_image_url: str | None

    captured_at: datetime | None
    fetched_at: datetime | None
```

The frontend should normally use RouteLens image URLs rather than upstream URLs.

---

# 14. CameraObservation Model

Multimodal analysis output.

Conceptual:

```python
class CameraObservation(BaseModel):
    camera_id: str
    analyzed_at: datetime

    precipitation_visible: bool | None
    precipitation_type: str | None

    road_surface: str | None
    traffic_level: str | None
    visibility: str | None

    confidence: float | None
    notes: str | None
```

Values should be conservative.

Unknown or unclear values should remain `None` or explicit uncertainty rather than being invented.

---

# 15. WeatherObservation Model

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
    precipitation_mm: float | None
    humidity_pct: float | None
    wind_speed_kph: float | None
    wind_direction_deg: float | None
```

Only fields required by the product should be normalized.

Do not model the entire SWOB schema unless necessary.

---

# 16. WeatherForecast Model

Used primarily for OpenWeatherMap near-term forecast information.

Conceptual:

```python
class WeatherForecast(BaseModel):
    source: str
    location: Location

    forecast_at: datetime

    temperature_c: float | None
    precipitation_probability_pct: float | None
    precipitation_type: str | None
    wind_speed_kph: float | None

    summary: str | None
```

Forecast data must remain explicitly separate from current observations.

---

# 17. TransitAlert Model

Conceptual:

```python
class TransitAlert(BaseModel):
    id: str
    source: str

    title: str
    description: str | None

    route_ids: list[str]
    stop_ids: list[str]

    severity: str | None

    active_from: datetime | None
    active_until: datetime | None

    updated_at: datetime | None
```

Additional trip-delay structures may be added where needed.

The MVP does not require modeling every GTFS-Realtime field.

---

# 18. SourceStatus Model

Each external source should report its own state.

Conceptual:

```python
class SourceStatus(BaseModel):
    source: str

    success: bool
    fetched_at: datetime | None

    cache_hit: bool = False
    stale: bool = False

    error: str | None = None
```

This supports:

- partial success
- troubleshooting
- UI status
- logging

---

# 19. JourneyBriefing Model

Locked structure:

```python
class JourneyBriefing(BaseModel):
    status: str
    summary: str
    highlights: list[str]
    recommendation: str | None
```

Possible `status` examples:

- `clear`
- `minor_conditions`
- `attention`
- `disrupted`

Exact enum values may be refined during implementation.

The frontend should not depend on a raw prose blob.

---

# 20. JourneyAnalysis Model

Primary API result.

Conceptual:

```python
class JourneyAnalysis(BaseModel):
    trip: Trip

    destination_cameras: list[Camera]
    primary_camera_observation: CameraObservation | None

    construction_events: list[CityEvent]
    road_events: list[CityEvent]

    weather_observation: WeatherObservation | None
    weather_forecast: WeatherForecast | None

    transit_alerts: list[TransitAlert]

    timeline_events: list[dict]

    briefing: JourneyBriefing | None

    source_statuses: list[SourceStatus]
```

Additional fields may be introduced where justified.

---

# 21. Source Adapter Architecture

Every external source should be isolated behind its own adapter.

Recommended directory:

```text
backend/app/sources/
├── vancouver_cameras.py
├── road_ahead.py
├── drivebc_open511.py
├── drivebc_cameras.py
├── eccc_swob.py
├── translink.py
├── openweathermap.py
├── maptiler.py
└── openrouteservice.py
```

Each adapter should follow the same conceptual pattern:

```text
fetch
  ↓
validate upstream response
  ↓
normalize
  ↓
return normalized models
  ↓
report source status
```

---

# 22. Source Adapter Contract

Every adapter should:

1. own its upstream URL/API details;
2. own authentication requirements;
3. use configured timeout settings;
4. use cache where appropriate;
5. validate/parsing upstream data;
6. normalize into RouteLens models;
7. expose freshness;
8. report failure without crashing the orchestrator;
9. avoid leaking raw source schema into unrelated modules.

Conceptually:

```python
class SourceAdapter(Protocol):
    async def fetch(...) -> ...
    def normalize(...) -> ...
```

A formal inheritance hierarchy is optional.

Avoid unnecessary abstraction if simple modules/functions are clearer.

---

# 23. MapTiler Integration

MapTiler provides:

- autocomplete
- geocoding
- basemap/style

Frontend interaction:

```text
typed query
   ↓
frontend calls backend or permitted client integration
   ↓
MapTiler suggestions
   ↓
user selects result
   ↓
canonical Location
```

Preferred architecture:

- API key handling should follow MapTiler's supported browser/backend model;
- sensitive server-side credentials must not be exposed unnecessarily;
- destination result must be validated as inside Vancouver.

The exact client/server split can be finalized based on MapTiler key restrictions.

---

# 24. Vancouver Destination Validation

The backend should enforce destination support.

Do not rely solely on frontend checks.

Possible implementations:

- bounding polygon
- bounding box plus administrative data
- geocoder metadata

Preferred:

> use a simple City of Vancouver polygon/boundary check if easily available.

If implementation cost is disproportionate, a practical geographic approximation is acceptable for the MVP.

The check should be deterministic.

---

# 25. Driving Route Generation

For drive mode:

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
- allow a single route if no alternatives exist;
- store route geometry in normalized RouteCandidate models;
- route styling should clearly differentiate selected/unselected candidates.

---

# 26. Transit Corridor Generation

Transit mode does not reconstruct real transit routing.

Instead:

```text
origin
 + destination
      ↓
generic journey corridor
      ↓
broader relevance region
      ↓
TransLink + city telemetry
```

Initial implementation may use:

- direct origin-destination line
- broadened corridor
- one approximate road/path geometry if experimentally useful

The exact strategy should remain simple.

Transit route precision is considered experimental.

The product should not imply that the corridor represents the actual bus/SkyTrain itinerary.

---

# 27. Geospatial Engine

Locked library:

- Shapely

Responsibilities:

- convert route geometry to Shapely objects
- create route buffer
- calculate distance to destination
- calculate distance to route
- test intersections
- rank nearby events/cameras

No geospatial database is required.

---

# 28. Route Buffer

Concept:

```text
route geometry
      ↓
Shapely LineString
      ↓
buffer(radius)
      ↓
route relevance polygon
```

Different source types may use different configured radii.

Example initial values:

```text
construction          250 m
road incidents        500 m
route cameras         500 m
destination cameras   1–2 km
```

These are starting values, not hard product requirements.

They must be configurable.

---

# 29. Relevance Scoring

MVP scoring should remain deterministic and simple.

Potential factors:

- distance
- route intersection
- distance to destination
- freshness
- severity
- travel mode
- source type

Conceptual:

```text
score =
  distance_weight
+ freshness_weight
+ severity_weight
+ source_priority
```

Exact weights should be adjusted empirically.

No machine-learning ranking is needed.

---

# 30. Transit Relevance

Transit mode should use a broader relevance strategy.

Potential logic:

- wider corridor buffer
- destination proximity
- relevant route identifiers if discoverable
- broad TransLink alerts affecting nearby corridors/services

The application should err toward surfacing a potentially relevant transit disruption rather than requiring exact itinerary reconstruction.

However, noise must still be controlled.

This behavior should be tuned through real-world testing.

---

# 31. Destination Camera Ranking

Initial ranking should use:

1. distance to destination
2. image freshness
3. source preference where useful

Conceptual:

```text
candidate cameras
      ↓
remove stale/unusable
      ↓
rank by distance
      ↓
adjust for freshness
      ↓
optional source preference
      ↓
primary + alternatives
```

Select:

- one primary
- a small number of alternatives

Avoid overengineering orientation or visual field-of-view calculations in the MVP.

---

# 32. Camera Image Proxy

The backend should proxy camera imagery.

Frontend flow:

```text
React
  ↓
GET /api/cameras/{camera_id}/image
  ↓
FastAPI
  ↓
local cache or upstream image
```

Benefits:

- avoids CORS issues
- centralizes caching
- ensures AI and frontend use the same frame
- isolates upstream URL changes
- allows consistent error handling
- avoids exposing unnecessary upstream details

---

# 33. Camera Image Cache

Latest-image-only cache.

Directory:

```text
data/cache/cameras/
```

Example:

```text
data/cache/cameras/{camera_id}.jpg
```

Behavior:

```text
image requested
      ↓
cache fresh?
 ┌────┴────┐
 yes       no
 │          │
return      fetch upstream
            ↓
       overwrite existing
            ↓
          return
```

No historical image archive.

---

# 34. Camera Cache Metadata

SQLite may store:

- camera ID
- fetched timestamp
- captured timestamp if available
- file path
- upstream metadata
- latest AI-analysis timestamp

Raw image binary data does not need to be stored in SQLite.

---

# 35. Camera Analysis Cache

AI analysis should be reused where sufficiently fresh.

Example:

```text
camera image fetched at 14:05
analysis performed at 14:05

user selects camera at 14:07
→ reuse analysis

camera refreshed at 14:12
→ new image
→ new analysis required
```

The analysis should be associated with:

- camera ID
- image fetch/capture timestamp
- model identifier where useful

---

# 36. Multimodal Analysis Pipeline

Flow:

```text
Camera
  ↓
fetch latest image
  ↓
temporary cache
  ↓
prepare constrained vision prompt
  ↓
OpenRouter
  ↓
structured JSON
  ↓
Pydantic validation
  ↓
CameraObservation
  ↓
persist normalized result
```

The model should be explicitly instructed to:

- describe observable evidence only
- avoid unsupported certainty
- return null/unknown where unclear
- avoid identifying individuals
- avoid irrelevant image description

---

# 37. Camera Structured Output

Target contract:

```json
{
  "precipitation_visible": true,
  "precipitation_type": "rain",
  "road_surface": "wet",
  "traffic_level": "moderate",
  "visibility": "good",
  "confidence": 0.84,
  "notes": "Light precipitation appears visible around passing vehicles."
}
```

The backend must validate output before storing or returning it.

Invalid AI output should:

- be logged
- fail gracefully
- not break the journey analysis

---

# 38. Weather Observation Selection

ECCC SWOB may expose multiple stations.

Initial selection:

```text
available observations
      ↓
fresh enough?
      ↓
nearest useful station to destination
```

Possible secondary logic:

- route-adjacent station
- origin station

Destination conditions have priority.

---

# 39. Weather Forecast

OpenWeatherMap should provide near-term forecast information.

Primary interest:

- current/near-term temperature
- precipitation probability/type
- wind where useful
- changes over approximately 30 minutes–2 hours

Do not build long-range forecasting features.

---

# 40. Observed vs Forecast Separation

The backend API and models must keep these distinct.

Never merge into one ambiguous object.

Frontend labels should reflect:

```text
Observed
Forecast
```

This is both a data and UX requirement.

---

# 41. TransLink Integration

Primary GTFS-Realtime interests:

1. service alerts
2. trip updates / delays
3. related relevant disruption data

Not required:

- vehicle animation
- complete timetable reconstruction
- full transit routing engine

The adapter should normalize only the fields needed by the MVP.

---

# 42. Main Journey Analysis Endpoint

Primary orchestration endpoint:

```text
POST /api/trips/analyze
```

Responsibilities:

1. validate input
2. construct canonical Trip
3. fetch relevant source data
4. normalize all results
5. perform geospatial filtering
6. rank destination cameras
7. fetch/analyze primary camera
8. select weather observation
9. retrieve near-term forecast
10. process transit data when needed
11. build journey timeline
12. build structured briefing input
13. call journey-briefing model
14. return JourneyAnalysis

---

# 43. Synchronous Orchestration

The MVP should use one main synchronous orchestration flow.

Do not introduce:

- job queues
- worker processes
- polling architecture
- WebSocket requirements

The frontend may visually show progressive loading stages, but the backend can still treat analysis as one request.

If real API latency later makes this unacceptable, staged loading may be revisited.

---

# 44. Concurrency

Although orchestration is one request, independent source fetches should be performed concurrently where practical.

For example:

```text
Road Ahead ──────────┐
Open511 ─────────────┤
SWOB ────────────────┤
OpenWeatherMap ──────┼── concurrently
Vancouver cameras ───┤
DriveBC cameras ─────┤
TransLink ───────────┘
```

Use Python async/httpx where appropriate.

This improves latency without adding architectural complexity.

---

# 45. Manual Refresh

No automatic telemetry refresh is required.

After an analysis completes, the state remains static until the user chooses to:

- re-run analysis
- manually refresh/re-analyze

This keeps behavior predictable and implementation simple.

---

# 46. Source Timeouts

Every external HTTP adapter should use an explicit timeout.

A source should not be allowed to hang indefinitely.

Use modest per-source timeout values.

Exact values should be configuration-driven.

Example:

```text
5–10 seconds
```

depending on source behavior.

---

# 47. Retry Strategy

Retries should remain minimal.

Preferred:

- zero or one retry
- retry only for reasonable transient failures

Do not create long exponential backoff behavior in a user-facing synchronous request.

Fast partial failure is preferable to blocking the entire analysis.

---

# 48. Caching Architecture

SQLite may store a generic raw source cache.

Conceptual table:

```text
source_cache
------------
source
cache_key
payload_json
fetched_at
expires_at
```

Use cases:

- reduce repeat API requests
- improve demo reliability
- debug source normalization
- tolerate temporary service failures where stale data remains acceptable

---

# 49. Raw vs Normalized Data

Raw source payloads may be cached.

However:

> normalized models are the application contract.

Business logic must not directly query arbitrary cached source JSON.

Flow:

```text
raw API response
      ↓
optional raw cache
      ↓
adapter normalization
      ↓
RouteLens model
      ↓
application logic
```

---

# 50. SQLite Responsibilities

SQLite stores:

- raw cache entries
- camera metadata
- camera-analysis metadata/results
- normalized events where useful
- normalized weather observations where useful
- trip-analysis results if useful

SQLite is not intended to become:

- a historical data warehouse
- long-term telemetry archive
- user-account database

---

# 51. SQLAlchemy

SQLAlchemy is locked.

Use it for:

- model persistence
- database access
- schema clarity
- practice with standard application patterns

Avoid unnecessary repository/service abstractions if they do not improve clarity.

---

# 52. API Endpoints

Likely endpoints:

```text
GET  /api/health

GET  /api/places/search
POST /api/routes

POST /api/trips/analyze

GET  /api/cameras/{id}
GET  /api/cameras/{id}/image
POST /api/cameras/{id}/analyze
```

Exact endpoint shape may evolve.

Keep the API surface small.

---

# 53. Place Search Endpoint

Possible:

```text
GET /api/places/search?q=...
```

Responsibilities:

- proxy MapTiler geocoding if desired
- apply geographic bias
- normalize results

Frontend may alternatively use an approved MapTiler client flow.

Choose the simplest secure supported integration.

---

# 54. Route Endpoint

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
  "routes": [...]
}
```

Transit mode may return one generic corridor rather than real transit alternatives.

---

# 55. Camera Endpoints

Possible:

```text
GET /api/cameras/{id}
GET /api/cameras/{id}/image
POST /api/cameras/{id}/analyze
```

`analyze` behavior:

- reuse fresh result if available
- otherwise fetch current image
- perform OpenRouter analysis
- persist normalized CameraObservation
- return result

---

# 56. Journey Briefing Pipeline

After relevance filtering:

```text
Trip
+
Destination CameraObservation
+
WeatherObservation
+
WeatherForecast
+
important CityEvents
+
TransitAlerts
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

---

# 57. Journey Briefing Structured Output

Required shape:

```json
{
  "status": "minor_conditions",
  "summary": "Your journey is mostly clear, with light rain near the destination.",
  "highlights": [
    "Recent camera imagery shows wet roads downtown.",
    "One construction zone is near the selected corridor."
  ],
  "recommendation": "Bring an umbrella; no major route disruption is apparent."
}
```

Target:

- concise
- evidence-based
- no invented events
- 3–6 important points maximum

---

# 58. Journey Timeline Generation

Timeline events should be generated primarily deterministically.

Potential timeline event categories:

- origin condition
- construction
- incident
- relevant camera
- transit disruption
- destination condition

Order by:

- approximate position along route
- destination priority
- event importance

The LLM should not be required to build route ordering from scratch.

---

# 59. Frontend Component Boundaries

Recommended components:

```text
App
├── JourneyInput
│   ├── AddressAutocomplete
│   ├── ModeSelector
│   └── AnalyzeButton
│
├── RouteSelector
│
├── MapPanel
│   ├── RouteLayer
│   ├── CameraLayer
│   ├── ConstructionLayer
│   └── IncidentLayer
│
└── IntelligencePanel
    ├── JourneyOverview
    │   ├── JourneyStatus
    │   ├── DestinationConditions
    │   ├── RouteIssues
    │   ├── JourneyTimeline
    │   ├── JourneyBriefing
    │   └── SourceFreshness
    │
    └── CameraDetail
```

These are light boundaries.

Do not over-componentize trivial markup.

---

# 60. Frontend State

Keep state simple.

Likely top-level state:

```text
origin
destination
mode
routeCandidates
selectedRoute
analysis
selectedCamera
analysisLoading
sourceErrors
```

No Redux or advanced global-state framework is required.

React state/hooks are sufficient unless implementation proves otherwise.

---

# 61. Route Selection UX

Driving flow:

```text
user inputs trip
      ↓
route candidates fetched
      ↓
MapLibre displays up to 3 routes
      ↓
user clicks closest match
      ↓
selected route highlighted
      ↓
Analyze Journey
```

Unselected routes should be muted.

Selected route should use strong contrast.

---

# 62. Journey Analysis UX

After submission:

- selected route remains visible
- route reveal animation may run
- loading stages become visible
- map telemetry appears
- right-panel cards animate in
- primary camera becomes prominent
- briefing appears after evidence is ready

Frontend animation must not block data display.

---

# 63. Camera Detail UX

When a camera is selected:

```text
JourneyOverview
      ↓
Framer Motion transition
      ↓
CameraDetail
```

CameraDetail:

- large image
- name/location
- freshness
- camera AI result
- weather context
- Back control

Alternative-camera analysis may show its own loading state.

---

# 64. Map Layers

Likely MapLibre layers:

- selected route
- alternative candidate routes
- Vancouver cameras
- DriveBC cameras
- Road Ahead construction
- Open511 incidents
- optional weather location markers

Route-relevant items should appear at higher prominence.

Off-route nearby data should remain visible but subdued.

---

# 65. Visual Priority

Map styling should make:

1. route
2. cameras
3. meaningful disruptions

immediately visible.

Avoid generic default map markers if custom Lucide/icon-based styling is practical.

---

# 66. Framer Motion Usage

Use Framer Motion for:

- card entrance
- journey/camera panel transition
- subtle loading/reveal
- route-analysis state changes

Do not use motion for:

- simulated traffic
- moving transit vehicles
- decorative continuous animations

---

# 67. Logging

Use lightweight application logging from the beginning.

Log:

- source fetch start/result
- source failures
- cache hits/misses
- source latency
- OpenRouter call latency
- OpenRouter errors
- analysis start/end
- overall analysis latency

No external observability platform required.

Standard Python logging is sufficient.

Structured/log-friendly messages are preferred.

---

# 68. Error Isolation

Each adapter should catch/convert expected source-specific failures.

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

Unexpected programming errors should still surface clearly during development.

Do not broadly swallow every exception.

---

# 69. Frontend Failure Presentation

Source-level errors should appear unobtrusively.

Examples:

```text
Transit data unavailable
Camera analysis unavailable
Weather observation temporarily unavailable
```

The UI should emphasize successful useful data rather than turning partial source failure into a full-screen error.

---

# 70. Configuration

Environment variables should contain:

- API keys
- source base URLs where useful
- cache TTLs
- route relevance radii
- request timeout settings
- OpenRouter model identifiers
- debug flags

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

# 71. Example Environment Variables

Conceptual:

```text
MAPTILER_API_KEY=
OPENROUTESERVICE_API_KEY=
OPENWEATHERMAP_API_KEY=
TRANSLINK_API_KEY=
OPENROUTER_API_KEY=

OPENROUTER_VISION_MODEL=
OPENROUTER_TEXT_MODEL=

CAMERA_CACHE_TTL_SECONDS=
OPEN511_CACHE_TTL_SECONDS=
SWOB_CACHE_TTL_SECONDS=

ROUTE_EVENT_RADIUS_METERS=
ROUTE_CAMERA_RADIUS_METERS=
DESTINATION_CAMERA_RADIUS_METERS=
```

Exact names may evolve.

---

# 72. Secret Handling

Rules:

- never hardcode API keys
- never commit `.env`
- never return secret keys to frontend
- all OpenRouter calls are backend-only
- backend logs must avoid printing credentials
- `.env.example` contains names only, not secret values

---

# 73. Testing Strategy

Testing should emphasize deterministic behavior.

Primary tool:

- pytest

External API tests should use:

- saved fixtures
- mocked HTTP responses

Do not depend on live upstream APIs for normal automated tests.

---

# 74. Adapter Tests

Each adapter should have representative fixture tests covering:

- valid response
- missing optional fields
- malformed entries
- empty results
- timestamp parsing
- normalization correctness

Examples:

```text
tests/fixtures/road_ahead/
tests/fixtures/open511/
tests/fixtures/swob/
tests/fixtures/translink/
```

---

# 75. Geospatial Tests

Test:

- event inside route buffer
- event outside route buffer
- camera ranking by distance
- route intersection
- destination proximity
- configured-radius behavior

These should be deterministic and lightweight.

---

# 76. Camera Analysis Tests

Do not require live LLM calls during automated tests.

Test:

- valid structured response parsing
- invalid JSON
- missing fields
- out-of-range confidence
- null/uncertain values
- fallback behavior

Live multimodal testing should remain manual/integration-level.

---

# 77. Journey Briefing Tests

Test structured response validation.

Given mocked OpenRouter results:

- valid briefing accepted
- malformed response rejected
- missing highlights handled
- recommendation may be nullable if allowed

Also test evidence preparation deterministically where possible.

---

# 78. Integration Tests

Use controlled mocked external sources to test:

```text
POST /api/trips/analyze
```

Expected:

- multiple source results combined
- one source can fail
- result still returns
- correct SourceStatus values
- primary camera selected
- correct route events included/excluded

---

# 79. Manual Live Integration Checks

A small manual checklist should validate:

- MapTiler autocomplete
- openrouteservice routes
- Vancouver camera access
- Road Ahead live data
- Open511 live data
- DriveBC cameras
- ECCC SWOB
- OpenWeatherMap
- TransLink
- OpenRouter camera analysis
- OpenRouter briefing

These are manual external-service sanity checks, not automated tests.

---

# 80. Ruff / Type Checking

Ruff should be used for:

- linting
- import cleanup
- simple consistency checks

Additional typing checks may be added if useful, but should not become a major project burden.

Frontend should pass:

```text
npm run build
```

before a phase is considered complete.

---

# 81. Development Boundaries

The architecture should remain intentionally simple.

Avoid introducing:

- unnecessary generic repositories
- deep inheritance hierarchies
- elaborate dependency injection frameworks
- premature interfaces
- speculative abstractions

Codex should favor concrete readable code over architecture for hypothetical future scale.

---

# 82. Git Control

The human owns Git history.

Coding agents may:

- inspect repository state
- inspect diffs
- modify files
- run tests/builds
- report changes

Coding agents must not:

- create commits
- push
- force-push
- rewrite history
- create tags
- merge branches
- decide that a phase is accepted

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

This rule should also be documented in the development workflow.

---

# 83. Phase Completion Expectations

A meaningful development phase should leave:

- working implementation
- passing relevant tests
- successful frontend/backend build where applicable
- no obvious broken repository state
- clear report of changed files
- clear report of verification performed
- no Git commit made by the coding agent

---

# 84. Security Scope

RouteLens is not a security-focused project.

However, normal application hygiene still applies:

- backend-only secret storage
- input validation
- no secrets in logs
- safe image handling
- bounded external request timeouts
- dependency discipline
- reasonable error handling

Do not spend MVP development time on heavyweight security architecture.

---

# 85. Performance Expectations

The application does not need production-scale optimization.

Expected workload:

- one interactive user
- small route
- limited telemetry
- small numbers of camera images
- one primary camera AI call
- one journey briefing AI call

Prioritize perceived latency.

Useful optimizations:

- concurrent source fetching
- caching
- avoid redundant AI analysis
- small evidence payloads

---

# 86. Analysis Latency

The target is not a fixed SLA.

The product should feel acceptable for a near-departure lookup.

The UI should communicate progress while:

- source APIs respond
- image downloads occur
- AI calls complete

A slower AI call should not make the application appear frozen.

---

# 87. AI Cost Control

Cost control strategies:

- analyze primary camera automatically
- analyze alternative cameras only on demand
- reuse fresh camera analysis
- send small structured evidence to text model
- avoid sending irrelevant raw API payloads to LLMs
- allow independent model selection for vision/text

---

# 88. Data Retention

The MVP is not intended to accumulate long-term personal or city history.

Persist only what helps:

- cache
- debugging
- current analysis
- demo reliability

Camera images:

> latest frame only

No historical image archive.

Trip-analysis persistence may be limited or periodically cleared.

---

# 89. Technical Non-Goals

This architecture does not include:

- exact Google Maps route import
- Google Maps SDK
- exact transit itinerary reconstruction
- PostGIS
- historical telemetry warehouse
- persistent camera archive
- realtime push subscriptions
- WebSockets
- background worker system
- mobile architecture
- authentication
- accounts
- user personalization
- city simulation
- traffic simulation
- vehicle animation
- complex ML ranking
- model training

---

# 90. Initial Technical Success Criteria

The technical design is realized when:

1. React/Vite app loads with dark MapTiler/MapLibre map.
2. Origin/destination autocomplete returns valid locations.
3. Vancouver destination validation works.
4. Drive mode returns candidate routes.
5. User can select a candidate route.
6. Transit mode produces an approximate corridor.
7. FastAPI can orchestrate all core data adapters.
8. External responses are normalized into common models.
9. Shapely filters telemetry around the selected corridor.
10. Vancouver cameras render on the map.
11. Relevant DriveBC cameras render where applicable.
12. Construction and incidents render correctly.
13. ECCC observations are selected near destination.
14. OpenWeatherMap provides near-term forecast.
15. TransLink data is included for transit mode.
16. Primary destination camera is proxied/cached.
17. Primary camera can be analyzed through OpenRouter.
18. Camera output validates through Pydantic.
19. Journey briefing validates through Pydantic.
20. JourneyAnalysis reaches the frontend.
21. Right-panel JourneyOverview renders correctly.
22. CameraDetail works with Back transition.
23. Source failures produce partial results.
24. automated tests use fixtures/mocks for external services.
25. frontend and backend builds/tests succeed locally.

---

# 91. Technical Mental Model

The system should remain understandable as:

```text
INPUT
origin / destination / mode
        ↓
ROUTE CONTEXT
approximate corridor
        ↓
INGESTION
public telemetry adapters
        ↓
NORMALIZATION
RouteLens models
        ↓
RELEVANCE
Shapely + deterministic ranking
        ↓
OBSERVATION
camera + weather + incidents + transit
        ↓
AI INTERPRETATION
camera analysis + journey briefing
        ↓
PRESENTATION
MapLibre map + journey intelligence panel
```

If implementation begins becoming substantially more complicated than this model, the architecture should be re-evaluated before adding more infrastructure.

---

# 92. Implementation Guidance

This design should be implemented using vertical slices.

Do not build every adapter, every table, and every UI component before testing an end-to-end workflow.

Preferred pattern:

```text
one source
  ↓
one normalized model
  ↓
one relevance rule
  ↓
one API output
  ↓
one visible frontend result
```

Then expand.

The detailed phase order belongs in:

> `docs/implementation-plan.md`

The coding-agent execution rules belong in:

> `docs/development-workflow.md`

This document remains the architecture-level source of truth.
