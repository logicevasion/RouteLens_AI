# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 6 — Current + Near-Term Weather
**Phase status:** Approved for planning; implementation not started. Assignment 6A is the first proposed, separately authorized validation task.
**Source:** `docs/implementation-plan.md`, Phase 6; `docs/prd.md`, weather evidence and source boundaries; `docs/technical-design.md`, ECCC SWOB and OpenWeather sections.
**Previous phase:** Phase 5 — Regional Road Context: DriveBC Open511, implemented, human accepted on 2026-10-11, committed and pushed.

### Objective

Add **destination-focused current and near-term weather evidence** to the accepted driving-only journey experience while keeping two fundamentally different types of evidence separate:

- **ECCC GeoMet/SWOB:** measurements observed at identified physical stations, with explicit station locations, observation times, measurement windows, and coverage limitations.
- **OpenWeather:** coordinate-based structured current conditions and near-term forecast information from an actually validated, accessible API product.

**Selected driving journey + canonical Vancouver destination → cached independent weather source results → conservatively selected destination evidence → source-aware journey response and weather panel.**

Camera imagery and visual interpretation are **not** part of Phase 6. Weather evidence should be ready to compare with destination camera observations in later Phases 7–8 and to supply the source-grounded briefing in Phase 10.

Phase 6 must deliver:

- live evidence establishing which OpenWeather products the existing API credentials actually support;
- sanitized representative OpenWeather and SWOB fixtures, with field and timestamp semantics documented;
- independent weather adapters with validation, provenance, bounded requests, caches, and stale fallback;
- cautious selection of useful station measurements for a Vancouver destination;
- a minimal, additive integration with the existing manual `POST /api/trips/analyze` workflow;
- a readable destination weather section distinguishing **measured observation**, **structured current conditions**, and **forecast**;
- truthful source freshness, partial/unavailable states, and no fabricated precipitation or hyperlocal certainty;
- mocked/fixture-backed regression tests, bounded live smoke verification, and human visual acceptance.

**Scope choice:** Keep the MVP destination-focused. Do not create a grid of observations along every point of the driving route, calculate weather-driven ETA changes, or infer camera conditions before the camera phases.

---

## 2. Execution Scope and Authorization

Phase 6 consists of four **separately authorized** assignments. Completing one does **not** authorize the next. The human developer supplies each bounded Codex assignment prompt and performs Git staging, commit, and push after review.

### Assignment 6A — OpenWeather Access and Contract Validation

- Verify that the existing `OPENWEATHER_API_KEY` is available without disclosing it.
- Check official documentation and make a **small, bounded** set of actual requests to relevant current/forecast products; confirm HTTP outcomes and actual account entitlements without purchasing a subscription.
- Inspect returned schema, units, coordinate interpretation, observed/forecast timestamps, timezone, current condition fields, precipitation fields, forecast intervals, missing values, rate limits and practical request behavior.
- Use one representative **City of Vancouver destination coordinate** for the primary check.
- Recommend the smallest accessible product set that meets the current + near-term use case; record limitations honestly if fine-grained forecasts are unavailable.
- Save sanitized, provider-derived fixtures and a concise source-evidence note under `fixtures/openweather/` and `docs/integration-notes/` where appropriate.
- Recommend, but do **not implement**, endpoint selection, normalization, sampling, TTL, coordinate cache key policy, and stale handling.

**Boundary:** Research/fixture/documentation only. No weather production adapter, no analysis or UI integration, no new dependency, and no Phase 6B–6D work. If credentials or entitlements are unavailable, report a blocker and available documented fallback options rather than assuming success. Keep Phase 6 implementation gated on human approval of findings.

### Assignment 6B — OpenWeather Adapter, Normalization, and Cache

