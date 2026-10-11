# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 7 — Vancouver Camera Pipeline
**Phase status:** Planned; implementation requires separate, bounded authorization for each assignment. Assignment 7A is the first proposed validation task.
**Source:** `docs/implementation-plan.md`, Phase 7; `docs/prd.md`, destination-camera requirements; `docs/technical-design.md`, camera catalogue, selection and image-handling design; `docs/data-licensing-and-commercialization.md`, camera rights and retention policy.
**Previous phase:** Phase 6 — Current + Near-Term Weather, Assignments 6A–6D completed and human accepted on 2026-10-11. Phase 6 final Git checkpoint is human-controlled; verify current repository status before implementation.

### Objective

Add **real, current Vancouver traffic-camera views near the selected destination** to the accepted driving-only journey experience, without AI interpretation yet.

**Official camera metadata → validated directional-view catalogue → nearest usable destination intersection → current multi-view image retrieval → ephemeral cache → source-attributed destination-camera UI.**

The phase must deliver:

- evidence-backed discovery of the City of Vancouver camera metadata, intersection locations and supported source webpages;
- a **standalone, bounded catalogue-enrichment process** that discovers real directional image URLs rather than fabricating filenames;
- a validated, locally reusable enriched intersection catalogue, with a provisional approximately 24-hour refresh policy and last-good fallback;
- deterministic destination-based selection of **one nearest usable camera intersection**, with fallback to the next candidate when images are unavailable;
- retrieval of **all usable directional views from that one intersection**, allowing any supported number of views;
- short-lived, overwrite-in-place image storage, with **no historical archive or image time series**;
- safe backend delivery of current images and honest freshness, missing-view and source-failure states;
- an additive journey response / camera API contract and an integrated destination-camera frontend, preserving all road and weather behavior;
- offline and bounded live verification followed by human browser acceptance.

Phase 7 retrieves and presents source imagery. **It does not classify rain, traffic, road wetness, visibility or any other conditions using AI or heuristics.** Phase 8 will perform a single multi-view vision assessment of the selected intersection using OpenRouter. Phase 7 must preserve the image references and timestamps needed by that later work without implementing it.

### Locked product boundaries

- **Drive mode only.** City of Vancouver destination validation and explicit route selection remain authoritative.
- **One selected camera intersection per journey**, chosen for proximity and image usability; collect multiple directional views only from that intersection.
- **Destination context, not route-wide camera coverage.** No automatic corridor-wide image collection or browsing numerous intersections for analysis.
- **Current frames only.** Cache images briefly and overwrite/discard them; do not create an archive.
- **Evidence and licensing first.** Public accessibility does not itself grant redistribution, proxying or third-party AI-processing rights.

---

## 2. Execution Scope and Authorization

Phase 7 comprises four **separately authorized** Codex assignments. Completion of an assignment does not authorize the next. The human developer reviews results, authorizes the next bounded prompt and handles Git staging, commit and push.

### Assignment 7A — Camera Source and Rights Validation

- Inspect current official City of Vancouver camera dataset(s), their records, source pages, coordinates, unique IDs and observed direction/view conventions.
- Verify an actual, bounded sample of public intersection webpages and image requests; identify working directional-view discovery paths, redirects, content types and common failure cases.
- Review the approved licensing document and applicable official source terms. Distinguish **metadata licence** from **webpage/image usage rights**; record attribution and any unresolved restrictions on displaying, caching, proxying and later AI processing.
- Establish a realistic inventory/coverage estimate, representative edge cases and a practical catalogue-refresh approach.
- Save small sanitized metadata/HTML examples, documented source evidence and proposed parser fixtures where allowed. Do not bulk-download camera images merely to create test fixtures.
- Recommend a minimal, testable contract for enrichment and ephemeral retrieval, clearly flagging any rights or technical blockers.

**Boundary:** Investigation, fixtures and evidence notes only. No production catalogue builder, image API or UI. Phase 7B requires explicit human approval of discovery rules and a suitable MVP image-use posture. Do not assume that city open-data metadata licensing automatically covers the camera JPEGs.

