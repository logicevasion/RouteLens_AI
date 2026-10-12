# Phase 9A — Journey Evidence Inventory and Contract Design

**Status:** Accepted Assignment 9A contract baseline. Assignment 9A was human accepted; its follow-on 9B implementation is summarized in Section 9.
**Basis:** Repository source inspected on 2026-10-11, accepted Phase 4–8 notes, current `BUILD_PLAN.md`, and the Phase 9/10 sections of `docs/implementation-plan.md`, `docs/prd.md`, and `docs/technical-design.md`.

## 1. Evidence-source inventory

| Evidence | Producer and existing contract | Meaning, provenance, and time | Empty/failure distinction and reusable work |
|---|---|---|---|
| Canonical trip and selected route | `backend/app/analysis.py`: `Trip`, `SelectedRoute`; built by `frontend/src/roadAhead.ts:buildAnalysisRequest` from the explicit selected candidate. `POST /api/trips/analyze` echoes the validated `trip` in `JourneyAnalysis`. | Origin/destination are `Location` (`frontend/src/locationTypes.ts`). Route identity is `selected_route.candidate_id`; exact GeoJSON LineString, distance, duration, and optional label are carried. `JourneyAnalysis.analyzed_at` is analysis evaluation time, not departure time. | Route selection is explicit; frontend guards candidate ID and request identity. No route should be recomputed or selected by the assembler. `Trip` validation already bounds geometry and destination. |
| Road Ahead | `backend/app/analysis.py:analyze_journey`; `backend/app/route_relevance.py:match_route_events`; original records from `backend/app/road_ahead.py`. Response: `JourneyAnalysis.findings: AnalysisFinding[]` with `CityEvent`, `direct_overlap|nearby`, route distance, and `DetailEnrichment`. | Authoritative record identity is `event.source_dataset_id` + `event.source_record_id` (and source-scoped event ID); source, attribution, geometry/coordinates, severity/status, schedule/restriction, `observed_at`, `updated_at`, URL, metadata, and relevance reason stay in `CityEvent`. Detail fetch time and stale/cache state are separate in `finding.detail`. | `source_statuses` has one `SourceStatus` per dataset with `success`, `available`, fetch/cache/stale fields and record counts. Empty `findings` with available statuses means no route-relevant match was identified; it is not a clear-road assertion. `unmatchable_events` records matcher limitations. Reuse accepted classification and distance; do not rematch. |
| DriveBC Open511 | `backend/app/analysis.py:analyze_journey`; `backend/app/drivebc_relevance.py:match_drivebc_events`; source adapter `backend/app/drivebc_open511.py`. Response: `drivebc_findings: DriveBCAnalysisFinding[]`, plus a separate regional map-only `regional_events[]`. | Finding includes original event/geometry and source-scoped IDs, `direct_overlap|nearby`, `distance_meters`, `geometry_basis` (`linestring_intersection`, `linestring_proximity`, `point_proximity`), and source evidence (event type/status/severity/subtypes/roads/schedule). Direction is `undetermined`, temporal applicability `unknown`, current impact `not_established`. Event `observed_at` is source creation time when present, not necessarily when active. | One Open511 `SourceStatus`; failed fetch yields empty events plus `success=false, available=false`. Available status plus no route findings is successful no-match, not proof of route clearance. Regional events must stay out of briefing evidence. Reuse the accepted matcher output and uncertainty fields. |
| OpenWeather destination current | Acquired by `_destination_openweather` in `backend/app/analysis.py`, adapter `backend/app/openweather.py`; response `destination_weather.openweather_current: CurrentWeatherResult`. | `weather` has source/product, requested and provider coordinates, `observed_at`, `fetched_at`, metric values, and condition. This is provider current-condition evidence at the canonical destination coordinates. Keep null measurements null. | `status` carries `success`, `available`, `fetched_at`, cache/stale metadata, and error. A successful available result with `weather=null` differs from failed/unavailable. Current source status is independent of forecast. |
| OpenWeather forecast | Same acquisition boundary; `openweather_forecast: ForecastWeatherResult`. | `intervals[]` each has source/product, `forecast_at`, `fetched_at`, values and condition; `coverage` has evaluation/window bounds, interval counts, missing/malformed/duplicate diagnostics and continuity. These are forecasts for target times, not observations or a journey timeline. | Own status, independent of current. Empty intervals plus unavailable status means failure; available status with empty/partial intervals preserves the adapter's coverage semantics. Reuse supplied intervals and coverage; no invented arrival/departure alignment. |
| ECCC GeoMet/SWOB | `_destination_swob` in `backend/app/analysis.py` calls `fetch_regional_observations` and `select_for_destination`; adapter/models in `backend/app/eccc_swob.py`. Response carries `eccc_status`, up to three `SelectedStationObservation`s and attribution. | Backend `StationObservation` preserves station ID/name, `station_identifiers`, `source_record_id`, station position, measurements with original field/unit/interval/quality code, `observed_at`, and `retrieved_at`. Selected wrapper adds destination distance, observation age/staleness, cache staleness, useful measurements, and selection reason. It is station evidence, not destination measurement. | `SwobSourceStatus` distinguishes success/availability and cache/fetch state. Successful retrieval with zero selected observations differs from failure. Each station may also have no useful measurement; do not turn that into zero. Reuse deterministic latest-per-station selection and destination-distance calculation. Current `frontend/src/weather.ts:station` drops `station_identifiers` and `source_record_id`; 9B must preserve them in the frontend type/normalizer if the proposed pure frontend bundle is to retain full observation identity. |
| Camera vision | `POST /api/cameras/observe` in `backend/app/routes.py` selects the destination intersection server-side and invokes `backend/app/openrouter_vision.py` (`AdapterResult`). `frontend/src/cameraVision.ts:normalizeCameraVisionResult/fetchCameraVision` validates the response. | `observation` carries model observation status/failure code, authoritative intersection ID/name/street names, distance to destination, camera source/attribution/page, included/excluded directional view provenance, model `views[]`, summary/evidence view IDs, requested model, actual provider/endpoint, `inferred_at`, and usage. Each included view has authoritative `view_id`, direction label, `retrieved_at`, nullable `source_capture_at`, digest/snapshot and image metadata. Retrieval is not capture time. | Backend adapter returns typed `available|partial|insufficient_evidence|unavailable|error` status and bounded failure code; HTTP/network/invalid-result frontend errors are converted to unavailable or invalid-output evidence. In `JourneyEvidenceState`, request lifecycle is `pending` then `complete`; a failed inference is a completed result with model status unavailable/error, not an indefinitely pending request. A stale request is rejected; journey invalidation clears it. |

