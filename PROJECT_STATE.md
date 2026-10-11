# RouteLens AI — Project State

## 1. Current Status

**Project:** RouteLens AI  
**Planning:** Substantially complete — authoritative documents established  
**Current phase:** Phase 3 — Drive Route Candidates + Selection
**Phase status:** Assignment 3A implementation complete; ready for human review
**Human review:** Completed — Assignments 2A–2C and full Phase 2 accepted by human developer on 2026-10-10
**Git checkpoint:** Assignment 1A `01ff452`; Assignment 1B `c2c501b`; Assignment 1C `fb931ad`; Assignment 2A `d46e12a`; Assignment 2B `f3b7d65`; Assignment 2C pending human commit
**Repository baseline:** Inspected for Assignment 0A

Assignment 0A validated the root SDD harness and inspected repository contents; at that time no application source or automated tests were found. Assignments 0B–0D added sanitized provider evidence and readiness notes. Assignment 0E consolidated the evidence and finalized `.env.example`. Assignments 1A–1C established the app foundation, interactive Vancouver basemap, and desktop shell; Phase 1 was accepted on 2026-10-10. Assignments 2A–2C delivered and verified geocoding, destination validation, and canonical location selection; Phase 2 was accepted on 2026-10-10. Assignment 3A adds the backend ORS driving-candidate API only. No route UI, telemetry, or AI journey analysis has been implemented. The Phase 0 assessment is `docs/integration-notes/phase-0-readiness-summary.md`.

## 2. Established Planning Artifacts

The following documents define approved project intent:

- `docs/prd.md` — product requirements and MVP scope.
- `docs/technical-design.md` — architecture and integration design.
- `docs/implementation-plan.md` — Phase 0–13 roadmap.
- `docs/development-workflow.md` — development responsibilities and workflow.
- `docs/data-licensing-and-commercialization.md` — data-use and commercialization research.

The Codex SDD harness has been drafted and accepted as v1:

- `AGENTS.md` — agent operating rules.
- `APP_SPEC.md` — condensed application specification.
- `BUILD_PLAN.md` — current Phase 3 scope and acceptance criteria.
- `PROJECT_STATE.md` — implementation reality and progress.

All four root harness files are present and readable. All five listed planning documents are present.

## 3. Implementation Reality

**Repository implementation status: Assignments 1A–1C, 2A–2C, and 3A implemented; Assignment 3A evidence is recorded in Section 16.**

The Assignment 0A inventory found no backend, frontend, source code, dependency manifest, or application configuration. Later readiness assignments added integration notes and fixtures only. Assignment 1A added the minimal backend/frontend foundation, Assignment 1B added the interactive MapLibre map with MapTiler's dark Vancouver basemap, and Assignment 1C added the desktop shell and intelligence placeholders. Assignments 2A–2C implement backend geocoding/validation and frontend location selection. Assignment 3A implements backend route-candidate retrieval; route rendering, selection, and journey analysis are not implemented.

At the Assignment 0A inventory, no automated test infrastructure, API integration scripts, or build tooling was found. Assignment 1A now provides a backend pytest/Ruff setup and a Vite/TypeScript/Tailwind frontend. Assignment 2B adds a shared React location autocomplete and parent-owned canonical origin/destination state. Assignment 3A adds normalized ORS driving routes through the backend. Assignment 0B added two observed OpenWeather response fixtures under `fixtures/openweather/`.

`.gitignore` is present and includes `.env`. The ignored local `.env` has MapTiler, ORS, OpenWeather, and OpenRouter credentials; `TRANSLINK_API_KEY` is absent locally, although planning research records prior testing. Secret values were not displayed or changed. Assignment 0E created `.env.example` with the five approved credential names and both tested provisional OpenRouter model identifiers.

## 4. Planning Research Baseline

Substantial external-data research was completed before implementation.

| Source | Planning Research Status |
|---|---|
| Vancouver Webcams | Catalogue and directional image-discovery strategy investigated |
| Vancouver Road Ahead | Both datasets, full geometry, detail enrichment, and daily caching investigated |
| DriveBC Open511 | Regional bounding-box fetching, pagination, and relevance separation investigated |
| ECCC GeoMet / SWOB | Live observations retrieved; sparse stations and missing values characterized |
| TransLink | API key tested; GTFS Static and Service Alerts investigated; matching approach established |
| OpenWeather | Current and 5 day / 3 hour endpoints and live schemas verified in Assignment 0B; active plan/quota remain unknown |

These findings are documented in the planning artifacts. They are planning evidence, separate from repository verification; Assignment 0B's live OpenWeather results are recorded in the integration note and fixtures.

Do not repeat completed research unless a specific readiness requirement or implementation discrepancy warrants it.

## 5. Phase 0 Workstream Status

| Workstream | Status | Remaining Requirement |
|---|---|---|
| OpenWeather | Validated — current and forecast endpoints | Review account-specific plan/quota and applicable terms; evidence and fixtures are in `docs/integration-notes/openweather-readiness.md` and `fixtures/openweather/` |
| MapTiler | Live access and schema validated for representative requests | Confirm active-plan quota/attribution details; MapLibre rendering remains Phase 1 |
| openrouteservice | Live driving routes and alternatives validated for three journeys | Confirm account-specific quota/terms; fewer-than-requested route behavior was not observed |
| OpenRouter | Preliminary synthetic readiness validated for both roles | One vision response truncated before a corrective call; one text response had an inconsistent status before correction; general reliability and real-camera accuracy remain untested. Evidence is in `docs/integration-notes/openrouter-readiness.md` and `fixtures/openrouter/` |
| Environment configuration | Ready for review with one credential follow-up | `.gitignore` excludes `.env`; `.env.example` now documents all five keys and both model variables; local TransLink key is absent and should be configured before Phase 10 |
| Fixtures and evidence | Ready for review | OpenWeather, MapTiler, ORS, and synthetic OpenRouter evidence and fixtures exist and were audited in Assignment 0E; planning-stage sources are not represented as repository live fixtures |

