# RouteLens AI

**A source-grounded briefing for the drive into Vancouver.**

RouteLens AI brings public road, weather, and camera evidence together around a journey you have already planned. It helps answer **“What should I know before I leave?”** with a map, current destination context, and a concise AI Journey Briefing. It complements navigation apps; it does not provide turn-by-turn directions or choose the best route.

> This is a locally run, desktop-oriented web application for driving journeys with a destination inside the City of Vancouver.

## Demo

> **Demo video:** (https://youtu.be/ExTeYvr00d0)

<!-- TODO: Replace the demo video placeholder after adding the approved video. -->

## What the MVP does

1. Choose an origin and a destination in Vancouver using place search.
2. Select **Find Routes** to generate approximate driving routes. RouteLens selects the first usable route returned, and you can choose an alternative.
3. Select **Analyze Journey** to gather evidence for the currently selected route and destination.
4. Review the map and supporting panels, then read the source-grounded AI Journey Briefing.

The briefing has three fixed topics:

- **Camera and weather:** describes visible conditions at the selected destination-area camera and compares them with current or forecast weather only when the evidence is sufficiently close in place and time.
- **Destination weather:** summarizes available current and near-term weather, with nearby ECCC station measurements kept distinct from OpenWeather conditions and forecasts.
- **Closest relevant construction:** describes one selected Vancouver Road Ahead construction finding, prioritizing direct route overlap before proximity and distinguishing nearby events from route overlap.

Each topic can report that evidence is unavailable or insufficient. AI text is an interpretation of the evidence selected by the application, not an authoritative observation. The map and supporting panels also show route context such as municipal road events and regional DriveBC Open511 events; those are separate from the three briefing topics.

## Architecture and data flow

```mermaid
flowchart LR
  U[User selects locations and finds routes] --> FE[React and TypeScript app]
  FE -->|Analyze Journey| API[FastAPI analysis API]
  API --> GEO[MapTiler geocoding and openrouteservice routes]
  API --> SOURCES[Road Ahead, DriveBC Open511, OpenWeather, ECCC SWOB, Vancouver cameras]
  SOURCES --> N[Normalize, track freshness, and match evidence to journey]
  N --> CV[OpenRouter camera interpretation]
  N --> BR[OpenRouter three-topic briefing]
  CV --> API
  BR --> API
  API --> FE
  FE --> MAP[MapLibre map and evidence panels]
```

The React/Vite frontend sends application requests to the local FastAPI backend. The backend calls external providers, normalizes source responses, tracks source status and timestamps, filters journey evidence, and makes AI requests. Provider credentials stay in the backend environment; only the MapTiler key needed by the browser map is exposed through Vite. Camera images are handled as current frames with a short-lived cache, not as a historical image archive.

## Technology and data sources

| Area | Implemented technology or source | Role |
| --- | --- | --- |
| Web app | React, TypeScript, Vite, Tailwind CSS | Journey inputs, analysis state, and evidence panels |
| Map | MapLibre GL JS with MapTiler | Vancouver basemap, geocoding, and place search |
| API | Python, FastAPI, Pydantic, httpx, Shapely | Provider access, validation, normalization, and geographic relevance |
| Driving routes | openrouteservice | Approximate route candidates with automatic first-route selection and manual alternatives |
| Municipal road data | City of Vancouver Road Ahead | Construction and road closures |
| Regional road data | DriveBC Open511 | Regional road events and route-relevant findings |
| Weather | OpenWeather and ECCC GeoMet/SWOB | Current/near-term weather and measured station observations |
| Camera data | City of Vancouver traffic-camera catalogue and linked views | Destination-area imagery and camera evidence |
| AI | OpenRouter with Google Gemma 4 31B Instruct | Structured camera interpretation and the three-topic briefing |

## Local setup

You will need Python 3.10 or newer, Node.js with npm, and provider credentials for the integrations you want to use. The application runs as separate local backend and frontend development servers.

1. Create a root `.env` file from the template and add your own credentials. Do not commit `.env`.

   ```bash
   cp .env.example .env
   ```

   The implemented provider variables are:

   | Variable | Used for |
   | --- | --- |
   | `MAPTILER_API_KEY` | Place search and map style/resources |
   | `OPENROUTESERVICE_API_KEY` | Driving-route candidates |
   | `OPENWEATHER_API_KEY` | Current and near-term weather |
   | `OPENROUTER_API_KEY` | Camera interpretation and AI briefing |

   | Daily quota setting | Default | Scope |
   | --- | --- | --- |
   | `MAPTILER_GEOCODING_DAILY_LIMIT` | 200 | Backend location searches across all visitors |
   | `OPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT` | 100 | Backend driving-route searches across all visitors |

   The backend reads these limits at startup from the process environment or root `.env`, with process values taking precedence. Omit a setting to use its default. Each limit must be a positive whole number within SQLite's signed 64-bit integer range. Zero and malformed values prevent startup. The limits are independent, reset at midnight UTC, and survive backend restarts when the usage database is retained. Existing OpenWeather and OpenRouter budget controls remain in effect.

   The backend also accepts optional settings `OPENWEATHER_DAILY_REQUEST_LIMIT`, `SWOB_BBOX`, `SWOB_CACHE_TTL_SECONDS`, and `CAMERA_IMAGE_CACHE_TTL_SECONDS`. ECCC SWOB and DriveBC Open511 do not require credentials in the current implementation. Transit is deferred and its template key is not used by the MVP. The AI model is configured in the backend; the model identifier is not an environment setting.

2. Install backend dependencies from the repository root:

   ```bash
   python3 -m venv backend/.venv
   backend/.venv/bin/python -m pip install -e "backend[dev]"
   ```

3. Install frontend dependencies:

   ```bash
   npm --prefix frontend install
   ```

4. Start the API in one terminal from the repository root:

   ```bash
   backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
   ```

5. Start the frontend in a second terminal:

   ```bash
   cd frontend
   npm run dev
   ```

   Open the local URL printed by Vite (normally `http://localhost:5173`). Vite proxies `/api` requests to the backend at `http://localhost:8000`.

## API usage reports

The backend stores usage in `data/app/api-usage.sqlite3` by default. Set `ROUTELENS_DATA_DIR` in the process environment to use another persistent directory. Relative paths resolve from the repository root. Production backend workers that share global quotas must use the same persistent SQLite database and quota settings. Point the CLI at the same directory.

```bash
backend/.venv/bin/python backend/scripts/api_usage_report.py --days 30 --daily --operations
```

The command is read-only. `--days` selects the number of UTC dates including today and defaults to 30. `--daily` adds per-date totals, and `--operations` adds per-operation totals.

MapTiler geocoding and openrouteservice directions each reserve one attempt in SQLite before HTTP transport. The atomic reservation also records the attempt. Once committed, it counts even if the request is cancelled, times out, receives a provider error, or fails during transport setup. Exhausted requests return HTTP 429 with `daily_quota_exhausted` and a `Retry-After` in seconds until midnight UTC. Unsafe admission returns sanitized HTTP 503 with `daily_quota_unavailable` before provider transport. Excessive concurrent admissions, long worker backlogs, or SQLite contention can trigger temporary 503s while preserving the cap.

Each debounced autocomplete request consumes one geocoding slot when admitted. The 200/day default provides additional headroom. Quota enforcement covers the existing request-scoped provider calls. New background or standalone callers must explicitly integrate equivalent enforcement.

The public API Usage disclosure shows counts for the last 30 UTC dates including today. Its Vancouver camera row counts only image requests. The CLI includes camera catalogue, page, and image requests. Counts represent backend-observed HTTP attempts or committed quota reservations. Provider-account billing totals are authoritative. Browser-side MapTiler map resources are untracked.

A dedicated accounting worker serializes writes and drains the queue on graceful shutdown. Uncapped monitoring is best effort. An abrupt exit can lose pending writes, and exceptional cross-process SQLite contention can cause missed writes.

## Data credits and licensing

The application labels its evidence sources and displays the ECCC attribution. This README credits the providers below. When reusing data, follow the terms that apply to the specific dataset, API plan, and asset:

- **City of Vancouver Road Ahead and camera catalogue metadata:** “Contains information licensed under the [Open Government Licence – Vancouver](https://opendata.vancouver.ca/pages/help/).” The licence for metadata does not by itself establish reuse rights for separately linked camera images. Camera imagery has distinct terms and rights considerations.
- **DriveBC Open511:** “Contains information licensed under the [Open Government Licence – British Columbia](https://pub.data.gov.bc.ca/license/OGL-vbc2.0.pdf). Source: DriveBC Open511 (Government of British Columbia).”
- **Environment and Climate Change Canada GeoMet/SWOB:** “Contains information licensed under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada). Source: Environment and Climate Change Canada GeoMet/SWOB.”
- **OpenWeather:** Visible attribution is required; use **“Weather data © OpenWeather”** with a link to [OpenWeather](https://openweathermap.org/) and follow the current API subscription terms.
- **MapTiler and openrouteservice:** These provide map/geocoding and routing services; follow their current terms and attribution requirements. The rendered map also presents its provider/source attribution.

This portfolio MVP is not a legal determination of data or image rights. Review current provider terms before redistribution, public deployment, or commercial use. See [`docs/data-licensing-and-commercialization.md`](docs/data-licensing-and-commercialization.md) for the project's licensing notes.

## Scope and limitations

- Supported journeys are driving journeys into the City of Vancouver. Origins may be elsewhere in the surrounding region; destinations outside Vancouver and journeys out of Vancouver are unsupported.
- Route candidates are approximate context, not navigation directions, an ETA, or a guarantee that the route matches another navigation service.
- Camera coverage is limited to available Vancouver views near the selected destination. A camera view is local evidence, not a description of the whole route or destination, and AI interpretation can be uncertain.
- RouteLens checks the primary image at up to four nearest eligible camera intersections and skips matches to the known offline placeholder. OpenRouter interprets one eligible view from the gallery's validated selection. Matching against a newly captured live City outage image remains unverified. Camera interpretation can still arrive too late for the first briefing.
- Data sources refresh on different schedules and may be missing, stale, delayed, or unavailable. The UI reports source status and freshness where available; a missing source does not mean conditions are clear.
- Weather observations, forecasts, and camera appearance represent different kinds of evidence and should not be treated as interchangeable.

## MVP and future ideas

**Implemented MVP:** driving-route selection; Vancouver destination validation; interactive map; municipal and regional road context; destination camera views and structured camera interpretation; destination weather from OpenWeather and ECCC/SWOB; and the source-grounded three-topic AI Journey Briefing.

**Deferred or future work:** transit and GTFS alerts, DriveBC cameras, journeys whose destination is outside Vancouver, richer timeline and cross-source analysis, and further integration/presentation hardening. These are not current MVP capabilities.

## Project notes

- [Application specification](APP_SPEC.md)
- [Current project state](PROJECT_STATE.md)
- [Implementation plan](docs/implementation-plan.md)
- [License](LICENSE)

Automated tests and fixtures are maintained in `backend/tests/`, `frontend/tests/`, and `fixtures/`.