## 2. Existing lifecycle and integration map

1. `App.tsx` owns the canonical origin/destination and explicit selected ORS route. `buildAnalysisRequest` packages these into the same `Trip` sent to both source operations.
2. On explicit Analyze Journey, the frontend increments request generations, stores a pending camera record with the trip and vision attempt ID, starts `POST /api/cameras/observe`, and independently starts `POST /api/trips/analyze`. Camera inference is deliberately not a gate for road/weather analysis.
3. `JourneyAnalysis` is normalized by `normalizeJourneyAnalysis` in `roadAhead.ts` and retained as `JourneyEvidenceState.analysis`. `normalizeCameraVisionResult` validates and stores the camera result in `.camera_vision.camera_vision.result`.
4. Input edits, Find Routes, and route changes call `invalidateAnalysis`, abort the requests, clear camera evidence and analysis, and advance identity generations. Both response paths check current request/attempt identity before retaining results.
5. The independent Phase 7 gallery (`cameraState`) is UI evidence and is not needed for the bundle; the 8D backend observation includes its own validated frame provenance. `regional_events` are map context, not route findings.

The current `JourneyEvidenceState` does **not** retain an explicit analysis attempt ID on the `analysis` branch. 9D should put one shared attempt identity on the state wrapper (or use the existing request key plus sequence in a small wrapper), and ensure it is the identity attached to camera evidence. Do not make the bundle infer identity from object position or route geometry alone.

## 3. Recommended assembly boundary

Use a **pure TypeScript function in the frontend** consuming already normalized `JourneyAnalysis` plus the matching `JourneyCameraEvidence` and explicit attempt identity.

This is the shortest path because all required road, weather, SWOB, trip and route fields are already in one validated analysis response; camera inference is already separately validated and retained in the same frontend-owned lifecycle. A backend assembler would need a new transfer/orchestration path to receive frontend camera results or would repeat source work, while a new endpoint would add lifecycle and API surface. No additional network calls are needed.