- Implement only the **human-approved product/endpoint contract established by 6A**. Do not silently substitute One Call or another product.
- Use a narrow weather model for fields actually provided: current conditions and near-term forecasts, source locations, timestamps, units, and nullable precipitation/wind/visibility fields where supported.
- Request weather for the canonical destination coordinate, with a documented safe coordinate-based cache key; avoid redundant calls for repeated analyses.
- Use validated cache replacement, source-specific TTL, stale valid cache fallback, bounded timeout/error handling, and truthful `SourceStatus`.
- Distinguish valid empty or unavailable forecast data from a request failure. Do not turn missing precipitation amounts into zero or a forecast into a measured observation.
- Test fixtures, malformed responses, product errors, cache freshness/fallback, location key separation, and time handling offline.

**Boundary:** Backend source adapter only. No SWOB implementation, journey orchestration, frontend, image analysis, or final AI briefing. Any departure from 6A's approved product decision requires escalation.

### Assignment 6C — ECCC SWOB Observation Adapter and Selection

- Verify actual GeoMet/SWOB access and observed response structure with **bounded** requests, supplementing existing source research.
- Use the researched Vancouver-area initial bbox `-123.30,49.15,-122.85,49.35` (west,south,east,north), adjusting only on measured evidence and approved scope.
- Parse recent observations; preserve embedded coordinates, station ID, observed timestamps, measurement names, units and measurement windows.
- Group readings by station and choose the latest **valid** observation for relevant measurements, without merging incompatible observation times into a falsely coherent measurement snapshot.
- Do not require each realtime station to exist in a separate station catalogue.
- Select useful station evidence based on **distance, freshness, and field availability**; do not simply label the nearest station as the destination's exact weather.
- Use a source-specific validated cache (provisional 10–15 minutes), stale fallback, reasonable bounds, and independent status/error handling.
- Preserve missing values as unknown; 0 mm precipitation at one station is not evidence that the destination is dry.
- Retain sanitized fixtures and deterministic tests, including missing fields, station grouping, sparse coverage, and distant/stale readings.

**Boundary:** SWOB source and conservative observation selection only. No analysis API or UI integration; no station interpolation, neighborhood rain map, camera inference, or Phase 6D work. Do not broadly refactor the completed road-source adapters.

### Assignment 6D — Combined Weather API and Destination UI

- Add source-separated weather data to `POST /api/trips/analyze` using **additive typed response fields** and preserving existing route, Road Ahead and DriveBC response behavior.
- Fetch each weather source independently (and concurrently where safe); retain useful road evidence even when both weather sources fail, and weather evidence when a road source fails.
- Preserve source-specific freshness, stale, unavailable and partial coverage with clearly identified source datasets. Do not collapse station observations into OpenWeather forecasts.
- Show weather **for the selected Vancouver destination** in a dedicated panel or section; identify station measurements by station, observation age and distance rather than presenting them as direct destination measurements.
- Distinguish current structured conditions from forecast intervals and from physical measurements, with units and timestamp/relative-age clarity.
- Preserve manual Analyze Journey, exact selected route, async request identity and cancellation safeguards; prevent stale results from a prior journey being misrepresented for a newly selected destination.
- Add focused API and frontend tests; run backend/frontend regressions, a bounded live journey smoke, and human browser acceptance.

**Boundary:** No camera pipeline or AI vision; no final LLM journey briefing; no new route/weather map simulation; no automatic polling or recurring monitoring; no Transit mode; no wholesale frontend redesign. Keep the existing ~65/35 application shell.

Each assignment is a separately reviewed unit. Assignment boundaries should not create speculative abstractions or unnecessary infrastructure. Codex must stop after its authorized task.

---

## 3. Established Accepted Baseline

### 3.1 Application and driving journey

Preserve accepted Phases 0–3:

- FastAPI backend and React/Vite/TypeScript frontend; MapLibre/MapTiler dark basemap; desktop shell and existing `/api` proxy;
- geocoded canonical locations, broad Metro Vancouver origin support, **City of Vancouver-only** destination validation;
- ORS driving alternatives, explicit user candidate selection and original selected GeoJSON LineString geometry;
- manually initiated `POST /api/trips/analyze` with selected candidate identity, distance and duration;
- request cancellation/identity protections, result invalidation when journey selection changes;
- backend-held credentials; pytest/Ruff, frontend tests and production build.

The MVP supports **Drive mode only**. Do not introduce Transit, GTFS or travel-mode switching.

### 3.2 Accepted Phase 4 Road Ahead

- Two official municipal datasets: Current Road Closures and Projects Under Construction.
- Validated approximately 24-hour structured caches and separately cached selective official detail enrichment.
- Source-attributed `CityEvent` normalization with accepted geographic geometry; deterministic Shapely/pyproj EPSG:26910 matching, all direct overlaps, nearby supplemental logic.
- Existing municipal map layers, findings, detail links, source statuses and partial failure behavior.

### 3.3 Accepted Phase 5 DriveBC Open511

- `backend/app/drivebc_open511.py`: normalized regional ACTIVE events, observed source metadata and geometry, paginated acquisition, validated 600-second regional cache, stale fallback and provider attribution.
- `backend/app/drivebc_relevance.py`: deterministic route intersections and proximity, with Point evidence classified as proximity; 500 m LineString and 250 m Point nearby defaults, capped supplemental findings, all direct LineString intersections retained.
- `backend/app/analysis.py`: Road Ahead `findings`, separate route-relevant `drivebc_findings`, separate map-visible `regional_events`, source-scoped diagnostics and independent source statuses; deterministic multi-source summary and overall coverage.
- Source-specific frontend sections, regional Point/LineString map layers, bounded focus/selection and existing manual analysis workflow.

The user accepted Phase 5 following automated and manual browser checks. Do not reinterpret event proximity as traffic delay or merge Road Ahead and Open511 records geometrically.

### 3.4 Existing model/response contracts are authoritative

Inspect repository code before extending `JourneyAnalysis`, `SourceStatus` or the frontend normalizer. This plan names conceptual weather fields but does **not** authorize breaking existing schemas, renaming road findings, or bypassing the approved validation paths.

---

## 4. Weather Evidence Principles

### 4.1 Three distinct evidence categories

1. **Station measurement (SWOB):** an instrument-based reading at a physical station and observation time, potentially for a specified accumulation window.
2. **Structured current condition (OpenWeather):** coordinate-based provider condition estimates/classifications for a requested destination and timestamp; not a local weather-station measurement merely because the endpoint calls it current.
3. **Near-term forecast (OpenWeather):** predicted conditions for explicit future timestamps or intervals; not a present observation.

Later camera AI observations form a **fourth, visual category**. Do not produce that category in Phase 6.

### 4.2 Missing, zero, stale and uncertain are different

- `None` / missing precipitation is **unknown**, not 0 mm.
- A 0 mm observed accumulation refers only to the given station and its measurement window.
- An OpenWeather condition code may be a provider classification, not a direct report of precipitation visibly falling at the destination.
- A broad 3-hour forecast must not be turned into minute-by-minute predictions.
- A nearby station can be distant enough that measurements do not represent the destination.
- Old observations and cached data retain their age and stale state; validity does not make them fresh.
- Contradictory sources must remain separately attributable, rather than being merged into a false consensus.

### 4.3 Destination-focused MVP

Use the canonical selected Vancouver destination as the primary weather target. The MVP needs **current and near-term conditions where the user is going**, not route-wide weather interpolation or an invented driving-weather risk score. A user-entered ETA is not required.

A later Phase 9/10 may consider time-alignment and synthesis using available actual timestamps, but Phase 6 must preserve uncertainty and avoid claiming that a particular forecast interval exactly predicts the user's arrival.

---

## 5. Assignment 6A — OpenWeather Source Evidence Gate

### 5.1 Before making provider calls