The complete acceptance boundary is defined in `BUILD_PLAN.md`.

Workstreams may be completed through separate bounded Codex assignments.

Phase 0 is **Accepted by the human developer as of 2026-10-09**, with documented non-blocking follow-ups. Assignment 0E consolidated Assignments 0A–0D and verified the configuration template and existing artifacts. The accepted follow-ups are: configure the local TransLink key before Phase 10; resolve Vancouver camera-image rights and external AI processing permissions before Phase 8; and review provider plans, quotas, and applicable terms before broader or public use. Phase 1 was accepted on 2026-10-10. Assignment 2C verification is complete; Phase 2 is awaiting human acceptance.

## 6. Verification Evidence

**Assignments 0A–0D repository and integration verification: Recorded below.**

| Verification Area | Latest Known Result |
|---|---|
| Root harness presence/readability | Passed — all four files present and readable |
| Repository inventory | Passed — tracked files and repository directories inspected |
| Backend tests / pytest | Not run — no application or test infrastructure found; outside Assignment 0A scope |
| Ruff | Not run — no Python application code found; outside Assignment 0A scope |
| Frontend build | Not run — no frontend or build tooling found; outside Assignment 0A scope |
| Assignment 0A live Phase 0 checks | Not run — explicitly outside Assignment 0A scope |
| Assignment 0B OpenWeather current endpoint | Passed on retry — initial request returned HTTP 401; later request returned HTTP 200 and `cod=200` |
| Assignment 0B OpenWeather forecast endpoint | Passed — HTTP 200, `cod=200`, 40 forecast entries at exact 3-hour spacing over five days |
| Assignment 0B response fixtures | Passed — actual successful JSON bodies saved under `fixtures/openweather/` |
| Assignment 0B schema review | Passed — current and forecast field presence, missing precipitation objects, explicit forecast zero values, and timestamps inspected |
| Assignment 0B API documentation review | Passed — endpoint details, request guidance, cache recommendation, and public pricing reviewed; account plan/remaining quota remain unverified |
| Assignment 0A environment configuration | Partial — `.gitignore` excluded `.env`; `.env.example` and local env files were absent at that inspection |
| Assignment 0B OpenWeather configuration | Passed for access — ignored `.env` defines `OPENWEATHER_API_KEY`; value not exposed; both endpoints succeeded on retry |
| Credential value | Not displayed or copied into artifacts; passed only to the authorized OpenWeather requests |
| Assignment 0B fixture validity and credential scan | Passed — both fixtures parse as JSON and the configured key value is absent from changed artifacts |
| Assignment 0C MapTiler geocoding/autocomplete | Passed — representative Vancouver-area requests returned GeoJSON features; broad-query ambiguity and contextual fields inspected |
| Assignment 0C MapTiler dark style/resources | Passed — `streets-v4-dark` style, TileJSON, a Vancouver vector tile, sprites, and valid glyph resources returned successfully; application rendering not tested |
| Assignment 0C ORS driving routes | Passed — three representative `driving-car` requests returned usable GeoJSON LineStrings and distance/duration summaries |
| Assignment 0C ORS alternatives | Passed for sampled journeys — each returned three routes; fewer-than-requested behavior not observed |
| Assignment 0C response fixtures | Passed — actual sanitized geocoding, style, and route responses saved under `fixtures/maptiler/` and `fixtures/openrouteservice/` |
| Assignment 0C fixture/schema and credential scan | Passed — 7 MapTiler JSON and 3 ORS GeoJSON fixtures parsed and checked; configured key values absent from readiness artifacts |
| Assignment 0C `.env` ignore rule | Passed — `git check-ignore -q .env` |
| Assignment 0C whitespace and `git diff --check` | Passed — new note has no trailing whitespace and `git diff --check` reported no issues |
| Assignment 0D OpenRouter configuration/authentication | Passed — ignored `.env` contains the key and both role variables set to `google/gemma-4-31b-it`; four API requests returned HTTP 200; no credential value was displayed or saved |
| Assignment 0D model/capability/pricing review | Passed — current OpenRouter model page and endpoint metadata reviewed; image/text input, text output, endpoint-specific `structured_outputs`, tested DeepInfra Turbo pricing, and provider information recorded |
| Assignment 0D multi-image vision | Partial — two synthetic images were accepted together in one request; first output truncated at 240 tokens, corrective strict-schema response parsed and passed field checks |
| Assignment 0D structured text briefing | Partial — both responses parsed; first had a status inconsistency, corrective response passed structural/manual grounding review; camera-to-route relevance remains unverified |
| Assignment 0D request counts, usage, and costs | Passed — 4/4 paid API calls returned HTTP 200; one vision response was truncated/invalid JSON; one text response had a semantic status inconsistency; 3,674 total tokens; provider-reported cost $0.00047691 |
| Assignment 0D fixtures and credential scan | Passed — synthetic inputs, actual outputs, first/failed attempts, and sanitized metadata saved under `fixtures/openrouter/`; all 9 JSON fixtures parsed, final contract checks passed, credential scan found no key value |
| Assignment 0D `.env` ignore rule | Passed — `git check-ignore -q .env` |
| Assignment 0D `git diff --check` | Passed — no whitespace errors |
| Assignment 0E fixture inventory and parse/structure audit | Passed — required notes and fixtures present; JSON and GeoJSON parsed and representative expected structures checked |
| Assignment 0E configuration and credential audit | Passed — five credential names and both provisional model variables in `.env.example`; no secret values found in the audited artifacts; `.env` remains ignored and was not modified; local TransLink key identified as missing |
| Assignment 0E planning/live evidence distinction | Passed — public and transit source research is labeled planning-stage; live verification claims are limited to OpenWeather, MapTiler, ORS, and OpenRouter |
| Assignment 0E no-live-call boundary | Passed — no APIs or inference providers were called |
| Assignment 0E final diff/status checks | Passed — `git diff --check` clean; only `.env.example`, the consolidated summary, and `PROJECT_STATE.md` are changed |
| Initial repository Git status | Passed — clean `main` tracking `origin/main` before this state update |
| Assignment 0A final repository Git status | Passed — only `PROJECT_STATE.md` was modified for that assignment |