The trade-off is that the bundle remains an internal frontend handoff for Phase 10's eventual consumer. Keep the transformation pure and deterministic; Phase 10 can choose a server-side text-model boundary later without moving source acquisition into the assembler. Build only from normalized contracts, and reject mismatched trip/attempt identity.

## 4. Proposed `JourneyEvidenceBundle v1`

The compact v1 reuses source structures rather than translating them into generic evidence items. TypeScript shape (names are proposed; source subtypes reuse `analysisTypes.ts` and `cameraVision.ts`):

```ts
type EvidenceAvailability = 'available' | 'empty' | 'partial' | 'unavailable' | 'pending' | 'failed' | 'unknown';
type BundleReadiness = 'ready' | 'partial' | 'unavailable';

type JourneyEvidenceBundleV1 = {
  schema_version: 'journey-evidence-v1';
  assembled_at: string;                 // ISO UTC transformation time
  identity: {
    attempt_id: number;                 // explicit Analyze Journey generation
    trip: AnalysisRequest;              // canonical request, selected route included
    analyzed_at: string | null;         // JourneyAnalysis.analyzed_at; null if request failed
  };
  readiness: {
    status: BundleReadiness;
    ready_for_briefing: boolean;
  };
  sources: {
    road_ahead: {
      availability: EvidenceAvailability;
      statuses: SourceStatus[];          // preserve each dataset status verbatim
      findings: AnalysisFinding[];       // route-relevant only
      unmatchable_events: JourneyAnalysis['unmatchable_events'];
    };
    drivebc_open511: {
      availability: EvidenceAvailability;
      status: SourceStatus | null;
      findings: DriveBCAnalysisFinding[];
    };
    openweather_current: {
      availability: EvidenceAvailability;
      status: WeatherSourceStatus | null;
      weather: CurrentWeatherEvidence | null;
    };
    openweather_forecast: {
      availability: EvidenceAvailability;
      status: WeatherSourceStatus | null;
      intervals: ForecastInterval[];
      coverage: ForecastCoverage | null;
    };
    eccc_swob: {
      availability: EvidenceAvailability;
      status: WeatherSourceStatus | null;
      observations: SelectedStationObservation[]; // 9B adds source_record_id/station_identifiers to frontend normalized type
      attribution: string | null;
    };
    camera_vision: {
      availability: EvidenceAvailability; // pending is non-blocking
      result: CameraVisionResult | null;   // existing validated one-image result
    };
  };
};
```

For a failed `/api/trips/analyze` request, the input `Trip` and attempt remain known; `analyzed_at` is null, all analysis-produced source sections are `unknown` (the request failure is not a source-level report), and `readiness.status='unavailable'`, `ready_for_briefing=false`. For a successful response, copy source sections and their existing payloads/statuses; do not add a second representation of event evidence. Existing empty arrays and `available=false` status together distinguish a successful no-match from failure.

Do not include `regional_events`, raw provider payloads, raw HTML, image bytes/data URLs, full model responses, API credentials, or camera gallery state. Preserve route geometry only once in `identity.trip.selected_route`. The supported existing output bounds are inherited: at most three selected SWOB stations; one AI-analyzed camera frame under accepted 8D; the forecast adapter's returned bounded intervals; route-matched events from existing adapters. 9B must not silently truncate source arrays to meet a generic limit. If a new evidence-specific cap is required, retain all direct overlaps first, record an explicit `omitted_count` per section and reason, and confirm the cap in review; current inventory does not establish a need for an additional cap.

### Example (abbreviated)