### Assignment 7B — Enriched Camera Catalogue

- Build a **standalone, rerunnable enrichment script/service function** using verified official metadata and observed camera webpage markup.
- Retain stable intersection ID/name/location/page URL plus discovered directional view IDs, directions when reliably identified and validated image URLs.
- Detect, validate and record missing/duplicate/broken views without guessing filenames or directions.
- Persist a schema-validated enriched catalogue with an initial approximately 24-hour refresh TTL, atomic replacement and last-good fallback.
- Keep enrichment bounded: request timeouts, concurrency ceilings, retry limits, response-size limits and source-friendly pacing; do not trigger a full-city scrape per journey.
- Provide deterministic parser, malformed-page, partial-catalogue, and cache/fallback tests; perform only a bounded live sanity check.

**Boundary:** Catalogue production and persistence only. No destination selection, live per-journey image download, journey API integration, UI, or AI interpretation. A catalogue entry describes *discovered candidate views*, not a guarantee that its current JPEGs remain usable.

### Assignment 7C — Destination Selection, Image Retrieval and Backend Contract

- Select candidate intersections by geodesic/projected distance to the canonical Vancouver destination, using the validated enriched catalogue.
- Test actual image usability in nearest-first order with a strict candidate and request budget. When a nearer intersection has no usable view, try the next candidate.
- Select **the first intersection with at least one currently usable view**, then retrieve all usable directional images from **that same intersection**. Do not combine views from different intersections.
- Verify responses as actual bounded image payloads; reject nonimages, oversized payloads, invalid/unsafe URLs, failed redirects and corrupt images.
- Store only latest frames in an ephemeral/cache-only location, overwriting prior frames; expose validated backend image references with source/view and fetch times. No archive or per-refresh version history.
- Supply a small, typed backend destination-camera result and backend delivery endpoints, or a narrowly additive analysis contract, consistent with accepted routing/API patterns.
- Preserve independent cache/catalogue/image states and honest no-camera, degraded-view and stale/unavailable behavior.
- Add mocked/fixture-based selection, retrieval, security, cache and API tests.

**Boundary:** Backend only. No frontend or vision inference. If incorporating camera metadata into `POST /api/trips/analyze`, do so only additively; do not change selected-route identity, road/weather fields or existing source semantics. Do not fetch images on every page render without an explicit journey/user-driven request.

### Assignment 7D — Camera UI, Integration and Human Acceptance

- Integrate the camera result into the existing manually initiated Analyze Journey experience, or a clearly linked user-driven destination-camera load consistent with the approved backend contract.
- Display the chosen intersection, approximate destination distance, all usable directional views, source attribution, image retrieval time and any partial/stale status.
- Preserve the dark interface and ~65/35 desktop map/panel layout; place imagery naturally alongside destination weather rather than creating a new telemetry dashboard.
- Keep images tied to the current journey request identity. Clear old camera content when origin, destination or selected route changes; ignore late responses.
- Handle no usable intersection, missing individual views, stale catalogue, interrupted retrieval, and disabled/unavailable image use with accurate UI text.
- Add focused frontend tests and backend regression tests; verify a bounded live Vancouver journey and conduct human visual acceptance.

**Boundary:** No OpenRouter calls, vision/weather-from-image classification, historical imagery, traffic estimation, multi-intersection analysis, or Phase 8+ implementation.

**Assignment rule:** Each assignment is a bounded reviewed unit. Do not add speculative architectures merely because work is phased. Codex must stop after the authorized assignment and leave all Git history operations to the human developer.

## Assignment 7E — Nearby Camera Map Markers and Road Ahead Selection Reset

**Assignment status:** Authorized for implementation after human review of Assignment 7D. This assignment is a limited Phase 7 acceptance amendment.

### Objective

Complete two focused usability improvements before closing Phase 7:

1. Fix the existing Road Ahead map-highlight state so that selecting or resetting a journey cannot leave obsolete road segments highlighted.
2. Display up to four nearby Vancouver camera-intersection markers on the map after the user manually runs Analyze Journey.

### Scope

**Road Ahead state cleanup**