Review official endpoint/product documentation and existing Phase 0 notes. Check for local credential presence without printing it. Separate **API-key validity** from **product entitlement**: authorization to call one OpenWeather product does not establish access to another.

### 5.2 Bounded live checks

- Use an approved, representative City of Vancouver location.
- Verify documented authentication parameters, units and HTTPS method for likely current/forecast products.
- Capture the actual accessible product(s), HTTP status, request restrictions and observed returned keys.
- Where a product returns 401/403/429 or another failure, record it once and do not brute-force retries or subscription bypasses.
- Do not assume One Call 3.0, One Call 4.0, 5 Day / 3 Hour Forecast, or Current Weather endpoints are enabled or return particular fields. Confirm each product before using it.
- Avoid leaking secrets in exception messages, raw request logs, saved JSON, or report URLs.

### 5.3 Evidence deliverables

- Concise `docs/integration-notes/` report separating *documented*, *live confirmed*, *not accessible*, and *not yet verified*.
- Small, sanitized `fixtures/openweather/` files preserving schema variations, units and timestamps where permitted.
- A recommended minimum endpoint strategy for current conditions and near-term forecasts, with explicit limitations if forecast granularity is coarser than desired.
- A recommended provisional cache and coordinate key policy, with source/provider usage considerations.
- Model and adapter design recommendations to review **before Assignment 6B**.

**Decision gate:** 6A completes only after human review of the evidence and approval of the product and schema contracts. No production weather code is authorized by completion of 6A alone.

---

## 6. OpenWeather Adapter Contract — Assignment 6B

### 6.1 Normalize only verified fields

Use a small RouteLens-owned representation for actual supported data; likely categories include:

- target coordinate and provider/source identity;
- provider observation/current timestamp;
- current temperature and condition description/code where provided;
- wind, humidity, visibility and precipitation fields only where genuinely available;
- forecast interval timestamps, actual granularity, precipitation probability/amount where supported;
- provider retrieval time, cache freshness and attribution.

Units must be explicit and consistent. Retain provider-native fields only where they support provenance or a known useful distinction. Unknown and unavailable fields stay nullable.

### 6.2 Request and cache discipline

- Request weather for the selected destination with appropriately bounded geographic cache identity. Do not cross-serve distant coordinates as a supposedly exact destination reading.
- Make product-specific cache TTL decisions from 6A observations and documented refresh/update behavior. Do not lock a TTL before that evidence is reviewed.
- Validate the full intended response before atomic cache replacement; do not overwrite good cache with malformed or truncated data.
- Use bounded timeouts and limited retries; handle auth, quota, transport and malformed-response failures independently.
- Expose `SourceStatus` or equivalently compatible typed status, indicating available, fetched time, stale age and errors without credentials.
- Reuse valid cache on repeated analysis and use valid stale cache transparently after failed refresh where allowed.

### 6.3 Test requirements

Cover valid current and forecast examples, missing precipitation fields, malformed temperatures/time data, invalid JSON, product access failure, forecast horizon limitations, unit conversions if used, fresh cache reuse, stale fallback, cache-key location separation and honest absence of usable data.

---

## 7. SWOB Adapter and Station Selection — Assignment 6C

### 7.1 Source boundary

Use ECCC GeoMet/SWOB observations. The approved initial Vancouver-area bbox is:

`-123.30,49.15,-122.85,49.35` (west,south,east,north).

SWOB coverage is sparse. One station is not automatically representative of an entire neighborhood; missing catalogue records must not erase valid realtime measurements with embedded coordinates.

### 7.2 Validation and normalization

- Make bounded, non-repetitive live checks; inspect actual field/units/time semantics rather than assuming all stations emit the same measurements.
- Preserve source station ID, source geometry, observation datetime, per-field available data, measurement times/windows, and retrieval provenance.
- Group by station and select latest valid readings conservatively. Do not mix an outdated measurement into a newer station record without timestamp attribution.
- Reject invalid values/timestamps and note normalization losses rather than inventing replacements.
- Consider temperature, precipitation, wind, visibility and snow fields only where supported by actual source data.