```json
{
  "schema_version": "journey-evidence-v1",
  "assembled_at": "2026-10-11T20:00:00Z",
  "identity": {
    "attempt_id": 12,
    "trip": {"mode": "drive", "origin": {}, "destination": {}, "selected_route": {"candidate_id": "route-2", "geometry": {"type": "LineString", "coordinates": []}, "distance_meters": 9200, "duration_seconds": 1100, "label": null}},
    "analyzed_at": "2026-10-11T19:59:45Z"
  },
  "readiness": {"status": "partial", "ready_for_briefing": true},
  "sources": {
    "road_ahead": {"availability": "available", "statuses": [], "findings": [], "unmatchable_events": []},
    "drivebc_open511": {"availability": "failed", "status": {"success": false, "available": false}, "findings": []},
    "openweather_current": {"availability": "available", "status": {}, "weather": {"observed_at": "2026-10-11T19:45:00Z", "fetched_at": "2026-10-11T19:59:40Z"}},
    "openweather_forecast": {"availability": "available", "status": {}, "intervals": [], "coverage": {}},
    "eccc_swob": {"availability": "available", "status": {}, "observations": [], "attribution": "ECCC GeoMet/SWOB"},
    "camera_vision": {"availability": "pending", "result": null}
  }
}
```

The abbreviated objects above illustrate only bundle organization; implementations must use full existing source models and validate complete required fields.

## 5. Status, readiness, spatial relevance, and timestamps

- `available` means a usable source result exists; `empty` means successful retrieval but no relevant result/value was produced; `partial` means the source explicitly reports partial coverage/evidence; `unavailable` means the source result itself reports unavailable; `failed` means the operation failed before a valid source result; `pending` is an in-flight camera request; `unknown` means the analysis request failed before source outcomes were obtained. Preserve original statuses unchanged beside this summary.
- `empty` with an empty findings/observations/interval list means no relevant evidence was returned by that successful operation. It never means the route is clear. Do not define a separate positive “clear” state.
- Bundle readiness is about whether the bundle can be used, not whether every source succeeded: `ready` = successful analysis and all source states are available or successfully empty; `partial` = successful analysis with one or more partial, unavailable, failed, unknown or camera-pending sources; `unavailable` = no valid analysis result. `ready_for_briefing` is true for `ready` and `partial`, including while camera inference remains pending. Phase 10 must be able to proceed with the available bundle and must not wait indefinitely for camera completion.
- Use existing road classifications/distances as the route relevance. Weather/SWOB and camera are destination-context evidence; SWOB keeps station-to-destination distance. Do not imply route-wide coverage from destination data. DriveBC point proximity remains `point_proximity`, never route overlap.
- Keep distinct timestamps: `assembled_at`; `identity.analyzed_at`; Road Ahead event `observed_at`/`updated_at` and detail `retrieved_at`; Open511 source event timestamp/schedule as supplied; OpenWeather current `observed_at` and `fetched_at`; forecast `forecast_at` and `fetched_at` plus coverage window; SWOB `observed_at`, `retrieved_at`, observation age, and regional cache age; camera view `retrieved_at`, nullable `source_capture_at`, and model `inferred_at`. No timestamp should be renamed to “journey time.”
- `source_capture_at` is nullable and unverified if absent; never substitute camera retrieval or inference time. Preserve model `status`, `failure_code`, per-view uncertainty enums, and one-direction scope.

## 6. Minimal deterministic reconciliation policy

1. Copy Road Ahead `direct_overlap`/`nearby` and DriveBC classifications, distances, and geometry basis unchanged. Do not rerun intersection/proximity calculations or infer traffic delay.
2. Keep OpenWeather current and forecast in different fields and maintain each product's own status, timestamp, and cache metadata. Do not treat forecast probability as measured precipitation.
3. Keep each SWOB station as its own observation with station/source record identity, coordinates, values/units/quality/interval, observed and retrieved times, and distance/age/staleness. A missing measurement is unknown, not zero.
4. Keep camera output explicitly model-derived and attached to backend-selected intersection + directional `view_id`. One frame is a single view of the destination area. Do not turn wet-looking pavement into rain amount, an official closure, or route-wide congestion; do not merge it with weather as if both measured the same thing.
5. Preserve independent source outcomes. Do not infer agreement/conflict across sources unless a later narrowly justified rule has common subject, location and time; v1 adds no relationship graph or cross-source labels.
6. Do not invent segment ETAs, departure/arrival time, delay, future journey timeline, route scores, or omitted evidence. For any later bounded trimming, report what was omitted explicitly.

## 7. 9B–9D implementation handoff

### Assignment 9B — pure source assembly