Planning-stage API experiments are recorded separately from repository verification. No external APIs were called during Assignment 0A. Assignment 0B's OpenWeather findings are recorded in `docs/integration-notes/openweather-readiness.md`; Assignment 0C's live findings are recorded in `docs/integration-notes/geographic-services-readiness.md`; Assignment 0D's OpenRouter findings are recorded in `docs/integration-notes/openrouter-readiness.md`.

Future updates should include meaningful verification results, relevant environment context, and unresolved failures.

Use **Passed**, **Failed**, or **Not run** for checks.

Do not preserve extensive terminal transcripts or historical test logs in this document.

## 7. Implementation Decisions and Discoveries

Assignment 0A confirmed that the current repository contains planning and harness materials only; it did not establish application implementation decisions.

Approved product and architectural decisions remain in `APP_SPEC.md` and the authoritative planning documents.

Record future implementation discoveries here when they materially affect:

- actual source behavior;
- implementation limitations;
- local technical choices;
- deviations from approved expectations;
- future phase readiness.

Do not silently convert observed implementation differences into changes to approved architecture.

## 8. Known Limitations and Blockers

### Known Readiness Gaps

- OpenWeather current and forecast endpoints and their observed schemas are verified. The account's subscription, remaining quota, and plan-specific terms remain unknown and should be confirmed before broader use or release.
- MapTiler geocoding, dark-style resources, and ORS driving routes/alternatives were accessible in Assignment 0C. Assignment 1B confirmed browser rendering of the MapTiler dark style. Account-specific quotas, terms, and whether the active MapTiler plan requires its logo remain unverified. MapTiler search results can be ambiguous and require contextual review; POI categorization can be imperfect.
- ORS returned three alternatives for the three sampled trips. Fewer-than-requested behavior was not directly observed and three candidates are not guaranteed for arbitrary journeys.
- OpenRouter accepted the provisional Gemma model for both synthetic readiness requests through DeepInfra. One successful vision response was obtained after a truncation; one text status inconsistency was corrected. These small samples do not establish production reliability, real-camera accuracy, or robustness.
- OpenRouter and DeepInfra publish favorable retention/training claims for the tested route, but account-level privacy controls were not inspected. The real Vancouver camera-image licence and permission to transmit those images for AI inference remain unresolved.
- A local ignored `.env` does not define `TRANSLINK_API_KEY`; planning research records that credentials were previously obtained and tested. Configure/confirm the key before Phase 10. Its value was not exposed.
- No application test infrastructure or production integration code was created. Readiness notes and fixtures now exist for OpenWeather, MapTiler, ORS, and OpenRouter.
- The `README.md` describes DriveBC Cameras as a planned core source, while `APP_SPEC.md` explicitly excludes DriveBC Cameras from the MVP. This pre-existing scope discrepancy is outside Assignment 1B.
- **Local VMware/Chromium WebGL compatibility (Assignment 1B):** The Debian 13 VMware Workstation development VM uses the VMware SVGA3D renderer (`vmwgfx`, Mesa OpenGL 4.3). Brave and Chrome initially blocklisted WebGL, preventing MapLibre from initializing. Enabling VMware 3D acceleration and Brave's `Override software rendering list` flag (`brave://flags/#ignore-gpu-blocklist`) restored map rendering in Brave. Firefox rendered the map without this override. This is a local browser/VM graphics compatibility issue, not a confirmed RouteLens application defect. The Chromium override is intended for local development only.

These are outstanding readiness requirements, not confirmed service failures.

### Confirmed Implementation Blockers

None established through repository inspection.

Additional blockers must be recorded when discovered, including affected workstreams and their impact.

## 9. Phase Acceptance and Git Handoff

**Phase 0 acceptance:** Accepted — 2026-10-09, with documented non-blocking follow-ups
**Phase 0 Git checkpoint:** Committed and pushed — human-confirmed
**Phase 1 acceptance:** Accepted — 2026-10-10, following human browser and functional review
**Phase 1 human review:** Completed — map rendering, pan/zoom, desktop layout, panel behavior, and backend connectivity verified
**Phase 1 Git checkpoint:** Assignment 1A `01ff452`; Assignment 1B `c2c501b`; Assignment 1C `fb931ad`
**Phase 2 progress:** Assignment 2A accepted and committed as `d46e12a`; Assignment 2B accepted and committed as `f3b7d65`; Assignment 2C verification complete and ready for human review
**Phase 2 acceptance:** Accepted — 2026-10-10, following human functional review and Assignment 2C integrated verification
**Phase 2 human review:** Completed — geocoding, canonical selection, destination validation, rejection recovery, location-state integrity, map behavior, and desktop layout verified
**Phase 2 Git checkpoint:** Assignment 2A `d46e12a`; Assignment 2B `f3b7d65`; Assignment 2C pending human commit

Use the following status distinctions:

- **Planned** — authorized work has not begun.
- **In progress** — implementation or verification underway.
- **Ready for review** — Codex reports required work and available checks complete.
- **Accepted** — human has explicitly approved the phase.
- **Blocked** — required work cannot proceed without a decision or dependency.

Codex may report readiness for review but must not independently declare human acceptance.

Only record a Git checkpoint as completed when confirmed by the human or verified through repository evidence.

Codex must not stage, commit, push, merge, rebase, tag, or rewrite Git history.

## 10. Assignment 1A Status and Verification