- Clear selected Road Ahead event and associated highlighted route geometry whenever the origin, canonical destination, route candidates, selected route, or journey-analysis context is invalidated.
- Ensure stale asynchronous results cannot restore an obsolete selection.
- Preserve normal route styling and other independent map layers.
- Add focused regression coverage.

**Nearby camera map markers**

- Reuse the accepted 7B normalized camera catalogue and its existing 24-hour cache.
- Return up to four nearest camera intersections to the canonical City of Vancouver destination, including the selected gallery intersection when it is within the approved nearby search radius.
- Use the established 2 km camera search radius unless the accepted application architecture requires a stricter bound.
- Show markers only after an explicit Analyze Journey action.
- Distinguish the selected gallery intersection from other nearby cameras through a modest visual treatment.
- Clicking a marker opens a small map popup containing the official intersection name and a link to its official City camera webpage.
- Additional markers are metadata-only: do not retrieve, cache, decode, or display their camera images.
- Marker presence must not imply confirmed image availability.
- Clear markers on journey-context invalidation and protect against stale responses.
- Preserve the existing single-intersection multi-view Destination Cameras gallery without an additional camera list.

### Design boundaries

- Maximum four map markers per analyzed destination.
- No citywide camera-marker layer, clustering, image previews, new source ingestion, automatic background polling, or extra frontend filters.
- No changes to accepted weather, routing, Road Ahead/DriveBC source ingestion, or Phase 8 AI vision behavior.
- Prefer a narrow, catalogue-backed metadata API or a backward-compatible response extension, whichever best preserves accepted backend contracts.
- Use established map-marker, popup, layering, styling, and source-attribution conventions.
- Preserve existing manual Analyze Journey behavior.

### Verification and human acceptance

Require focused backend/frontend tests as applicable, complete relevant regression checks, frontend TypeScript validation and production build, and repository hygiene checks.

Human acceptance requires:

1. Road Ahead highlighting resets correctly after origin, destination, or selected-route changes.
2. A normal analyzed journey displays no more than four nearby camera markers.
3. Marker popups show correct intersection names and working official-page links.
4. The gallery-selected camera is visually distinguishable when represented on the map.
5. Changing or clearing the journey removes obsolete camera markers and Road Ahead highlights.
6. Existing destination camera gallery, weather, road findings, and route interactions remain functional.
7. No unnecessary image retrieval or automated polling occurs for additional markers.

Assignment 7E is not accepted merely because automated tests pass. Human visual verification is required before Phase 7 is marked complete.

Do not begin Phase 8 during 7E.

---

## 3. Established Accepted Baseline

### 3.1 Driving journey and application

- FastAPI; React/Vite/TypeScript; MapLibre/MapTiler dark map; existing API proxy and desktop shell.
- Canonical geocoded origin/destination, destination **inside City of Vancouver**, ORS driving alternatives and **explicit selected-route choice**.
- Manual `POST /api/trips/analyze` with exact selected route and original GeoJSON geometry; cancellation/request identity and stale-result invalidation.
- Backend-held credentials, pytest/Ruff, frontend tests and TypeScript/production build.
- No Transit/GTFS/other travel modes, automatic rerouting or speculative ETA changes.

### 3.2 Phase 4 municipal road evidence

- Road Ahead closures and construction, ~24-hour validated source caching and selective detail enrichment.
- Conservative `CityEvent` models, metre-based route matching, preserved direct intersections, separately bounded nearby events, source statuses and existing map/panel rendering.

### 3.3 Phase 5 regional road evidence

- DriveBC Open511 active regional events, bounded pagination, normalized geometry, validated ~600-second cache and stale fallback.
- Separate route-relevant `drivebc_findings` and broad map-visible `regional_events`, with source attribution, conservative relevance/direction/schedule logic and no cross-source geometry deduplication.

### 3.4 Phase 6 destination weather evidence