- **Likely modules:** add `frontend/src/journeyEvidence.ts` with the v1 types and pure `assembleJourneyEvidence(...)`; import existing types from `analysisTypes.ts` and `cameraVision.ts`. Make a narrow provenance-preserving adjustment in `frontend/src/analysisTypes.ts` and `frontend/src/weather.ts` so normalized weather retains the existing coordinate context and rain/snow fields, and SWOB readings retain backend `source_record_id` and `station_identifiers`. No backend/API change. If `AnalysisState.error` is included, accept canonical `Trip` and attempt ID separately so a failed request can still produce an unavailable bundle.
- **Inputs/outputs:** canonical trip + attempt ID + normalized `JourneyAnalysis | null` + analysis request outcome + matching `JourneyCameraEvidence | null` → versioned typed bundle. Copy route findings, statuses, destination weather, SWOB, and camera result; omit regional map events.
- **Essential tests:** successful full result; successful zero-match vs failed source; independent current/forecast states; SWOB identity/timestamps retained; route classification and DriveBC geometry basis retained; camera pending and unavailable represented; mismatched trip/attempt rejected; no mutation of inputs.
- **Acceptance:** runtime validation/types match this note; no new network calls or provider parsing; no generic evidence graph; direct and nearby findings preserved.

### Assignment 9C — small reconciliation/readiness helpers

- **Likely modules:** extend `frontend/src/journeyEvidence.ts` with deterministic `deriveBundleReadiness` and only any narrowly approved freshness/relevance annotations. Keep the v1 source objects intact; avoid a second copied item schema.
- **Inputs/outputs:** assembled source statuses, trip identity, and camera pending/completed state → readiness/source annotations or the completed bundle. Timestamp grouping can remain source-native unless Phase 10 identifies a concrete need.
- **Essential tests:** readiness matrix across failed/empty/available/pending camera states; no camera wait; camera retrieval time never used as capture time; no cross-source agreement/conflict generated; no destination evidence labeled route-wide.
- **Acceptance:** deterministic, preserves all original classifications/statuses/times, does not add unsupported conclusions or a relationship graph.

### Assignment 9D — lifecycle attachment and handoff

- **Likely modules:** `frontend/src/App.tsx` and `frontend/src/cameraVision.ts` (or a narrow state helper) attach the bundle to the existing evidence state and shared active attempt identity; `frontend/src/journeyEvidence.ts` remains the pure assembler. Do not add endpoints or change the camera contract.
- **Inputs/outputs:** each accepted analysis completion/failure and camera pending/completion update for the active trip/attempt → current internal bundle; stale or superseded results cannot replace it.
- **Essential tests:** same attempt with analysis first/camera pending, camera first/analysis pending, camera failure, late previous attempt, trip or route change invalidation, analysis failure, retained camera result only for matching trip. Existing source-fetch tests stay mocked/offline.
- **Acceptance:** one current bundle per active Analyze Journey attempt; analysis is not gated on vision; failure remains source-specific; no stale bundle survives trip/route invalidation; Phase 10 can read the stable typed contract.

9B and 9C can share this small pure module: 9B defines and assembles the source sections; 9C adds only tested readiness/relevance rules on the same typed values. 9D is genuinely dependent on the final 9B/9C function signature, but lifecycle integration can be prepared in parallel only after the v1 schema is human-approved. This was the proposed handoff at the end of 9A; completed 9B work is summarized in Section 9, and 9C/9D remain unstarted.

## 8. Discrepancies and unresolved decisions