Assignments 0A–0E are **completed and accepted by the human developer as of 2026-10-09**. Phase 0 established integration readiness for OpenWeather, MapTiler, openrouteservice, and OpenRouter, supported by sanitized fixtures and readiness documentation. Planning-stage research for Vancouver Webcams, Road Ahead, Open511, SWOB, and TransLink remains distinguished from repository-based live verification.

The following non-blocking follow-ups remain: configure the local TransLink key before Phase 10; resolve camera-image rights and external AI processing permissions before Phase 8; and review provider account limits and applicable terms before broader or public use.

Assignment 1A implements a minimal FastAPI health endpoint and React/Vite/TypeScript/Tailwind scaffold. The frontend makes one `/api/health` request and shows checking, connected, or unavailable status. Vite proxies `/api` to the local backend. Assignment 1A was accepted and committed as `01ff452`.

| Check | Result |
|---|---|
| Backend import and startup | Passed — Uvicorn started and completed application startup on `127.0.0.1:8000` |
| `GET /api/health` direct request | Passed — HTTP 200, `{"status":"ok"}` |
| Backend pytest | Passed — 1 health endpoint test |
| Ruff | Passed — `ruff check app tests` |
| Frontend install | Passed — npm dependencies installed and lockfile generated |
| TypeScript and production build | Passed — `npm run build` (`tsc -b && vite build`) |
| Vite development server | Passed — started on `127.0.0.1:5173` |
| Proxied `GET /api/health` | Passed — Vite returned the backend HTTP 200 health response |
| Backend unavailable proxy response | Passed — Vite returned HTTP 502 while the frontend route remained available; the UI catches failed requests and sets unavailable state |
| Tailwind build output | Passed — generated CSS contains the scaffold utility selectors |
| Browser visual/rendered-state inspection | Not run for Assignment 1A; Assignment 1B browser checks are recorded in Section 11 |
| Credential requirement | Passed — no external provider credentials are used by this foundation; `.env` and `.env.example` were preserved |
| Git history operations | None — no staging, commit, push, or history changes were performed |

**Review status:** Accepted by the human developer; committed as `01ff452`.

Phase 0 and Assignment 1A remain accepted. Assignment 1B review is complete, and its map verification is recorded below.

## 11. Assignment 1B — Interactive Vancouver Map

Assignment 1B adds a lifecycle-safe MapLibre GL JS component using MapTiler's validated `streets-v4-dark` style, centered at `[-123.1207, 49.2827]` at zoom 12. Vite selectively reads `MAPTILER_API_KEY` from the project-root `.env` and defines only `VITE_MAPTILER_API_KEY` for browser code. `envPrefix` is disabled to prevent automatic exposure of other environment variables. MapLibre's packaged worker is emitted as a Vite URL asset. The map includes navigation controls, provider attribution, loading, configuration-required, and resource-failure states. ResizeObserver updates map dimensions; unmount cleanup removes observers, listeners, and the MapLibre instance.

| Check | Result |
|---|---|
| MapLibre dependency and lockfile | Passed — MapLibre GL JS 6.13.0 installed; npm reported 0 vulnerabilities. Install emits a non-fatal Node engine warning for its `@mapbox/jsonlint-lines-primitives` dependency (requires Node 22); the Node 20.19 dev server and build both run successfully |
| Frontend TypeScript and production build | Passed — `npm run build`; Vite emits the worker asset. Build reports a large JavaScript chunk warning for MapLibre |
| Browser style and supporting resources | Passed — Chrome rendered Vancouver; 19 MapTiler requests returned HTTP 200 in the verified session |
| Browser viewport and attribution | Passed — map canvas filled its container; MapTiler and OpenStreetMap attribution was visible |
| Pan and zoom | Passed — drag-pan and the MapLibre zoom control both changed the rendered frame |
| Browser resizing | Passed — after viewport resize, map canvas dimensions matched the resized map frame |
| Map loading state | Passed — loading presentation cleared after map load |
| Missing MapTiler key | Passed — separate Vite server with the key unset displayed the configuration-required message without creating a map canvas |
| Backend status and Vite `/api` proxy | Passed — browser showed backend connected during the live-map session; missing-key session retained the unavailable status when backend was stopped |
| Backend pytest | Passed — 1 existing health test |
| Ruff | Passed — `ruff check backend/app backend/tests` |
| Browser console | Passed with non-blocking warning — worker-loading issue found during development was fixed; final style emits a missing optional sprite-image warning for `transportation:road_`; no application exception remained |
| `.env` ignore and credential exposure | Passed — `.env` remains ignored; browser build exposes only the intended MapTiler key; backend-only credential values are absent from browser assets and changed source |
| `git diff --check` | Passed — no whitespace issues |

The browser verification used headless Chrome with MapTiler requests succeeding. The actual map was visually inspected and interaction/resizing checks were exercised. The browser key is intentionally visible in browser requests and generated assets; review provider-supported restrictions and the active plan's logo requirement before any shared or public deployment. No automatic retry behavior is implemented.

**Review status:** Human review completed; Assignment 1B is committed as `c2c501b`.

## 12. Assignment 1C — Desktop Shell and Visual Integration

Assignment 1C replaces the tall scaffold page with a viewport-filling desktop interface: branded header and one-shot backend status, visibly inactive origin/destination/mode/analyze placeholders, a fixed 65/35 map and intelligence workspace, and a vertically scrollable panel with honest empty states for conditions, road context, transit, cameras, and AI briefing. The existing `VancouverMap` implementation and its MapLibre lifecycle, MapTiler style, Vancouver viewport, controls, attribution, worker URL, resize observer, and loading/error handling were preserved. The attribution presentation was adjusted for the dark shell. No dependencies or later-phase journey behavior were added.