- Accepted `backend/app/openweather.py` One Call 4.0 current plus 15-minute forecast; actual three-hour horizon, independent 600-second product caches and a persistent local 100-upstream-attempts-per-UTC-day guard. Human-set OpenWeather account limit: 500 calls/day.
- Accepted `backend/app/eccc_swob.py`: regionally fetched ECCC GeoMet station observations, per-station grouping, selected nearby useful measurements, 600-second cache, source time/freshness and coverage limitations.
- `destination_weather` is additive to the journey response and UI. OpenWeather current/forecast and SWOB measurements remain separately attributed; a station reading is not exact destination weather.
- Phase 6 passed backend/frontend regressions, bounded live journey verification and **all eight human browser acceptance checks** on 2026-10-11.

### 3.5 Accepted contracts are authoritative

Inspect repository code before extending `JourneyAnalysis`, weather/source statuses, frontend response normalization, cache paths or the request lifecycle. Do not rename or break existing road and weather fields. A camera result is **not** a `CityEvent` or a measured SWOB observation.

---

## 4. Camera Evidence, Rights and Provenance

### 4.1 Source and discovery evidence

The source of truth is the **official Vancouver camera metadata and currently observed camera webpages**. Camera image URLs must be discovered and verified, not inferred from station names, view numbers, or assumed filename patterns.

Preserve, when available:

- authoritative source record ID and intersection name;
- WGS84 coordinates and geometry accuracy/limitations;
- official camera webpage URL;
- each discovered view's stable identifier and reliable directional label;
- image endpoint/source reference and discovery/verification time;
- image retrieval timestamp, bytes/content type and availability status;
- source attribution and any limitations.

A webpage's compass label may describe the viewing direction or traffic approach; do not assert which without verified semantics.

### 4.2 Licensing decision gate

`docs/data-licensing-and-commercialization.md` treats Vancouver camera image handling more cautiously than the underlying public metadata. It accepts only an **ephemeral/cache-only MVP posture**, but explicitly warns this does not itself establish permission for image proxying, public display, redistribution or transfer to an external model provider.

Assignment 7A must independently examine current applicable terms and record:

- permissions and attribution for public catalogue metadata;
- what is and is not established for individual image/webpage content;
- constraints on automated retrieval, display through RouteLens and short-lived cache;
- any distinct restrictions on **Phase 8 third-party vision processing**.

Do not claim legal certainty from accessibility. If the intended use is plainly prohibited, stop and propose a permitted alternative. If rights remain unclear, present a bounded **local demonstration posture** and limitations for human review before 7B; do not silently characterize it as cleared for production/commercial use.

### 4.3 Ephemeral-only images

- Latest current frames only, in Git-ignored runtime cache.
- Overwrite earlier image bytes for each intersection/view rather than saving timestamped history.
- Bounded TTL and cleanup for obsolete images; choose values from observed image update behavior in 7C.
- No separate permanent thumbnail set, training corpus, persistent image collection or time-series.
- Raw images may later be provided to one explicitly authorized vision call in Phase 8, subject to the separate rights/security decision; Phase 7 does not make that call.

---

## 5. Assignment 7A — Evidence and Catalogue Design Gate

Research before writing a scraper or issuing extensive requests. Capture the **actual observed** catalogue schema and webpage layout, not a guessed URL algorithm.

A bounded representative sample should include, where available:

- one conventional intersection with several working directional views;
- a record with fewer, missing or broken views;
- representative naming, coordinate and URL variations;
- transient errors/redirects that affect retrieval;
- observed image format, dimensions/size and update cadence indicators.

Document the official dataset endpoint/query shape, record counts or pagination, link ownership, observed directional-view extraction selectors, and realistic total enrichment cost. Avoid scraping the full catalogue merely to answer feasibility questions.

**7A deliverables:** source evidence note, limited nonsecret examples/fixtures as permitted, verified discovery approach, provisional cache policy, rights assessment and a recommendation for 7B scope. Report unresolved uncertainty rather than inventing completion. No production code.

---

## 6. Assignment 7B — Catalogue Enrichment Contract

### 6.1 Catalogue entry

Use a small typed model with source-scoped identity, location, page URL, last discovery/check time and a bounded set of verified candidate view records. Preserve verified native view IDs/directions; nullable labels remain unknown.

### 6.2 Discovery process