### 7.3 Station evidence selection

Choose useful readings according to:

1. availability of the field relevant to the user;
2. actual observation freshness;
3. distance between station and destination;
4. geographic limitations and source coverage.

No neighborhood rain prediction, geographic interpolation, broad station heatmap, or assertion that the nearest station's weather is identical to the destination. If no useful recent station exists, state that measured evidence is unavailable rather than showing a misleading zero.

### 7.4 Cache and failure

Use provisional **10–15-minute** SWOB refresh caching; select one documented default based on observations in 6C. Preserve the last valid cache if replacement fails, surface stale status and age, and avoid refetching the entire feed for every UI event.

### 7.5 Tests

Cover heterogeneous stations, missing/invalid coordinates, missing station catalogue entries, multiple observation timestamps, field-availability ranking, distance/freshness boundaries, sparse or empty data, zero-versus-missing precipitation, stale valid cache fallback and unavailable source status.

---

## 8. Weather Analysis API — Assignment 6D

### 8.1 API strategy

Extend the accepted `POST /api/trips/analyze` additively. Preserve:

- exact origin, Vancouver destination, `mode="drive"`, explicitly selected route and existing request validation;
- Road Ahead `findings` and enrichment;
- DriveBC `drivebc_findings`, `regional_events` and event evidence classifications;
- source-scoped diagnostics and existing API error semantics;
- the three existing road dataset statuses and existing source success/stale reporting.

Weather models should be distinct from `CityEvent`, which is intended for road events. Add typed weather response containers that retain **measured station observations**, **OpenWeather current conditions**, and **OpenWeather forecast intervals** as separate evidence.

### 8.2 Overall availability and summaries

Define and test consistent status semantics when adding weather datasets to an analysis that already has three road datasets. A missing weather source should not erase road findings. Conversely, a failed road source should not erase available weather evidence.

Choose an additive source-status shape that preserves compatibility. Do not silently reinterpret an old road-only summary as complete road-and-weather intelligence. The original deterministic road summary may remain specifically road-focused, supplemented by clearly labeled weather evidence, or it may be explicitly expanded with correct source-group distinctions; document the choice and update frontend labeling accordingly.

A valid zero finding from a source is not an outage; unavailable weather evidence is not proof of fair weather. Stale valid weather may remain usable with accurate age/status.

### 8.3 Weather-oriented frontend

- Weather is **destination context**, not another road-event list.
- Show a structured OpenWeather current-condition card and an appropriately sized near-term forecast representation reflecting **actual** time intervals.
- Separately show selected SWOB measurement(s) with station identity, station-to-destination distance, measurement window and observation age.
- Clearly distinguish forecast from measured evidence and avoid spurious precision.
- Show source status, stale availability and unavailable coverage without drowning the existing road findings.
- Preserve the dark desktop layout, selected ORS route and municipal/regional map overlays.
- No camera images, computer-vision-derived conditions or AI narrative in 6D.

### 8.4 Backend/frontend test matrix

- Both weather sources available; one unavailable; both unavailable; one or both stale.
- Road sources available with weather unavailable and vice versa.
- No recent useful SWOB station; OpenWeather forecast absent/coarse; valid zero precipitation vs unknown.
- Different Vancouver destinations must not reuse mismatched cached weather as if exact.
- Original route request, invalid destination rejection and stale response invalidation still work.
- Weather source statuses remain separate; event/source counts don't conflate weather with road findings.
- Frontend source labels, units, time formatting and empty/error states remain accurate.
- Full existing Road Ahead/Open511 regression and frontend builds pass.

---

## 9. Provenance, Licensing and Security