| Check | Result |
|---|---|
| Frontend TypeScript and production build | Passed — `npm run build`; Vite reports the existing large MapLibre bundle warning |
| Vite development server | Passed — started on `127.0.0.1:5173` |
| Backend import | Passed — `app.main` imports as `RouteLens AI API` |
| Backend pytest | Passed — 1 health endpoint test |
| Ruff | Passed — `ruff check app tests` |
| Backend health through Vite `/api` proxy | Passed — Chrome showed connected and FastAPI recorded successful health requests |
| Backend unavailable frontend state | Passed by earlier Assignment 1A/1B verification; no new failure-state browser session was captured for 1C |
| Desktop/narrow layout inspection | Passed — headless Chrome screenshots at 1440×900, 1280×800, 1024×768, and 430×900; desktop retains two columns, the panel scrolls independently at 1024×768, and the narrow view stacks without horizontal overflow |
| Browser console | Passed with a non-fatal warning — the MapTiler style reported its optional `transportation:road_` sprite image missing; no application exception was reported in the observed Vite output |
| Map rendering and interaction in 1C | Passed during human review — the developer verified real Vancouver basemap rendering, map interactions, attribution, and layout behavior in the configured Brave browser. Codex's separate headless Chrome test failed to render the basemap and remained on the loading overlay; this limitation is preserved as an environment-specific verification discrepancy, not a confirmed application defect. |
| `.env` ignore rule | Passed — `git check-ignore -q .env` |
| Backend-only secret values in production assets | Passed — checked configured backend credential values without printing them; none were present |
| `git diff --check` | Passed — no whitespace errors |
| Git history operations | None — no staging, commit, push, or history changes were performed for Assignment 1C |

### Phase 1 acceptance assessment

| Phase 1 requirement | Assessment |
|---|---|
| FastAPI startup, `/api/health`, pytest, and Ruff | Satisfied — Assignment 1A/1C checks passed |
| React/Vite/TypeScript frontend startup and production build | Satisfied — 1C build and dev server passed |
| Frontend-to-backend connection through `/api` and graceful unavailability | Satisfied — successful connection rechecked in 1C; unavailable state was verified in 1A/1B |
| MapTiler dark map, Vancouver initial view, pan/zoom, attribution, resize | Satisfied — successful Assignment 1B verification and completed Assignment 1C human browser review; headless Chrome rendering limitation documented separately |
| Top controls, fixed 65/35 desktop layout, readable right panel, inactive placeholders | Satisfied by 1C implementation and viewport inspection |
| No fabricated telemetry; no later-phase behavior | Satisfied by source and visual inspection |
| Local startup instructions, selective MapTiler key exposure, `.env` ignore | Satisfied — existing instructions/configuration retained; ignore and production asset checks passed |
| `PROJECT_STATE.md`, browser verification, and Git boundary | Satisfied — this assessment records the remaining map-rendering verification caveat; no Git history operation occurred |

**Phase status:** Accepted by the human developer on 2026-10-10. Assignments 1A–1C established a working FastAPI backend, React/Vite frontend, interactive Vancouver basemap, and desktop intelligence shell. Automated verification and human browser inspection are complete. The documented headless Chrome rendering discrepancy and other non-blocking limitations remain visible.

**Next action:** Assignment 2B implementation and verification are recorded in Section 14. Phase 2 remains in progress.

## 13. Assignment 2A — Geocoding and Location Validation

Assignment 2A adds a server-side async MapTiler adapter and two backend endpoints. The approved `Location` fields are `name`, `latitude`, and `longitude` (required), with `address` and `provider_id` optional. A geocoding candidate requires a provider feature identifier, name, and valid Point coordinates; malformed candidates are skipped. GeoJSON `[longitude, latitude]` is normalized to the canonical `longitude` and `latitude` fields without inversion. The API returns up to five normalized matches from `GET /api/geocoding/search?q=...`; search is limited to Canada and Vancouver proximity biases ranking. Neither is an enforceable Lower Mainland origin boundary. `POST /api/locations/validate-destination` checks canonical coordinates, with no origin city-boundary rule.