- Acquire an authoritative, complete-enough official metadata snapshot with source-aware pagination and schema checks.
- Visit camera pages **only through controlled official URLs**, with bounded concurrency and user-agent/terms compliance.
- Extract actual image candidates from verified markup; support observed variability and graceful per-page failures.
- Validate URL destinations/protocol and required content shape. Avoid trusting arbitrary script or user-provided URLs.
- Record unavailable/failed enrichment per intersection without treating a partial catalogue as fully populated.
- Do not generate dozens of speculative URL guesses per record.

### 6.3 Catalogue cache

Choose a documented default around **24 hours**, with source/version/query identity, complete replacement validation, atomic activation, last-good stale fallback and clear partial/failed-refresh diagnostics. Refresh outside ordinary per-journey image lookups where feasible, without introducing an unnecessary polling service. Make initial bootstrapping/re-enrichment an explicit, rerunnable operation.

Avoid requiring SQLite/SQLAlchemy merely to store one locally validated catalogue JSON snapshot; introduce persistence infrastructure only if there is a concrete need.

---

## 7. Assignment 7C — Destination Selection and Retrieval

### 7.1 Candidate ordering and fallback

Using canonical Vancouver destination coordinates:

1. Load the current or valid stale enriched catalogue.
2. Exclude invalid locations and entries with no discoverable views.
3. Sort candidate intersections by actual metre-distance from destination with stable ID tie-breaking.
4. Test the nearest intersection's verified view URLs within a strict candidate count/time/network budget.
5. If **none** is usable, proceed to the next-nearest candidate.
6. Select the **first** intersection that has at least one usable current image.
7. Retrieve all other usable views from **that intersection alone**.

Do not pick a more distant intersection just because it has more available views once the nearest usable intersection meets the minimum one-view rule. No multi-intersection stitching or comparison.

### 7.2 Image validation and security

Only accept validated HTTP(S) targets from the approved discovery trust boundary. Enforce host allowlists based on **real** observed official image-serving hosts (including documented CDN hosts if needed). Check every redirect target. Block loopback, private/link-local, metadata-service and otherwise unsafe destinations; never proxy an arbitrary caller-supplied URL.

Bound timeouts, redirects, payload bytes, supported types, image dimensions and requests per journey. Confirm image magic/decoder compatibility rather than trusting a `.jpg` extension or response header alone. Never execute webpage scripts or render untrusted HTML on the backend.

Image fetches may fail independently: keep good directional views, label omitted/broken views accurately and avoid swapping in images from another intersection. No fabricated images.

### 7.3 Cache and delivery

Use a short-lived overwrite-in-place frame cache, keyed by verified intersection/view identity (not by uncontrolled URL strings). Persist only latest bytes and minimal metadata; avoid URL/query secrets in paths. Validate cache before reuse, keep honest fetch timestamps, and invalidate bad content. Do not create dated versions. Serve images via small backend routes using stable validated IDs and correct content type, cache headers and source attribution as permitted by 7A.

When no usable intersection exists, return an explicit unavailable/no-image result and retain functioning journey, road and weather data. Catalogue staleness and image age are separate.

### 7.4 API and request lifecycle

Prefer a narrow typed `destination_camera` result or a camera-specific backend API tied to the validated journey destination. Maintain manual Analyze Journey semantics. Where retrieval latency is significant, an explicit user-driven image load after analysis may be acceptable if the UI and response identity rules are coherent; do not silently start image polling on mount.

Do not make image delivery contingent on LLM/vision analysis. Keep camera metadata, view IDs, timestamps and image references ready for Phase 8's separately approved inference step.

---

## 8. Assignment 7D — Frontend Camera Presentation

### 8.1 Placement and content

Add a distinct but visually cohesive **Destination Camera** section near destination weather. Show:

- selected intersection and approximate distance from the destination;
- all available directional image views at that intersection;
- direction/view labels only where supported;
- capture time if supplied by the camera source; otherwise **retrieved at** time rather than invented capture time;
- official attribution and optional safe link to the source page;
- catalogue/image freshness, unavailable views and degraded-source states.