- **Phase 9 scope drift:** `docs/implementation-plan.md` Phase 9 describes backend combining, a normalized timeline, `JourneyTimeline`, `JourneyStatus`, `AlongYourRoute`, `SourceFreshness`, and ranking. Current `BUILD_PLAN.md` locks Phase 9 to an internal bundle/reconciliation and says existing UI remains unchanged absent necessity. Assignment 9A is expressly a proposal in that build plan. Human approval should confirm whether visible timeline/ranking work is deferred; this note follows the current assignment's internal-bundle boundary and does not edit the authoritative plan.
- **Evidence contract age:** `docs/technical-design.md` contains conceptual `JourneyAnalysis` examples with camera/weather fields integrated into one backend response. Actual implementation uses separate `JourneyAnalysis` and `/api/cameras/observe` operations plus frontend-owned `JourneyEvidenceState`. This proposal follows actual implementation and does not rewrite accepted source APIs.
- **Camera schema capability:** Current 8D accepted policy analyzes exactly one selected directional image, and accepted real-camera checks used one image. `camera-observation-v1` and TS types remain multi-view capable (`included_views[]`, `views[]`). For v1 consume the complete validated result unchanged; current accepted output will have one included view and corresponding observation. The bundle should not add a second camera schema or silently pick an item if a future result has multiple views.
- **Attempt identity:** The current `analysis` state does not expose an attempt ID, while camera evidence does. 9D must create one shared identity in its small lifecycle wrapper. This is a necessary integration detail, not a new provider/API contract.
- **Normalized SWOB identity:** Backend responses contain `source_record_id` and `station_identifiers`, but `weather.ts` currently removes them. The frontend boundary remains the smallest assembly location, with a small 9B normalization/type change required to retain these existing fields; it does not require a new source request or backend contract.
- **Weather normalization subset:** Backend OpenWeather models include requested/provider coordinates and precipitation amounts (and additional forecast wind/precipitation fields) that the current frontend weather types omit. Retain those already-produced values in the 9B frontend normalized types if they are to be available to the briefing; do not reconstruct them from raw provider responses.
- **Bounded omission:** Current inputs have explicit adapter bounds, but no contract-level omission counters for route findings or forecast intervals. Avoid a new arbitrary cap. If Phase 10 payload needs a tighter limit, human review should approve cap and omission metadata before implementation.
- **Readiness approval:** Proposed `ready_for_briefing` permits Phase 10 to proceed with partial source coverage and camera pending/unavailable. Human approval of this semantic is required before 9B/10 consume the field.

## 9. Assignment 9B implementation note

**Status:** Human accepted and complete. The three human-approved decisions are: (1) a frontend-owned pure TypeScript assembler consumes normalized journey analysis and validated camera-vision results; (2) readiness is partial-first, retaining usable evidence when another source is pending, failed, or unavailable; and (3) current `BUILD_PLAN.md` defines the MVP, with the older timeline/UI work deferred and Phase 10 owning the user-facing briefing.

`frontend/src/journeyEvidence.ts` exports `JourneyEvidenceBundle`, source-specific evidence section types, `EvidenceAvailability`, and deterministic `assembleJourneyEvidence(inputs)`. It preserves the canonical trip/selected route, explicit attempt and assembly identity, analysis outcome, Road Ahead findings/statuses/unmatchable records, DriveBC route findings/status, independent OpenWeather current and forecast sections, selected SWOB observations, and validated camera result/provenance. Regional map-only events and the analysis summary are omitted. Input trip and attempt identity are checked against successful analysis and supplied camera lifecycle evidence. Assembly time is supplied by the caller.

The bundle adds `identity.analysis_status` (`success | pending | failed | unknown`) to the proposed v1 identity so an analysis that has not completed cannot be confused with a successful empty result. Source sections retain `available | empty | partial | unavailable | pending | failed | unknown`; `insufficient_evidence` camera results are retained with source status `empty`, not positive visual evidence. A stale cached result following a failed refresh maps to `partial`, not `empty`. After successful analysis, `ready_for_briefing` is true even when other sections are partial or pending. Section 10 records the 9C refinement of aggregate readiness and retained error detail.

Frontend weather normalization now preserves existing OpenWeather requested/provider coordinates, current rain/snow amounts, and forecast wind and rain/snow fields. SWOB `source_record_id` and `station_identifiers` are preserved as optional fields for compatibility with older fixtures/responses. No backend model, endpoint, provider call, persistence, UI, or Analyze Journey integration changed. The assembler assumes validated normalized source inputs and does not introduce a generic payload cap or evidence graph.

Focused offline tests cover source distinctions, stale-cache outcomes, timestamps, SWOB provenance, one-direction camera provenance, pending/insufficient camera states, unknown/failed analysis, trip identity, immutability, deterministic output, and the additional weather/SWOB normalization fields. Assignment 9B is human accepted. Assignment 9C readiness refinement and verification are recorded in `PROJECT_STATE.md` Section 41; 9D lifecycle attachment remains unstarted.

The earlier readiness-approval question in Section 8 is resolved by the human-approved partial-first policy above. The timeline/UI scope difference is resolved for the MVP: it remains deferred, and Phase 10 owns the eventual briefing.

## 10. Assignment 9C readiness refinement