Destination validation uses the City of Vancouver Open Data Portal's `city-boundary` GeoJSON export, retrieved 2026-10-10. The source describes the data as the line defining the City's legal jurisdiction; its 14 MultiLineString segments polygonize into one valid polygon. Shapely `covers(point)` means a point exactly on the boundary is accepted. The City notes that some boundary features are less precise than survey accuracy. The dataset is published under the Open Government Licence – Vancouver. The local source artifact is `backend/app/data/city-boundary.geojson`; provenance is the [City boundary dataset](https://opendata.vancouver.ca/explore/dataset/city-boundary/map/) and [City open data licence](https://opendata.vancouver.ca/pages/licence/). No exact Lower Mainland origin polygon is defined by the approved design, so no such restriction was invented.

| Check | Result |
|---|---|
| Backend import and health endpoint | Passed — FastAPI imports and `GET /api/health` remains available |
| Backend tests | Passed — 38 tests, including normalization, mocked HTTP failures, API behavior, boundary inclusivity, nearby municipalities, and health endpoint |
| Ruff | Passed — `ruff check backend/app backend/tests` |
| Frontend production build | Passed — `npm run build`; existing large MapLibre chunk warning remains |
| Targeted live MapTiler/API check | Passed — three backend endpoint searches (Downtown Vancouver, Richmond, Burnaby) each returned HTTP 200 and five normalized candidates; Downtown validated inside, Richmond and Burnaby outside; coordinate order/ranges were valid |
| `.env` ignore and secret safety | Passed — `.env` remains ignored; no credential-bearing URLs or raw upstream errors are returned; configured key was not printed or added to tracked files |
| MapLibre code, Vite `/api` proxy, and desktop shell | Preserved; no frontend source was changed |

Known scope limit: the origin search is biased toward Vancouver and limited to Canada, but there is no deterministic Lower Mainland origin acceptance boundary. Destination validation uses the official City boundary and is independent of geocoder names and ranking. No frontend journey controls or routing behavior were added.

**Review status:** Accepted by the human developer on 2026-10-10. Manual API verification confirmed real MapTiler suggestions and deterministic geographic validation: Downtown Vancouver was accepted and Richmond was rejected. Automated verification passed with 38 backend tests, Ruff, and the frontend production build. Provider suggestions from outside the intended search area were observed and will be handled through geographic context and destination validation in later assignments.

**Next action:** Assignment 2B implementation and verification are recorded in Section 14. Assignment 2C remains required before Phase 2 acceptance.

## 14. Assignment 2B — Journey Input Interface

Assignment 2B replaces the origin and destination placeholders with a shared `LocationAutocomplete` component. It uses the relative FastAPI endpoints `/api/geocoding/search` and `/api/locations/validate-destination`, keeps separate canonical `Location | null` values in `JourneyControls`, and only accepts a destination after backend validation. Origin edits clear only origin state. Destination validation has pending, geographic rejection, and request-failure feedback; rejected or unverified candidates are not retained as accepted destinations. Search is normalized, debounced by 300 ms, skipped below two characters, and protected from stale responses with abort signals and request identity checks. Inputs support Arrow Up/Down, Enter, Escape, pointer selection, and combobox/listbox semantics. Drive remains the active presentation, Transit and Analyze Journey remain disabled, and no routing or analysis behavior was added. `VancouverMap` was not changed.

| Check | Result |
|---|---|
| Frontend TypeScript and production build | Passed — `npm run build` (`tsc -b && vite build`); the existing large MapLibre bundle warning remains |
| Backend regression tests | Passed — 38 tests |
| Ruff | Passed — `ruff check app tests` |
| Vite development server | Passed — started on localhost after sandbox approval |
| FastAPI through Vite `/api` proxy | Passed — `/api/health` returned HTTP 200 and `{"status":"ok"}` |
| Live backend geocoding | Passed — `Downtown Vancouver` returned five real candidates with Vancouver, Victoria, and New Westminster context; `Richmond` returned a canonical candidate |
| Live destination validation | Passed — a Downtown Vancouver point was accepted; Richmond was rejected with the backend's City of Vancouver reason |
| Browser autocomplete flow | Passed — headless Chrome selected an origin by pointer and a destination by keyboard, accepted a valid destination, rejected Richmond, replaced it with a valid location, and confirmed editing origin preserves the valid destination |
| Browser asynchronous and keyboard behavior | Passed — rapid query replacement showed latest results; Escape closed suggestions |
| Browser layout and map observation | Passed in observed desktop viewport — no horizontal overflow, Analyze Journey remained disabled, and MapLibre canvas and attribution were present. Map pan/zoom was not re-tested in this assignment; `VancouverMap` is unchanged |
| Empty and search-failure browser states | Passed with mocked fetch responses — empty results and unavailable search show distinct user-facing feedback |
| Narrow-screen dropdown clipping | Passed at 390×844 — no horizontal overflow and the suggestion list fit within the viewport |
| `.env` ignore and backend-only provider scan | Passed — `.env` remains ignored; no backend-only provider references were added to frontend source or build output |
| `git diff --check` | Passed — no whitespace errors |
| Git history operations | None — no staging, commit, push, or history changes were performed |

Known limitation: origin search uses the backend's Canada-limited, Vancouver-biased MapTiler search and does not enforce a Lower Mainland polygon. Empty-result and search-failure UI states were verified with mocked browser responses; a real provider outage and destination-validation network failure were not induced. Map pan/zoom was not re-tested in this assignment. Assignment 2C remains responsible for comprehensive end-to-end verification and Phase 2 acceptance. No dependency or API contract changes were introduced.

**Review status:** Accepted by the human developer on 2026-10-10. Manual browser testing confirmed functional origin/destination autocomplete, real suggestion selection, successful City of Vancouver destination validation, Richmond destination rejection, recovery after rejection, selection invalidation, and preservation of independent location state. The frontend layout, MapLibre interaction, and inactive later-phase controls behaved as expected. Automated verification passed with 38 backend tests, Ruff, and the frontend production build.

**Remaining verification:** A real provider outage and destination-validation network failure were not induced. The lack of a strict Lower Mainland origin boundary remains documented. Assignment 2C will perform final integration, regression, and Phase 2 acceptance checks.

**Next action:** Human review and acceptance decision for Assignment 3A. Assignment 3B requires separate authorization after acceptance.

## 15. Assignment 2C — End-to-End Verification and Phase 2 Assessment

Assignment 2C verified the accepted 2A/2B integration without changing application code or API contracts. No demonstrated source defect required correction. Phase 2 is ready for human acceptance review; this status does not represent human acceptance.

| Verification | Result |
|---|---|
| Backend startup and health | Passed — FastAPI started; direct `GET /api/health` and the Vite `/api/health` proxy returned HTTP 200 with `{"status":"ok"}` |
| Live geocoding through the frontend proxy | Passed — authenticated MapTiler searches for Richmond, Burnaby, and Downtown Vancouver each returned five normalized candidates; provider coordinates and context matched the canonical contract |
| Live destination validation | Passed — Downtown Vancouver accepted; Richmond and Burnaby rejected with the City of Vancouver boundary reason; out-of-range latitude rejected with HTTP 422 |
| Backend regression tests | Passed — 38 pytest tests, including malformed provider candidates, normalization and coordinate ordering, nearby municipalities, boundary `covers` behavior, API failures, and health |
| Ruff | Passed — `ruff check backend/app backend/tests` |
| Frontend TypeScript and production build | Passed — `npm run build` (`tsc -b && vite build`); the existing large MapLibre chunk warning remains |
| Browser valid/rejected/recovery flow | Passed — Chrome selected Richmond origin and Downtown Vancouver destination, accepted both, rejected Richmond destination, removed any prior accepted destination, retained origin, recovered with Downtown, and accepted a Burnaby origin with a valid Vancouver destination |
| Editing and canonical state | Passed — changing origin cleared only origin; changing destination immediately cleared only destination; validation failure left destination unaccepted and preserved origin |
| Destination-validation request failure | Passed — browser-simulated HTTP 503 showed recoverable “Destination could not be verified” feedback; a subsequent valid selection succeeded |
| Asynchronous search and validation races | Partially verified — controlled stale search and stale validation-success-after-edit cases passed. A delayed rejection after a newer success was not directly completed before the temporary local server session ended; source inspection confirms the shared sequence check precedes both validation outcome branches |
| Search empty/failure and retry states | Passed in the accepted Assignment 2B browser checks using mocked responses; both states were distinct and retry remained available. A live provider outage was not induced |
| Keyboard and pointer interaction | Passed — Arrow Down/Enter selection and Tab focus navigation were checked in Chrome; Escape and pointer selection are covered by accepted Assignment 2B browser evidence |
| MapLibre and desktop shell | Passed — headless Chrome 155 rendered the MapTiler dark Vancouver basemap; zoom control and drag-pan were exercised; controls and attribution remained visible |
| Viewports | Passed — Chrome emulation at 1440×900, 1280×800, 1024×768, and 390×844 showed no horizontal overflow; the desktop map/panel remained at the fixed 65/35 proportions, and the panel remained scrollable |
| Credentials and repository hygiene | Passed — `.env` is ignored; configured non-browser credential values were absent from frontend production assets; no dependency or API-contract change was made |
| Diff and Git boundary | Passed — `git diff --check`; no staging, commit, push, or history operation was performed |

### Phase 2 acceptance criteria (BUILD_PLAN.md, Section 8)

| Criterion | Assessment | Evidence |
|---|---|---|
| Backend MapTiler geocoding integration exists | Satisfied | Accepted 2A implementation and live API searches |
| Real authenticated location search works | Satisfied | Current live MapTiler searches through Vite `/api` proxy |
| Search results use the approved `Location` contract | Satisfied | Backend normalization tests and live response inspection |
| Longitude/latitude ordering is preserved | Satisfied | GeoJSON normalization test and live candidate coordinates |
| Geocoding errors, missing fields, and empty results are handled | Satisfied | 2A parser/API tests; accepted 2B empty/error UI checks |
| Destination validation is deterministic | Satisfied | Coordinate-based Shapely validation and API regression tests |
| Valid City of Vancouver destinations are accepted | Satisfied | Downtown and residential test points; live Downtown validation |
| Nearby non-Vancouver destinations are rejected | Satisfied | Richmond, Burnaby, and North Vancouver regression tests; live Richmond/Burnaby checks |
| Destination boundary tests pass | Satisfied | Included/excluded boundary points verify `covers(point)` semantics |
| Origin locations within the supported examples can be selected | Satisfied | Live browser selections for Richmond and Burnaby origins |
| Origin and destination autocomplete work | Satisfied | Current browser workflow with live suggestions |
| Users can select real geocoding suggestions | Satisfied | Live MapTiler candidates selected by keyboard in Chrome |
| Selected locations persist during normal interaction | Satisfied | Valid journey state remained selected until corresponding input edit |
| Editing a field invalidates its outdated selection | Satisfied | Browser verified independently for origin and destination |
| Destination validation feedback is clear | Satisfied | Browser observed the municipal rejection message and request-failure message |
| Loading, empty, and provider-failure states are understandable | Satisfied | Current pending/validation UI and accepted 2B mocked empty/search-failure checks |
| Stale autocomplete responses cannot overwrite newer results | Satisfied | Controlled delayed search response in Chrome |
| Basic keyboard interaction works | Satisfied | Arrow Down, Enter, Escape, and normal Tab focus behavior |
| Drive remains primary without premature Transit functionality | Satisfied | Drive remains the displayed mode; Drive/Transit controls are disabled |
| The app does not calculate or display routes | Satisfied | Browser/source inspection; Analyze Journey remains disabled |
| Existing MapLibre and FastAPI functionality remains working | Satisfied | Live health/proxy and rendered MapTiler basemap with interaction |
| Fixed 65/35 desktop layout remains usable | Satisfied | Chrome viewport geometry at 1440×900, 1280×800, and 1024×768 |
| No fabricated telemetry or analysis appears | Satisfied | UI shows explicit unavailable/forthcoming placeholders; no route or analysis behavior exists |
| Relevant backend pytest and Ruff checks pass | Satisfied | 38 tests and Ruff passed |
| TypeScript checks and frontend production build pass | Satisfied | `npm run build` passed |
| Representative end-to-end searches are manually verified | Satisfied | Current live Richmond/Burnaby/Downtown browser journey |
| Backend-only credentials are not exposed in the frontend | Satisfied | Non-browser `.env` values absent from production assets; Vite exposes only the browser-usable MapTiler key |
| `PROJECT_STATE.md` accurately records results and limitations | Satisfied | This section records 2C evidence and remaining limitations |
| Completion report and no Git staging/commit/push | Satisfied | Reported for 2C; working tree remains human-controlled |

### Remaining limitations and handoff

- Origin lookup remains Canada-limited and Vancouver-biased. Richmond and Burnaby work, but the approved design defines no exact enforceable Lower Mainland polygon; proximity bias is not an eligibility boundary.
- The City boundary artifact remains the official City of Vancouver `city-boundary` export. Its published precision limitations remain applicable; boundary points are included because validation uses Shapely `covers(point)`.
- Provider subscription, quota, and terms review remains a separate follow-up before broader use.
- Empty/search-failure UI states rely on the accepted 2B mocked browser evidence. This turn simulated destination-validation HTTP failure; it did not induce an actual MapTiler outage or stop the backend to re-test the unavailable status.
- The exact delayed obsolete-rejection-after-newer-success browser interleaving remains unverified. The existing request sequence guard is applied before either the accepted or rejected result can update state; the controlled delayed-success-after-edit case passed.
- Browser evidence used headless Google Chrome 155 with SwiftShader; the map rendered and interaction/layout checks passed. A separate headful Brave session was not run in Assignment 2C.
- No deviation from the authorized Assignment 2C scope. No routing, telemetry, AI, persistence, or Phase 3 work was introduced.

**Review status:** Accepted by the human developer on 2026-10-10. Final browser review confirmed the Phase 2 journey-input workflow, including canonical origin/destination selection, City of Vancouver destination validation, rejection recovery, state invalidation, MapLibre functionality, and desktop layout. The accepted 2A/2B evidence and Assignment 2C regression results satisfy the Phase 2 acceptance boundary.

**Remaining limitations:** A delayed stale rejection after a newer successful validation was not directly exercised; existing request-sequence guards and other concurrency checks provide supporting evidence. Strict Lower Mainland origin-boundary enforcement remains undefined by approved product policy. The official municipal boundary dataset has documented precision limitations. Provider quotas, licensing, and public-deployment requirements remain future follow-ups.

**Phase status:** Phase 2 accepted. Assignment 3A implementation is recorded in Section 16.

**Next action:** Human review of Assignment 3A. No Assignment 3B frontend route selection or rendering work has begun.

## 16. Assignment 3A — Driving Route Backend

The Phase 3 build plan authorizes Assignment 3A. The backend now exposes `POST /api/routes/driving` with a canonical `{"origin": Location, "destination": Location}` request and `{"routes": [...]}` response. It validates both locations through the existing `Location` contract and rejects destinations outside the City of Vancouver using the accepted boundary validator. Origins are not subjected to a new geographic polygon.

`OpenRouteServiceRouter` sends an async request to the ORS `driving-car` GeoJSON directions endpoint with server-side `OPENROUTESERVICE_API_KEY`, canonical coordinates converted to `[longitude, latitude]`, `units=m`, `instructions=false`, and the Phase 0 alternative settings (`target_count=3`, `share_factor=0.6`, `weight_factor=1.4`). A 12-second timeout is applied. Valid routes normalize to the approved `RouteCandidate` fields: request-scoped `route-N` id, actual GeoJSON `LineString` geometry, provider distance in metres, duration rounded to integer seconds, and a short label. Invalid individual geometries or summaries are skipped; valid collections may return zero to three routes without duplication. Duration is an ORS estimate and is not a live traffic ETA.

Provider configuration/authentication failures, rate limits, timeouts, other HTTP failures, and malformed collection responses map to sanitized application errors with machine-readable codes. ORS's explicit unroutable-point response maps to `422 no_route_found`; a valid response with no usable alternatives succeeds with `{"routes": []}`. No route preference is inferred. The existing frontend, MapLibre layers, selection UI, and Vite proxy source were not changed.

| Verification | Result |
|---|---|
| Backend import and health endpoint | Passed — FastAPI imported; `/api/health` regression test returned HTTP 200 |
| Backend pytest | Passed — 79 tests, including accepted fixture normalization, coordinate ordering, one-to-three/zero candidates, invalid route skipping, request parameters, no-route and provider failures, destination boundary, API contract, and health |
| Ruff | Passed — `ruff check backend/app backend/tests` |
| Frontend production build | Passed — `npm run build`; existing large MapLibre bundle warning remains |
| Live ORS adapter request | Passed — one authenticated Richmond-to-Downtown request returned 3 distinct IDs, 278/328/330 coordinates, and positive provider distance/duration summaries |
| Live FastAPI routing request | Passed — HTTP 200, 3 candidates, each with only the normalized application fields and GeoJSON LineString geometry; raw provider `FeatureCollection` was not returned |
| Destination/origin geographic behavior | Passed in deterministic API tests — outside-city destination rejected before provider call; Richmond origin accepted for mocked request behavior |
| `.env` ignore and credential handling | Passed — configured root `.env` remains ignored; key is read server-side, was not printed, and is absent from source/fixtures |
| Frontend source and `/api` proxy | Passed by inspection — frontend files unchanged; existing Vite proxy configuration untouched |
| `git diff --check` | Passed — no whitespace errors |
| Git history operations | None — no staging, commit, push, or history changes were performed |

Live results above are this assignment's observations. Phase 0 separately observed three alternatives on three sample journeys; neither sample establishes a guarantee for all trips. Mocked tests cover fewer candidates, malformed route data, provider errors, and the no-route response. The project still has no enforceable Lower Mainland origin polygon; route alternatives remain subject to ORS availability and its documented alternative-route constraints, including distance limits. Provider quotas and terms remain account-level follow-ups. Assignment 3B must add user-controlled route inspection and selection only after separate authorization and human acceptance.

**Deviations:** None from Assignment 3A. The API reports a legitimate no-usable-route result as HTTP 200 with an empty application-owned `routes` list, preserving the approved candidate contract.

**Review status:** Accepted by the human developer on 2026-10-10. Manual API verification confirmed real ORS driving-route candidates for a representative Richmond-to-Downtown Vancouver journey, including valid GeoJSON geometry, distinct candidate identifiers, and provider-reported distance and duration. The routing endpoint also enforced the City of Vancouver destination boundary. Automated verification passed with 79 backend tests, Ruff, and the frontend production build.

**Remaining limitations:** ORS does not guarantee three alternatives for arbitrary journeys. Provider durations are routing estimates, not live traffic measurements. Strict Lower Mainland origin-boundary enforcement remains undefined in the approved design. Live no-route and upstream-failure scenarios were not induced; deterministic tests cover these behaviors.

**Next action:** Human Git checkpoint followed by separately authorized Assignment 3B — Route Visualization and Selection. Phase 3 remains in progress.