Use responsive layouts for one, two, three or more views; preserve image aspect ratio. Keep the selected driving route, map and road/weather panels usable. Do not add weather verdicts or AI confidence labels.

### 8.2 Trigger and invalidation

Camera loading must use an explicit, valid canonical destination and belong to the current manual journey-analysis lifecycle. Changing selected route or journey location invalidates old camera results, and late responses cannot repopulate them. Do not fetch the full camera catalogue from the browser or expose unsafe upstream URLs. No automatic image refresh loop or history slider.

### 8.3 Degradation

Communicate no nearby usable camera, a failed retrieval, partial directional availability, old cached imagery and stale catalogue as different conditions where the backend supports that distinction. Do not show old frames with a misleading “Live” label.

---

## 9. Validation and Test Requirements

Each assignment must report **Passed / Failed / Not run** for offline tests, live source access and browser verification independently.

### 7A — source evidence

- Official catalogue identity, schema and location fields supported by actual evidence.
- Verified representative camera pages and real image host/path patterns.
- Missing/broken/directional variants recorded.
- Catalogue metadata licence and separate image rights/attribution evaluated; unresolved items explicit.
- Representative limited fixtures sanitized, current and reasonably attributable.
- No unapproved full-city image crawl or production code changes.

### 7B — catalogue enrichment

- Source snapshot completeness, deduplication and malformed-record handling.
- Real markup extraction for multiple view counts and missing/changed layout.
- No guessed filenames/direction semantics.
- URL trust policy and bounded scraping/retries.
- Partial page failures, schema drift, catalogue cache corruption and stale fallback tested.
- Standalone rerun and output validation work without backend/UI coupling.

### 7C — image selection and backend

- Nearest usable intersection selected by real distance; unavailable nearest falls back correctly.
- At least one image required; all usable views retained from **one** chosen intersection.
- No mixing camera intersections.
- Content type, magic/image decode, size, dimension, redirect and host restrictions tested.
- SSRF/unsafe URL inputs blocked.
- Ephemeral overwrite/no-history, fresh image reuse, damaged cache and source failure tested.
- Honest returned source, image ages, status and API response validation.
- Existing weather/road API tests pass; image endpoints cannot reveal filesystem paths or arbitrary URLs.

### 7D — integration/browser

- Camera section shows actual current image(s) and supported source labels.
- Individual broken views do not blank otherwise usable views.
- Different view counts render without overlap/clipping.
- Distance, capture/retrieval time and stale states are truthful.
- No camera appears before authorized manual journey action.
- Journey changes and late responses cannot restore old destination frames.
- Existing road findings, OpenWeather/SWOB, selected route and map overlays survive.
- Backend pytest/Ruff, frontend tests/build and bounded live browser review complete.

### General hygiene

Check Git status/diff scope, `git diff --check`, `.env` and image-cache ignores, credentials in URL/log outputs, source fixture rights, test artifact cleanup and absence of committed runtime camera frames. Headless screenshot rendering is not equivalent to interactive human visual acceptance.

---

## 10. Phase 7 Non-Goals

Phase 7 does **not** authorize:

- OpenRouter API calls or any vision model processing (Phase 8);
- precipitation, wet-road, traffic, congestion or visibility conclusions drawn from camera pixels;
- analysis across multiple camera intersections or route-wide camera sampling;
- frame history, archival snapshots, timelapse, background surveillance or model-training datasets;
- camera imagery stored permanently in Git, databases or object storage;
- traffic count/speed/delay estimation, rerouting or weather-driven ETA calculations;
- DriveBC highway/bridge camera integration;
- automatic polling, WebSockets, jobs/queues or a periodic image-harvesting service;
- transit mode, GTFS, user accounts, saved journeys or a broad UI redesign;
- speculative image filenames, unverifiable source attribution or license certainty;
- final AI journey briefing, overall timeline synthesis or Phase 9–12 work.

---

## 11. Phase 7 Human Acceptance Criteria

Phase 7 is eligible for human acceptance only when:

- [ ] Official Vancouver camera metadata and actual webpages have been verified.
- [ ] Image/data terms and attribution have been reviewed, with unresolved image rights accurately recorded.
- [ ] Enrichment discovers genuine directional image URLs without guesses.
- [ ] An enriched catalogue with stable IDs, coordinates, source links, views and timestamps exists.
- [ ] Catalogue refresh/reuse, validation and last-good fallback are tested.
- [ ] Nearest-first selection chooses one usable destination intersection and falls back when needed.
- [ ] All usable views from the chosen intersection are retrieved; no multi-intersection mixing.
- [ ] No-image and broken-view cases are represented accurately.
- [ ] Image delivery enforces a verified trust boundary and bounded downloads.
- [ ] Ephemeral image cache reuses/overwrites current frames; no archive/history is produced.
- [ ] Camera image age is distinct from discovery age and any actual provider capture time.
- [ ] Journey request identity and selected-route behavior remain intact.
- [ ] Existing Road Ahead, DriveBC, OpenWeather and SWOB features remain functional.
- [ ] Destination Camera UI displays available views, source, distance and time clearly.
- [ ] Partial/stale/unavailable states are accurate and legible.
- [ ] Fixture-backed tests, backend/frontend regression, lint and production build pass.
- [ ] Bounded live Vancouver camera/journey checks and meaningful human browser acceptance are recorded.
- [ ] Credentials, URLs, generated images and caches are handled safely and are not committed inadvertently.
- [ ] No vision inference, historical archive, Transit or later-phase work is introduced.
- [ ] `PROJECT_STATE.md` records implementation evidence, limitations and actual human acceptance.
- [ ] Codex reports accurately and leaves all Git history actions to the human developer.

These are eligibility conditions, **not automatic acceptance by Codex**.

---

## 12. Blockers and Escalation

Stop the affected assignment and report evidence if:

- official camera metadata or webpages cannot reliably establish intersection/view identities;
- image host/path patterns require guesswork, unsafe unrestricted proxying or unbounded scraping;
- source terms clearly prohibit intended retrieval/display, or unresolved rights need explicit approval to proceed with even a bounded demo;
- a material source change makes full catalogue enrichment or current-frame retrieval infeasible;
- camera metadata coordinates are unreliable enough to break nearest-first selection;
- images cannot be served with an acceptable ephemeral/no-archive posture;
- selected-camera integration requires breaking established road/weather models or request-identity protections;
- an unapproved third-party service, subscription or broad architecture change is necessary;
- carrying out the assignment would require Phase 8 vision, background collection or other out-of-scope work.

For blockers, provide the observed issue, requirement affected, source evidence, minimal alternatives and completed in-scope work. Routine schema mapping, defensive URL validation, controlled parser updates, cache policies, test fixture refinements and small UI adjustments may proceed autonomously within the approved assignment.

---

## 13. Phase Completion and Handoff

After each assignment:

1. Run proportionate offline, live and (where relevant) browser verification, reporting outcomes separately.
2. Update `PROJECT_STATE.md` with factual changes, tests, source evidence and limitations **when that assignment authorizes it**. In 7A, the source-evidence note is primary and the human may record acceptance separately.
3. List changed files, verification commands/results, source behavior, deviations and any remaining blockers.
4. Stop for human review. Do not begin the next assignment automatically.
5. Leave Git staging, commits, pushes, merges, rebases, tags and history rewriting to the human developer.

After human Phase 7 acceptance:

1. Record acceptance and human browser evidence in `PROJECT_STATE.md`.
2. Create the human-controlled Git checkpoint.
3. Prepare/approve the next `BUILD_PLAN.md` for Phase 8.
4. Do not begin Phase 8 until separately authorized.

This build plan governs allowable implementation scope; it does **not** authorize a blanket execution of all of Phase 7.

---

## 14. Next Phase

**Phase 8 — Multi-View Camera AI Analysis**

Phase 8 will apply one controlled multimodal assessment to the selected intersection's currently available directional views, producing structured, source-attributed `CameraObservation` evidence. It requires separate authorization and an explicit review of any remaining camera-image rights/security boundaries before sending images to OpenRouter. Phase 8 is outside this build plan.