The 9C change remains a pure refinement in `frontend/src/journeyEvidence.ts`; source sections are not translated into a second evidence schema. `readiness.status` now distinguishes analysis `pending`, `failed`, and `unknown` directly, with `ready_for_briefing: false` for each. For successful analysis, readiness is `ready` only when all source sections are `available` or validly `empty`; otherwise it is `partial` with `ready_for_briefing: true`. This includes camera pending, provider timeout/error, unavailable or unknown camera coverage, and degraded other sources. A camera result with `insufficient_evidence` stays `empty`; its original observation status remains available in the result. The analysis request's error string is retained as `identity.analysis_error`.

No new relevance or freshness classification was needed. Existing route classifications, DriveBC geometry basis, source IDs/statuses, destination and station coordinates, SWOB station/distance/age metadata, and all source-native time fields already provide the required Phase 10 context. Camera intersection distance and the selected view's direction/view ID localize its interpretation; retrieval, nullable capture, and model inference times remain distinct. Current weather and forecast target intervals remain separate. No shared freshness threshold, arrival-time inference, positive weather/traffic inference, or cross-source relationship labels were introduced.

Regression tests cover successful all-source readiness, pending/failed/unknown analysis, partial readiness under camera pending/timeout/provider failure, `insufficient_evidence`, valid empty versus failed roads, stale cached data, OpenWeather current/forecast time separation, SWOB station provenance, single-direction camera localization and timestamps, conservative observation labels, determinism, and input immutability. Tests use synthetic local data only. 9D still owns active lifecycle attachment, shared attempt identity, and stale-result protection; Phase 10 remains unstarted.

## 11. Scope and deferred work

Sections 1–8 record the Assignment 9A evidence inventory, contract proposal, and handoff; they did not add production code, a new endpoint, persistence, provider calls, camera inference, briefing, timeline UI, source-relevance algorithms, a relationship graph, or dependencies. The contract and readiness/scope decisions were human approved before Assignment 9B. Section 9 records the bounded 9B implementation; Section 10 records the 9C readiness refinement; Section 12 records the 9D lifecycle attachment. Phase 10 briefing work remains deferred.

## 12. Assignment 9D — lifecycle attachment and Phase 10 handoff

**Status:** Implemented and pending human review. This note does not claim Phase 9 acceptance or completion.

**Internal access boundary:** `frontend/src/App.tsx` owns the memoized `journeyEvidenceBundle` value, derived by `deriveCurrentJourneyEvidence(...)` in `frontend/src/journeyEvidence.ts`. Its type is `JourneyEvidenceBundle | null`. Phase 10's internal consumer should read this one current-attempt value from App's existing journey lifecycle. The bundle includes canonical `identity.trip` and its selected route geometry, `identity.attempt_id`, `identity.analysis_status`, source-specific availability/status and normalized payloads, `readiness`, `ready_for_briefing`, and `assembled_at`. No bundle UI or briefing trigger is added.

`JourneyEvidenceState` owns the active `attempt_id`, captured canonical `trip`, existing `analysis`, and matching `camera_vision`. App reuses the analysis request generation as the shared attempt identity. Derivation is suppressed when there is no active attempt or the live selected Trip differs from the captured one. The assembler receives the current explicit ISO timestamp whenever lifecycle inputs change. It copies only normalized application evidence; it makes no request and does not invoke OpenRouter.

After a valid analysis succeeds, its existing Road Ahead, DriveBC, OpenWeather, and SWOB outcomes produce a usable bundle even while camera inference is pending. The aggregate is `partial` and `ready_for_briefing: true` until remaining sections resolve. Matching camera completion or an explicit timeout/provider/unavailable/insufficient-evidence result updates the derived bundle while preserving road/weather evidence. Analysis pending, failure, or unknown remains not ready. Source statuses preserve their individual pending, failed, unavailable, empty, partial, and unknown distinctions.

The established invalidation paths clear the shared attempt state on origin/destination edits, Find Routes, and selected-route changes. Existing analysis generation/key checks, camera sequence/key checks, cancellation, deadline, and guarded result retention reject late results. Regression coverage tests canonical trip/route and attempt association, partial readiness, camera update/failure, invalidation, stale source suppression, and request-free derivation. Verification details and known manual-acceptance limits are in `PROJECT_STATE.md` Section 42.