- Respect `docs/data-licensing-and-commercialization.md`, provider terms and attribution requirements before saving fixtures or displaying source content.
- Keep `OPENWEATHER_API_KEY` backend-side and outside Git; never report full authenticated URLs or exception text containing API keys.
- ECCC station measurements, OpenWeather current conditions, forecast data and future camera observations are **not interchangeable** evidence.
- Preserve observation time versus fetch time versus forecast-valid time; cache age is not measurement age.
- Preserve station-specific spatial specificity; do not label sparse SWOB evidence as a verified destination condition.
- Use sanitization/validation for weather descriptions; avoid raw HTML and secret leakage.
- Any source with insufficient data must report unknown or unavailable rather than a made-up normal condition.

---

## 10. Phase 6 Non-Goals

Phase 6 does **not** authorize:

- camera catalogue enrichment, image retrieval, camera AI assessment or any Phase 7–8 work;
- OpenRouter vision/text inference, final AI briefing or Phase 10 work;
- Transit mode, GTFS Static or GTFS-Realtime integrations;
- precise rain onset inference from unverified forecast granularity;
- weather radar, numerical modeling, neighborhood precipitation interpolation or a live citywide weather field;
- route-wide coordinate sampling grids or selected-route weather optimization;
- weather-driven travel delay, route recommendation or ETA adjustment;
- background monitoring, recurring weather polling, push notifications or scheduled tasks;
- user accounts, new deployment infrastructure or an unnecessary generalized weather framework;
- revisions to Road Ahead/DriveBC matching except narrow regression fixes;
- assumptions about paid OpenWeather products without verified access.

---

## 11. Verification Requirements

Every assignment must report **Passed / Failed / Not run** separately for fixture/offline, bounded live and browser verification.

### 6A — Research evidence

- OpenWeather credential available or accurately reported missing/disabled.
- Products/entitlements tested with bounded calls; live outcomes distinguished from documentation.
- Current fields, forecast granularity, units and timestamps documented with actual payload evidence.
- Sanitized JSON fixtures parse and contain no secrets.
- Recommended product choice and cache approach documented without production changes.
- `git diff --check` and changed-file/credential hygiene inspection pass.

### 6B — OpenWeather adapter

- Exact approved product(s) only; normalizer tested on observed fixtures.
- Nullable fields, forecast intervals, units, partial or absent products represented correctly.
- Fresh cache, stale fallback, invalid/partial responses and source errors tested.
- Coordinate cache identity and safe exception/reporting boundaries tested.
- Focused pytest and Ruff pass; no unrelated frontend requirements.

### 6C — ECCC SWOB

- Observed source semantics, stations, times and available measurements verified with bounded live samples.
- Grouping and station selection verified across multiple station records.
- Sparse data, missing values and distinct accumulation windows remain accurate.
- Cache freshness/stale fallback and expected failures tested.
- Backend regression suite and Ruff pass.

### 6D — Integration and human review

- `POST /api/trips/analyze` request remains unchanged and road evidence preserved.
- Weather typed response fields and source statuses remain accurate under partial failures.
- Destination weather UI distinguishes measured, current-structured and forecast evidence.
- Road Ahead/DriveBC map and panel behavior remains intact.
- Selected route changes correctly invalidate prior weather analysis.
- Backend pytest, Ruff, frontend tests, TypeScript/production build pass.
- Representative live Vancouver destination verification and browser visual acceptance completed or limitations reported.

### General hygiene

Run applicable `git diff --check`, status/scope inspection, `.env` ignore checks, secret scanning, cache/fixture hygiene and source contract tests. Do not require browser verification in backend-only or research-only assignments. Treat a passing build as distinct from human visual acceptance.

---

## 12. Phase 6 Human Acceptance Criteria

Phase 6 is eligible for human acceptance only when:

- [ ] OpenWeather access and chosen API product(s) are grounded in real validation evidence.
- [ ] Any forecast limitations, granularity and available fields are accurately documented.
- [ ] Sanitized provider-derived fixtures and repeatable offline tests exist.
- [ ] OpenWeather current conditions and forecast use source-grounded schemas and units.
- [ ] OpenWeather source status and validated caching behave correctly.
- [ ] SWOB realtime station readings retain station identity, coordinates and observation time.
- [ ] Useful SWOB selection considers availability, freshness and proximity.
- [ ] Missing/zero precipitation and temporal measurement windows are treated conservatively.
- [ ] SWOB cache and stale fallback have verified behavior.
- [ ] Distinct measured/current/forecast evidence is retained in the combined response.
- [ ] Weather failures do not erase road findings; road failures do not erase weather evidence.
- [ ] Existing driving request, selected route, Road Ahead and Open511 behavior are preserved.
- [ ] Destination weather UI identifies source, age, units and data limitations.
- [ ] Stale, partial, unavailable and valid-empty cases are truthfully represented.
- [ ] Real destination weather verification and a meaningful human browser check are recorded.
- [ ] Backend/frontend regressions and appropriate lint/build checks pass.
- [ ] Credential secrecy, fixture hygiene, cache ignores, licensing and attribution are maintained.
- [ ] No camera, Transit, background polling or speculative LLM functionality is introduced.
- [ ] `PROJECT_STATE.md` reflects evidence, limitations and actual human review status.
- [ ] Codex completes the authorized assignment and does not alter Git history.

These are conditions for **human acceptance**, not automatic acceptance by Codex.

---

## 13. Blockers and Escalation

Stop the affected assignment and report if:

- the existing OpenWeather credential lacks the capabilities required by the proposed product and no approved accessible alternative is established;
- official endpoint licensing or product terms contradict the intended data use;
- API schemas, station units, timestamps, geographic coverage or observation cadence cannot be interpreted safely;
- a source's data cannot be represented without breaking accepted `JourneyAnalysis`/frontend contracts;
- independently failed weather providers cannot be represented honestly in source statuses;
- destination-based caching risks silently misattributing one location's measurements to another;
- the SWOB source is too sparse to support the intended UI claim;
- source quotas/rate limits prohibit proposed acquisition patterns;
- the requested functionality would require unauthorized camera/LLM or later-phase work;
- material architectural redesign or infrastructure expansion is needed.

For a blocker, provide: observed issue, affected requirement, evidence, feasible minimal alternatives, and any safe in-scope work completed. Routine normalization, tested cache policies, bounded fixtures and narrow response additions may proceed within the explicitly authorized assignment.

---

## 14. Phase Completion and Handoff

After each assignment:

1. Perform scope-appropriate verification and record outcomes separately for offline, live and browser work.
2. Update `PROJECT_STATE.md` with factual findings and test evidence **when authorized for that assignment**. For 6A, an evidence note and fixtures are the primary deliverables; the human will record the 6A checkpoint if the investigation prompt does not authorize modifying `PROJECT_STATE.md`.
3. Report files changed, provider behavior, known limits, deviations and blockers.
4. Stop for human review. Do not automatically begin the next assignment.
5. Leave Git staging, commits, pushes, merges, rebases, tags and history rewriting to the human developer.

After human Phase 6 acceptance:

1. Record human acceptance and evidence in `PROJECT_STATE.md`.
2. Create the human-controlled Git checkpoint.
3. Prepare and approve the next `BUILD_PLAN.md` for Phase 7.
4. Do not begin Phase 7 until separately authorized.

This build plan defines permitted scope and the planned assignment sequence. It does **not** authorize a blanket implementation of Phase 6.

---

## 15. Next Phase

**Phase 7 — Vancouver Camera Pipeline**

The approved roadmap next introduces the destination camera catalogue, directional image enrichment/retrieval, nearest usable intersection selection, and ephemeral image cache, followed by multimodal camera assessment in Phase 8. Phase 7 is out of scope for this build plan and requires separate authorization.

