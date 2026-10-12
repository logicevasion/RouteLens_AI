# RouteLens AI — Build Plan

## 1. Current Phase

**Phase:** 10 — AI Journey Briefing

**Phase status:** Planning and specification preparation. Phase 10 implementation has not started. Phase 9 — Journey Evidence Organization and Reconciliation is human accepted and complete (2026-10-11). Assignments 9A–9D delivered the typed, source-attributed `JourneyEvidenceBundle v1`, deterministic evidence assembly, conservative readiness semantics, and lifecycle-safe handoff in `frontend/src/App.tsx`. The final Phase 9 Git checkpoint remains pending the developer's commit/push unless completed separately.

**Source:** `docs/implementation-plan.md` Phase 10; `docs/prd.md`; `docs/technical-design.md`; accepted Phase 8 camera-vision and Phase 9 journey-evidence contracts; `PROJECT_STATE.md`; and associated integration notes. Where documents differ, inspect the repository and report material discrepancies before changing accepted implementation authority. A dedicated Phase 10 build plan must be prepared and human approved before implementation.

**Previous phase:** Phase 9 — Journey Evidence Organization and Reconciliation, Assignments 9A–9D human accepted and complete on 2026-10-11. The accepted implementation uses a frontend-owned pure TypeScript assembler and memoized active-journey handoff. `journeyEvidenceBundle` is derived from canonical Trip/route identity, analysis attempt generation, normalized road/weather/SWOB evidence, and matching Phase 8 camera observations. Partial evidence remains usable; stale or mismatched journey results are rejected. Phase 9 introduced no additional external provider calls, user-facing evidence UI, or LLM inference.

**Next objective:** Design and implement one concise, validated, source-grounded AI Journey Briefing displayed at the **top of Journey Intelligence**. The briefing should explain important journey conditions using the accepted evidence bundle, distinguish official road events, weather observations/forecasts, and single-direction camera interpretations, and disclose unavailable or uncertain evidence. Phase 10 must define its own model/API contract, cost controls, single-generation lifecycle, error/fallback handling, and frontend presentation without duplicating Phase 8 camera inference or Phase 9 source reconciliation.

### Objective

Convert the existing independent journey-analysis results into **one coherent, validated, source-attributed journey evidence bundle** that can be consumed by Phase 10 without requiring the briefing model to independently reconstruct every source's semantics, reliability, location, timing, and uncertainty.

The Phase 9 pipeline should organize:

1. The canonical selected driving route and journey context.
2. City of Vancouver Road Ahead construction and closure findings.
3. DriveBC Open511 road incidents and route-relevant events.
4. OpenWeather destination weather conditions and short-term forecast evidence.
5. ECCC GeoMet/SWOB observed weather-station readings.
6. Phase 8 single-direction camera-vision telemetry and its authoritative camera provenance.
7. Source availability, limitations, uncertainty, relevance, and freshness.

The intended pipeline is:

**Canonical selected journey + accepted source results → validation and normalization → relevance classification → temporal/freshness organization → conservative cross-source reconciliation → versioned internal `JourneyEvidenceBundle` → Phase 10 AI Journey Briefing.**

The phase must deliver:

- A clearly typed and versioned internal evidence contract.
- Reuse of existing accepted source-specific analysis rather than independently reinterpreting raw provider payloads.
- Explicit distinction between authoritative source facts, measured observations, forecasts, and AI-generated visual interpretations.
- Stable association with the selected route, destination, and active Analyze Journey attempt.
- Conservative spatial and temporal relevance.
- Honest representation of missing, unavailable, stale, ambiguous, or contradictory evidence.
- Bounded, deterministic reconciliation rules that never invent missing observations.
- A compact, traceable collection of evidence suitable for an eventual briefing prompt.
- Failure isolation and preservation of existing road/weather/camera presentation.
- Automated validation, end-to-end integration testing, and human acceptance.

**Phase 9 organizes and reconciles evidence. It does not write the final user-facing AI Journey Briefing.**

Phase 10 owns the generation of that briefing, which will appear prominently at the top of Journey Intelligence and should communicate the journey's meaningful conditions without requiring users to inspect every supporting panel.

### Locked product boundaries

- **Driving only**, using the accepted canonical origin, destination, selected route, and explicit Analyze Journey lifecycle.
- **No new external data sources** during Phase 9. Work only with the already accepted route, Road Ahead, DriveBC, OpenWeather, SWOB, and camera-vision evidence.
- **No new inference role or OpenRouter call** for evidence organization. Phase 9 uses deterministic application logic. Phase 8 camera inference remains the only existing AI observation source.
- **No source fabrication.** A missing or failed provider cannot be represented as confirming clear roads, good weather, light traffic, or the absence of hazards.
- **No unsupported geospatial expansion.** Destination weather and destination camera observations must not be represented as describing every point along the selected route.
- **No invented travel timeline.** Do not fabricate departure times, arrival times, segment ETAs, expected delays, or future weather conditions.
- **No route scoring, rerouting, automatic route selection, or safety certification.**
- **No user-facing evidence bundle, debug JSON panel, standalone camera-AI interpretation card, or intermediate AI summary card.**
- Existing Journey Intelligence panels, map, events, weather display, camera gallery, and interaction behavior remain unchanged unless a specific Phase 9 integration requirement necessitates a minimal adjustment.
- The validated camera observation remains based on **one directional frame** from the nearest selected destination intersection; do not expand camera inference to other views or intersections.
- No camera image archive, model response archive, or new historical data collection.
- All Git staging, commits, pushes, and history changes remain the human developer's responsibility.

---

## 2. Execution Scope and Authorization

Phase 9 is divided into four proposed, separately authorized assignments.

This subdivision is a planning proposal, not a claim that the existing implementation plan already specifies these exact assignment names or boundaries. Assignment 9A must reconcile the subdivision against accepted project documentation before finalizing the implementation scope.

### Assignment 9A — Evidence Inventory and Contract Design

**Purpose:** Establish exactly which source results Phase 9 receives, what each result means, and the smallest reliable unified evidence representation.

- Inspect the actual current backend/frontend contracts for canonical Trip, route selection, Road Ahead, DriveBC, OpenWeather, SWOB, Phase 7 camera metadata, and Phase 8 `AdapterResult`.
- Trace each source's lifecycle, request identity, result location, status/error vocabulary, timestamps, and provenance.
- Identify which road events have already been matched against the selected route and which evidence remains destination-specific.
- Verify the existing handling of road-event geometry, event validity windows, weather forecast intervals, station observations, camera frame retrieval time, and model inference time.
- Identify existing source-specific typed models and reusable helpers.
- Define the minimal `JourneyEvidenceBundle` contract and versioning.
- Define evidence identities, source labels, relevance categories, temporal fields, confidence/uncertainty representation, and missing-source states.
- Define which source records can be summarized or condensed without losing evidence necessary for Phase 10.
- Establish conservative reconciliation rules and any unresolved product decisions.
- Define where the bundle should be assembled and retained, based on the actual architecture and Phase 8D `JourneyEvidenceState`.
- Document the proposed 9B–9D interfaces and verification strategy.

**9A exit gate:** Human approves the exact bundle schema, evidence semantics, reconciliation rules, assembly location, and remaining 9B–9D scope.

**9A boundary:** Research, contract design, and small safe fixtures only. No production evidence assembler, new AI call, frontend briefing, or unrelated refactor.

### Assignment 9B — Source Normalization and Evidence Assembly

**Purpose:** Implement deterministic extraction of trustworthy evidence records from existing validated source results.

- Create or reuse the minimal typed `JourneyEvidenceBundle` models approved in 9A.
- Adapt existing road-event findings into a uniform evidence representation while preserving source-specific meaning.
- Adapt destination weather and SWOB observations without conflating forecast and measurement.
- Adapt the Phase 8 camera observation, preserving its single-view coverage and separating model-generated values from backend provenance.
- Preserve the canonical selected route, trip identity, available route geometry references, and evidence-source statuses.
- Capture timestamps and source freshness information without treating all source timestamps as interchangeable.
- Retain source-specific IDs or stable references sufficient to trace supporting evidence.
- Represent missing, failed, stale, or unsupported sources explicitly.
- Add bounded record counts and payload-size controls appropriate to the existing application.
- Preserve unknown values instead of filling them with guessed defaults.
- Implement purely deterministic transformation functions suitable for offline unit tests.

**9B exit gate:** Mocked source results produce a schema-valid internal bundle with correct identities, statuses, provenance, source types, and explicit missing/uncertain evidence.

**9B boundary:** Evidence normalization and assembly only. No cross-source conclusions, new provider calls, final briefing, or extensive frontend changes.

### Assignment 9C — Relevance, Freshness, and Conservative Reconciliation

**Purpose:** Make the assembled evidence useful to Phase 10 while avoiding unsupported conclusions.

- Preserve accepted Road Ahead and DriveBC route-relevance findings rather than replacing their geospatial matching algorithms.
- Distinguish evidence located on or near the selected route from destination-area evidence and more general context.
- Organize temporal evidence into observed, current-reported, forecast, scheduled/event-validity, stale, or unknown categories where source semantics support those distinctions.
- Preserve source freshness, reporting time, validity windows, forecast target times, retrieval time, and model inference time as separate concepts.
- Identify when two sources appear to address a related condition without assuming they are measuring the same thing.
- Identify possible supporting, complementary, overlapping, or potentially conflicting evidence only where there is a justified common subject, location, and time.
- Treat apparent contradictions as uncertainty or limited coverage, not as permission to select a preferred fact without evidence.
- Avoid redundant display of the same underlying event when the same source record has multiple representations; do not merge distinct real-world events based only on proximity or similar wording.
- Produce compact evidence annotations and source references that a later briefing generator can use.
- Keep camera visual assessments explicitly marked as model interpretations of one directional frame.
- Validate the reconciled bundle against the approved 9A contract.

**9C exit gate:** Representative source combinations produce conservative relevance and temporal classifications without invented severity, delay, weather, or citywide conclusions.

**9C boundary:** Deterministic organization and reconciliation only. No LLM-generated narrative, travel advice, scoring, rerouting, or Phase 10 implementation.

### Assignment 9D — Journey Lifecycle Integration and Evidence Handoff

**Purpose:** Attach the accepted evidence bundle to the existing Analyze Journey lifecycle and verify that Phase 10 can consume it safely.

- Integrate the assembled bundle into the existing journey state or smallest appropriate typed internal interface.
- Reuse Phase 8D's canonical Trip, attempt identity, cancellation, and stale-result protections.
- Determine how independent evidence-source completion and pending camera inference affect bundle readiness.
- Preserve nonblocking road/weather/camera presentation while the evidence bundle is being assembled or updated.
- Ensure late Phase 8 camera inference cannot attach to a different trip or superseded analysis.
- Avoid creating a misleading complete bundle while required source requests remain pending.
- Establish explicit bundle readiness and source-coverage states appropriate to Phase 10.
- Preserve completed independent evidence when other sources fail.
- Make Phase 10's eventual input contract stable and documented, without calling a briefing model.
- Verify that no raw provider/image data is copied into the bundle.
- Complete mocked lifecycle, regression, frontend/build, and manual acceptance checks.

**9D exit gate:** A valid explicit Analyze Journey operation produces an internal, versioned, source-attributed and lifecycle-safe evidence bundle. Its source statuses, limitations, relevance, and timestamps are sufficient for Phase 10 to construct a briefing without repeating upstream inference or interpreting raw provider payloads.

**9D boundary:** No AI Journey Briefing UI, natural-language briefing generation, new inference role, route changes, or unrelated interface redesign.

**Assignment rule:** Codex receives authority only for the currently human-approved assignment. Completion and acceptance of one assignment do not automatically authorize the next. Codex must not stage, commit, push, merge, rebase, tag, or change Git history.

---

## 3. Established Accepted Baseline

### 3.1 Application and journey context

- FastAPI backend; React/Vite/TypeScript frontend; MapLibre/MapTiler dark map; Vite `/api` proxy; backend-held credentials.
- Canonical origin/destination and City of Vancouver destination validation.
- ORS driving routes with explicit candidate selection.
- Manual `POST /api/trips/analyze` request using the accepted selected-route geometry.
- Existing analysis generations and stale-request invalidation.
- Explicit Analyze Journey remains the only trigger for the camera-vision operation.

Phase 9 must reuse the actual selected journey context, not reconstruct a route from origin/destination independently.

### 3.2 Road Ahead municipal road evidence

- Accepted City of Vancouver Road Ahead source and cache.
- Existing construction, closure, and road-work findings.
- Existing selected-route spatial relevance behavior.
- Accepted event metadata and map/panel interactions.
- Source-specific status and failure handling.

Road Ahead provides official municipal event information. It must not automatically be translated into a precise travel-time delay or proof that a road segment is impassable unless the source and accepted analysis explicitly establish that fact.

### 3.3 DriveBC Open511 road evidence

- Accepted regional incident/event ingestion and cache behavior.
- Existing route-relevant event analysis.
- Conservative spatial matching, including source geometry limitations.
- Distinct source attribution from Road Ahead.

A nearby incident is not necessarily an incident on the selected route. Preserve the accepted relationship between incident location and route geometry.

Do not merge DriveBC and Road Ahead into one untraceable source.

### 3.4 Destination weather — OpenWeather

- Accepted OpenWeather One Call 4.0 current conditions and 15-minute forecast integration.
- Existing 600-second data caching.
- Persistent upstream-request budget with 100 attempts per UTC day, separate from the provider account limit.
- Destination-focused spatial scope.

Preserve the distinction between current provider conditions, forecast values, and their target intervals. Forecast data is not a direct measurement at the destination.

### 3.5 Observed weather — ECCC GeoMet/SWOB

- Accepted station-based weather observations.
- Existing freshness/cache behavior.
- Station identity, observation time, and available provenance.
- Conservative treatment of station distance and relevance.

SWOB station observations are measurements at identified observation stations, not direct measurements everywhere along the route or at the destination.

Do not silently treat SWOB and OpenWeather as two interchangeable weather readings.

### 3.6 Destination cameras — Phase 7

- Official City of Vancouver camera catalogue with validated intersection and directional-view metadata.
- Destination-camera selection and validated latest-frame retrieval.
- Short-lived current-frame cache; no historical image archive.
- Existing Phase 7 directional gallery and nearby map markers.
- Camera source attribution and official camera webpage links.

The gallery may display multiple directions, but the accepted Phase 8 inference policy analyzes only one eligible directional frame.

### 3.7 Camera vision — Phase 8

- Accepted `POST /api/cameras/observe` backend endpoint.
- Accepted `OpenRouterVisionAdapter`.
- Model `google/gemma-4-31b-it`, automatically selected OpenRouter provider, strict structured output and local validation.
- `camera-observation-v1` schema and `camera-visual-observer-v2` prompt.
- First eligible directional image in canonical catalogue order.
- Existing 60-second backend and 70-second frontend vision deadlines.
- Existing attempt quotas, estimated spending controls, no corrective retries, and bounded result reuse.
- Backend-controlled intersection/view IDs, direction, retrieval timestamp, nullable capture timestamp, digest, image identity, official source, model/provider, and usage.
- Typed `available`, `partial`, `insufficient_evidence`, `unavailable`, and `error` outcomes.
- Explicit Analyze Journey lifecycle ownership and internal `JourneyEvidenceState` camera-vision field.
- Two successful real-camera inference tests through reported provider CoreWeave, each producing one validated directional observation at approximately 6–7 seconds inference latency.

**Accepted limitation:** These tests establish working image inference and output validation, not measured accuracy of the camera observations. Their reported uncertainty levels are model-produced labels, not calibrated probabilities.

### 3.8 Existing contracts remain authoritative

Before implementing Phase 9, inspect the repository for exact typed models, result shapes, module locations, timestamps, readiness semantics, source-status values, and existing frontend lifecycle helpers.

The descriptions in this build plan are baseline summaries, not substitutes for code inspection.

Do not duplicate working fetchers, parsers, route matchers, caches, geospatial calculations, image validation, or camera inference logic.

---

## 4. Journey Evidence Bundle Contract

### 4.1 Conceptual purpose

The `JourneyEvidenceBundle` is an **internal normalized representation of the evidence available for one selected journey-analysis attempt**.

It is not:

- An additional source of independently measured facts.
- A new provider response.
- A free-form AI-generated report.
- A persistent traffic-history database.
- A user-facing Journey Intelligence card.
- A replacement for existing source-specific results or panels.

It should let the Phase 10 briefing system answer:

- Which journey and route are being analyzed?
- What relevant road events are reported?
- What current and forecast weather evidence is available?
- What station measurements are available and where?
- What did the selected destination camera image appear to show?
- Which claims are facts reported by authoritative sources, which are forecasts, and which are model interpretations?
- Where, when, and how does each piece of evidence apply?
- What information is missing, uncertain, unavailable, stale, or contradictory?

### 4.2 Proposed conceptual structure

The following is a design starting point for Assignment 9A, **not a finalized schema**.

```text
JourneyEvidenceBundle
  schema_version

  journey_context
    canonical_trip
    selected_route_identity
    selected_route_geometry_reference
    analysis_attempt_identity
    assembled_at

  source_coverage[]
    source_id
    status
    requested_or_applicable
    last_success_or_retrieval_time_if_known
    error_or_limitation_code_if_any

  evidence_items[]
    evidence_id
    source_id
    evidence_kind
    source_record_reference

    spatial_relevance
    temporal_relevance

    observed_or_reported_at_if_known
    retrieved_at_if_known
    valid_from_if_known
    valid_until_if_known
    forecast_target_time_if_known

    normalized_fact_or_observation
    uncertainty_or_limitation
    provenance

  relationships[]
    related_evidence_ids
    relationship_kind
    rationale_code

  readiness
    state
    pending_sources
    unavailable_sources
    partial_coverage

  limitations[]
```

The final 9A contract must be derived from existing source types and the actual consumer needs of Phase 10.

Prefer a small, understandable structure. Do not implement fields without a practical source or consumer requirement.

### 4.3 Evidence kinds

At minimum, the design should distinguish:

| Evidence kind | Source example | Interpretation |
|---|---|---|
| Official road event | Road Ahead | Source-reported construction, closure, or road-work information |
| Official road incident | DriveBC Open511 | Source-reported incident/event with existing route relationship |
| Provider current weather | OpenWeather | Current provider conditions at the configured location |
| Weather forecast | OpenWeather | Predicted conditions for a defined forecast interval |
| Measured station observation | ECCC SWOB | Observed conditions at a particular station and time |
| AI visual interpretation | Phase 8 camera vision | Model assessment of one selected directional image |
| Journey context | Canonical Trip / ORS route | User-selected route and destination context, not an external hazard observation |

Use the actual accepted source semantics rather than forcing incompatible source data into a single generic category.

### 4.4 Authoritative provenance versus interpretation

Authoritative application/source metadata includes:

- Journey and selected-route identity.
- Road-event source and source record identifiers.
- Accepted road-event geometry and route relationship.
- Weather provider and forecast or observation times.
- SWOB station identity/location and observation time.
- Camera intersection, direction, source page, retrieved frame identity, and destination distance.
- AI model/provider identity, inference time, and reported usage.

These fields must never be rewritten by model-generated interpretation or inferred from visual text.

Model-generated camera fields remain subordinate observations, including road-surface appearance, visibility, visible vehicle activity, controlled condition labels, uncertainty, notes, and optional summary.

### 4.5 Evidence identities and traceability

Every evidence item should have a stable reference sufficient to associate it with its original accepted source record **within the current journey context**.

Prefer existing source IDs and accepted canonical identities.

If normalized IDs are required, generate them deterministically from trusted source identity and relevant stable record fields.

Do not use an AI-generated identifier as an authoritative source reference.

Do not allow unrelated incidents to collapse into one record merely because they share a street name or approximate location.

Preserve the ability for Phase 10 and existing supporting UI to identify the original evidence source.

### 4.6 Bounded content

Keep the evidence bundle compact enough for later briefing generation without removing essential provenance.

Proposed constraints for 9A to finalize:

- Reuse source-specific event counts and relevance filters where available.
- Keep the most relevant records according to explicit, deterministic rules.
- Preserve source-coverage and omission counts when records are omitted for size.
- Prefer concise factual fields and bounded source descriptions.
- Do not place raw API payloads, camera JPEG bytes, base64 images, or entire provider completions inside the bundle.
- Do not silently truncate important events in a way that implies complete coverage.

If source evidence exceeds the accepted bundle budget, report the limitation rather than pretending the retained subset is exhaustive.

---

## 5. Relevance and Geospatial Semantics

### 5.1 Reuse accepted route relevance

Road Ahead and DriveBC route matching are already implemented and accepted.

Phase 9 must consume their findings instead of recomputing intersection/proximity logic.

Preserve source-specific distinctions such as:

- Event geometry intersects selected-route geometry.
- Event point lies near the selected route.
- Event is reported in the broader journey area without confirmed route impact.
- Event relationship is uncertain because source location or geometry is incomplete.

Only expose categories actually supported by accepted analysis.

Do not change existing distance thresholds or geospatial matching logic without a documented defect and human approval.

### 5.2 Destination-area evidence

OpenWeather destination conditions, destination-focused forecasts, and destination camera observations should normally be classified as destination-area evidence.

The Phase 8 camera observation is tied to the backend-selected camera intersection, including its approximate distance from the canonical destination.

Preserve that distance and the single selected direction.

A camera located 150 metres from a destination does not automatically describe the destination's exact weather, all intersection approaches, or the entire route.

### 5.3 SWOB station relevance

Retain the station's actual identity, location where available, observation time, and supported relationship to the destination.

Do not treat nearby station observations as measurements made at the destination.

Do not infer fine-grained weather conditions between stations without an accepted interpolation method.

### 5.4 Source coverage

Distinguish:

- An event source returned no relevant events.
- The event source was unavailable.
- The event source returned stale or incomplete data.
- The source returned events but none met the accepted route-relevance criteria.
- The source has information that cannot be spatially evaluated with confidence.

These outcomes should not collapse into a generic "no issues" statement.

---

## 6. Temporal Organization and Freshness

### 6.1 Timestamp meanings

Source timestamps have different meanings.

Phase 9 must preserve the distinction between:

- **Source-reported occurrence or observation time:** When the source says something happened or was measured.
- **Source validity window:** When a road event, construction notice, or other record is reported to apply.
- **Forecast target time:** When predicted weather is expected.
- **Retrieval time:** When RouteLens fetched the source information.
- **Camera frame retrieval time:** When the camera image was retrieved; not necessarily its capture time.
- **Verified camera capture time:** Only when established by source metadata.
- **Camera inference time:** When Gemma produced the visual interpretation.
- **Bundle assembly time:** When Phase 9 organized the evidence.

Do not substitute one meaning for another.

### 6.2 Current versus future conditions

The application may have both current information and forecasts covering future intervals.

Phase 9 should preserve that distinction without inventing a trip departure time or estimated time of arrival.

For example:

- "Current conditions at destination" is distinct from "forecast for the next 15-minute interval."
- "Construction scheduled during a published interval" is distinct from "construction confirmed active at the user's eventual arrival."
- "Camera frame retrieved recently" is distinct from "camera image captured at the same instant."

### 6.3 Freshness policy

Do not impose one universal TTL on all evidence.

Continue respecting existing source-specific cache and freshness policies.

Assignment 9A should define how the bundle represents source freshness, source expiry, and unknown timestamps without adding unnecessary cache layers.

Stale records may be retained as explicitly stale evidence if the accepted source contract permits it, but must not be portrayed as current.

### 6.4 Timeline representation

For the MVP, temporal organization should mean **categorizing evidence according to its supported time semantics**, not generating a simulated route itinerary.

Do not create:

- Route-segment arrival times.
- Forecast conditions at unverified arrival times.
- Travel-time adjustments from road-event presence.
- Predicted camera conditions later in the journey.
- A fabricated sequence of when road incidents will affect the traveler.

Phase 10 may explain source-supported timing in ordinary language, but Phase 9 must not manufacture a detailed trip timeline.

---

## 7. Cross-Source Reconciliation

### 7.1 Guiding principle

**Reconciliation means organizing relationships between evidence, not manufacturing agreement between sources.**

Phase 9 should establish which pieces of evidence are related, complementary, conflicting, or too different to compare meaningfully.

It must not resolve discrepancies by inventing certainty.

### 7.2 Road Ahead and DriveBC

These are separate official reporting systems with different geographic scope, event types, and reporting conventions.

Where events have related locations or subjects:

- Preserve each source's identity.
- Reuse existing route-relevance findings.
- Avoid declaring that separate records describe the same incident without sufficiently strong evidence.
- Do not infer that one source confirms the other merely because their events are geographically close.
- Do not turn a construction or incident report into an unsupported travel delay.

### 7.3 OpenWeather and SWOB

OpenWeather and ECCC SWOB provide different kinds of weather evidence.

OpenWeather may supply current conditions and forecasts for the configured location; SWOB supplies actual station observations.

Potential disagreement should retain its spatial, temporal, and measurement differences.

Examples:

- A weather forecast and a station measurement do not necessarily contradict one another.
- A station observation from an earlier time does not refute a newer forecast.
- Different conditions at different nearby locations may both be accurate.

Do not create a synthetic "verified weather" fact merely because two providers return similar values.

### 7.4 Camera and weather

The Phase 8 camera model provides **visual interpretation of one directional image**.

A `wet_looking` road surface does not prove active rainfall.

A dry-looking surface does not disprove rain reported at a weather station or predicted for the destination.

`not_observable` is not evidence that a condition is absent.

Camera interpretation may provide supporting or contrasting local context only when location, time, and observed details justify that relationship.

The model-generated uncertainty field is qualitative and uncalibrated.

### 7.5 Camera and road events

A visible apparent queue is not proof of a reported traffic incident, congestion level, construction impact, or road closure.

An official road incident is not necessarily visible in the selected directional camera view.

The camera should not be used to confirm or deny Road Ahead/DriveBC events unless the accepted visual evidence and source relationships genuinely support such a conclusion.

For the MVP, conservative non-comparison is preferable to unsupported correlation.

### 7.6 Relationship types

Assignment 9A should consider a minimal internal relationship vocabulary such as:

- `supports`
- `complements`
- `potential_conflict`
- `overlapping_report`
- `not_comparable`

These are **proposed design candidates**, not frozen enum names.

Only implement relationship types with clear deterministic evidence and useful Phase 10 consumer semantics.

It is acceptable to leave evidence items unlinked rather than invent a relationship.

---

## 8. Uncertainty, Absence, and Readiness

### 8.1 Evidence certainty

Distinguish among:

- Official source-reported facts or events.
- Measured observations at identified stations.
- Forecast/predicted conditions.
- Model-generated visual interpretations.
- Unknown or insufficiently observable conditions.
- Unsupported or unavailable source data.

Do not assign invented numerical confidence scores.

A source's authority in its own domain does not guarantee that an event affects the selected route.

### 8.2 Missing data is not a negative finding

The following must remain different:

- No relevant Road Ahead events returned.
- Road Ahead request failed.
- No DriveBC incidents matched the route.
- DriveBC data was unavailable.
- OpenWeather returned no forecast for a requested interval.
- SWOB provided no usable observation.
- The selected camera had no eligible current frame.
- Camera inference returned `insufficient_evidence`.
- Camera inference returned `invalid_model_output` or timed out.

Phase 9 must preserve enough distinctions that Phase 10 cannot casually turn provider failure into "no hazards detected."

### 8.3 Evidence readiness

The bundle must convey whether its constituent evidence sources are:

- Still pending.
- Completed successfully.
- Completed with partial or uncertain evidence.
- Unavailable, stale, or failed.
- Superseded by a newer journey attempt.

The exact bundle readiness vocabulary is a 9A contract decision.

**Partial source availability should not automatically invalidate the entire journey evidence bundle.**

A future briefing should be able to describe known conditions and disclose missing sources rather than failing altogether.

### 8.4 Late camera inference

The Phase 8 camera inference may complete after the ordinary road/weather analysis.

Phase 9 must not attach observations from a superseded analysis.

Assignment 9A should inspect how `JourneyEvidenceState` currently handles pending/completed evidence and decide whether Phase 9 assembles incrementally, at a defined completion boundary, or through another minimal deterministic policy.

Do not create a new background job manager or persistent task queue for this.

A bundle must never silently claim completeness while a relevant request is pending.

---

## 9. Integration and Lifecycle Architecture

### 9.1 Existing ownership

Phase 8D established the internal frontend journey-evidence state and camera-vision lifecycle.

Phase 9 should extend that accepted ownership model rather than introduce a parallel journey coordinator.

Inspect the exact current `JourneyEvidenceState` and existing analysis state before selecting an assembly location.

### 9.2 Proposed integration approach

Prefer a **pure, typed evidence-assembly function** operating on already validated application results, with a small lifecycle handoff.

Conceptually:

```text
Canonical Trip + selected route
        |
Existing Analyze Journey evidence results
        |
        +-- Road Ahead findings
        +-- DriveBC findings
        +-- OpenWeather destination weather
        +-- SWOB station observations
        +-- Phase 8 camera_vision result
        |
Deterministic evidence assembly
        |
Relevance + freshness + relationship annotations
        |
Validated JourneyEvidenceBundle
        |
Current journey internal state
        |
Phase 10 AI Journey Briefing (future)
```

This is a conceptual architecture diagram, not an instruction to create new files or classes for every box.

Assignment 9A must select the actual location based on available typed data and accepted module boundaries.

If a minimal frontend module is appropriate because all accepted results already converge there, prefer that over duplicating source fetches in the backend.

If existing authoritative backend types are required, preserve their source ownership and avoid transporting redundant large objects.

### 9.3 Lifecycle safety

- One bundle belongs to one canonical Trip, selected route, and analysis attempt.
- A new valid Analyze Journey attempt must not inherit evidence from an earlier attempt.
- Input or route changes must invalidate incompatible evidence.
- Late independent source results may update only their owning active attempt.
- No source result may overwrite a newer attempt's bundle.
- A partial bundle must preserve pending and unavailable source states honestly.
- No re-fetch or new model call may occur merely because the evidence bundle is assembled or recomputed.

### 9.4 Failure isolation

A Phase 9 transformation failure must not discard successfully fetched existing analysis results.

Use bounded internal validation errors or a safe unavailable state rather than rendering a fabricated bundle.

Road, weather, cameras, and map interactions remain operational even when evidence assembly is incomplete.

### 9.5 No additional persistence by default

The MVP does not require a historical evidence database.

Keep the current journey bundle in the existing appropriate application lifecycle state.

Do not persist raw provider responses or start background aggregation.

Any proposed new cache requires explicit evidence of need and human review.

---

## 10. Previous Phase 9 Validation and Test Requirements

Each assignment must report **Passed / Failed / Not run**, with source fixtures, mocked responses, and any manual browser checks clearly distinguished.

### 9A — Inventory and contract gate

- Actual source result types, modules, and lifecycle boundaries inspected.
- Existing route/geospatial relevance and source statuses identified.
- Timestamp semantics and source-specific freshness constraints documented.
- Proposed bundle schema and evidence-kind vocabulary reviewed.
- Provenance and uncertainty boundaries specified.
- Assembly location and Phase 10 consumer contract justified.
- Material discrepancies with accepted implementation documents reported.
- Human approval obtained before implementing the schema.

### 9B — Source normalization

- Road Ahead official event identity, type, source and accepted route relationship preserved.
- DriveBC source/event identity and geometry relationship preserved separately.
- OpenWeather current conditions distinguished from forecast intervals.
- SWOB station observations distinguished from destination observations.
- Camera observation bound to exactly the selected frame and intersection provenance.
- Camera model-generated fields remain separate from authoritative metadata.
- Missing provider response is distinguishable from empty valid results.
- Source timestamps retain their original meanings.
- No images, API credentials, full provider responses, or raw model completions appear in the bundle.
- The result validates against the approved schema.
- Source record caps/omissions are represented honestly.

### 9C — Relevance and reconciliation

- Existing accepted road-event route relationships are reused.
- Destination-area camera/weather evidence is not promoted to route-wide evidence.
- Forecasts remain forecasts; station observations remain station measurements.
- Camera `wet_looking` does not become confirmed rain.
- Camera `vehicle_activity` does not become route congestion or delay.
- Camera `not_observable` does not become a negative finding.
- Related but non-comparable measurements are not presented as definitive conflicts.
- Separate source records are not merged without sufficient identity evidence.
- Event timing and source freshness remain distinct.
- Unknown/missing data cannot produce positive claims.
- Reconciliation is deterministic, bounded, and independently testable.

### 9D — Lifecycle and handoff

- Explicit Analyze Journey produces an internal evidence bundle for the active canonical Trip and selected route.
- Find Routes, page load, marker interaction, and camera-image retrieval do not trigger new provider calls through bundle assembly.
- A late camera result belongs only to its original active analysis.
- An older result cannot overwrite a newer bundle.
- Road/weather/gallery rendering remains functional when camera inference fails.
- Partial evidence and unavailable sources are represented accurately.
- No unnecessary duplicate source retrieval or model inference occurs.
- Phase 10 can consume the final typed contract without parsing provider response text or reimplementing source-specific relevance.
- Backend regressions, Ruff, frontend tests, TypeScript and production build pass according to changed scope.
- Manual browser checks confirm ordinary journey presentation remains unchanged.

### General hygiene

- `.env` and secrets remain ignored and inaccessible to frontend state.
- No raw camera images, image-filled prompts, complete OpenRouter responses, or unrestricted provider errors are logged.
- No new upstream requests are introduced by deterministic evidence assembly.
- `git diff --check`, changed-file review, and relevant cache ignore checks pass.
- No unsupported source or timeline claims.
- No historical evidence archive, polling worker, or automatic inference loop.
- Documentation identifies exactly what was implemented, tested, deferred, and accepted.

---

## 11. Previous Phase 9 Non-Goals

Phase 9 does **not** authorize:

- Generating a user-facing AI Journey Briefing.
- Adding a new LLM role or another OpenRouter request.
- Reprocessing camera images or expanding single-image inference.
- Additional camera intersections or map-marker camera inference.
- New Road Ahead, DriveBC, weather, transit, air-quality, or other external data sources.
- Reworking accepted ORS route calculation or route selection.
- Replacing existing Road Ahead/DriveBC geospatial matching.
- Automatic traffic-delay or speed estimation.
- Route scoring, ranking, rerouting, or recommendations that alter the selected journey.
- Generating an estimated future weather timeline without an accepted ETA/departure model.
- Treating SWOB measurements as direct destination observations.
- Treating AI camera assessments as measured weather or official road-event confirmation.
- User-facing standalone evidence, diagnostics, camera-AI, or timeline cards.
- Map layer redesign or unrelated UI restyling.
- Historical data collection, persistent evidence archives, or continuous monitoring.
- General-purpose agent orchestration, autonomous tool execution, recursive AI workflows, or model ensembles.
- Speculative source abstractions, plugin frameworks, new database systems, or broad refactors.
- Public/commercial deployment authorization based on private-prototype testing.

---

## 12. Previous Phase 9 Human Acceptance Criteria

Phase 9 is eligible for final human acceptance only when:

- [ ] The actual existing source/result contracts have been inspected and reconciled with the accepted design documents.
- [ ] A human-approved `JourneyEvidenceBundle` schema and version are documented and implemented.
- [ ] The bundle is bound to one canonical Trip, selected route, and active analysis attempt.
- [ ] Road Ahead findings retain official source identity and accepted route relevance.
- [ ] DriveBC findings retain official source identity and accepted route relevance separately.
- [ ] OpenWeather current and forecast fields retain their distinct temporal meanings.
- [ ] SWOB observations retain station provenance and measurement time.
- [ ] Phase 8 camera evidence preserves backend-controlled intersection and single directional-frame provenance.
- [ ] Camera interpretations remain model-derived visual evidence, not official traffic or weather facts.
- [ ] Source timestamps, validity windows, forecast target times, retrieval times, and model inference times are not conflated.
- [ ] Geospatial relevance does not overstate route-wide or destination-wide coverage.
- [ ] Missing, failed, unavailable, stale, pending, and valid-empty source states remain distinguishable where source contracts support them.
- [ ] Cross-source relationships are conservative and do not manufacture agreement, conflict, or causal explanation.
- [ ] No unsupported route delay, congestion severity, rainfall verification, closure confirmation, or travel timeline is introduced.
- [ ] Evidence items remain traceable to source records and authoritative provenance.
- [ ] Bundle size and omitted evidence are handled honestly.
- [ ] Existing provider caches, request budgets, and model inference limits remain unchanged.
- [ ] No new provider call is triggered solely by evidence assembly.
- [ ] Stale/superseded results cannot contaminate a newer journey bundle.
- [ ] Independent road/weather/camera presentation works when one or more evidence sources fail.
- [ ] The internal bundle is available for Phase 10 without implementing Phase 10.
- [ ] No new user-facing AI narrative, evidence/debug card, or raw JSON display is added.
- [ ] Automated tests and applicable backend/frontend regressions, Ruff, TypeScript and build pass.
- [ ] Manual journey testing verifies the expected internal evidence handoff and existing UI behavior.
- [ ] `PROJECT_STATE.md` and integration notes accurately record schemas, provenance, limitations, verification, and developer acceptance.
- [ ] Codex stops at each authorized assignment boundary and leaves all Git operations to the developer.

These are proposed Phase 9 acceptance conditions to be finalized in Assignment 9A. Human approval is required; passing automated tests alone does not grant acceptance.

---

## 13. Blockers and Escalation

Stop the affected assignment and report evidence if:

- Accepted source result types cannot be safely reconciled without changing previously approved API contracts.
- The current journey lifecycle cannot associate independent source results with the same canonical analysis attempt.
- Existing source metadata is insufficient to distinguish essential timestamps or provenance.
- Relevance logic requires inventing geometry or reconstructing source locations.
- Proposed reconciliation rules create unsupported weather, congestion, incident, or delay claims.
- Missing or failed sources cannot be represented without misleading downstream consumers.
- The evidence assembler requires new independent provider calls, unauthorized AI inference, or repeated paid image processing.
- Adding the bundle would break existing source-specific UI or stale-result behavior.
- A proposed implementation would require major architecture changes, historical persistence, or a new orchestration framework.
- The work cannot remain within the accepted Phase 9 scope without implementing Phase 10.

Report the observed issue, affected acceptance requirement, smallest safe alternatives, completed work, and what requires human resolution.

Continue independent in-scope design or fixture work where safe, but do not silently enlarge scope or invent missing requirements.

---

## 14. Phase Completion and Handoff

For each assignment:

1. Inspect accepted documentation and the current implementation baseline.
2. Perform only the separately authorized scope.
3. Prefer the smallest implementation that satisfies the approved contract.
4. Run proportionate offline verification and document any manual checks performed.
5. Update `PROJECT_STATE.md` and an appropriate integration note with factual results.
6. Distinguish completed, pending, blocked, unavailable, and unverified behavior.
7. Report changed files, tests, remaining limitations, and proposed next steps.
8. Stop for human acceptance.
9. Leave all Git staging, commits, pushes, and history operations to the developer.

After human Phase 9 acceptance:

1. Confirm that the final typed evidence bundle is tied to the correct journey.
2. Verify that road, destination weather, station observations, and camera telemetry retain distinct provenance.
3. Review representative bundles for unsupported relationships or missing-source misrepresentation.
4. Record the accepted schema version, source semantics, readiness behavior, tests, limitations, and handoff contract.
5. Human commits and pushes the completed Phase 9 checkpoint.
6. Prepare and human-review a new Phase 10-specific `BUILD_PLAN.md`.

This build plan does not authorize all Phase 9 assignments simultaneously.

---

## 15. Next Phase

**Phase 10 — AI Journey Briefing**

Phase 10 will consume the accepted `JourneyEvidenceBundle` and generate the primary user-facing AI Journey Briefing.

The briefing will appear at the **top of Journey Intelligence**, above the existing supporting road-event, destination-weather, and camera sections.

Its product objective is:

**A user should be able to understand the important journey conditions from the briefing alone, while retaining the map, road events, weather information, and camera imagery as supporting evidence.**

The briefing must:

- Use the accepted evidence bundle rather than independently hallucinating source facts.
- Identify meaningful road-event, destination-weather, and visual-camera information when supported.
- Distinguish official source findings, observed measurements, forecasts, and AI visual interpretations.
- Communicate missing or unavailable sources without presenting their absence as safe conditions.
- Avoid unsupported traffic-delay estimates, road closures, precise destination rain claims, or citywide visual conclusions.
- Attribute camera evidence to its actual intersection and directional view, including approximate distance from the destination.
- Respect the single-image MVP limitation.
- Avoid presenting low-quality or insufficient visual observations as strong findings.
- Remain concise, readable, and genuinely useful for deciding what to expect during a journey.

Phase 10 will separately determine its model, prompt, evidence serialization, response validation, fallback behavior, UI presentation, latency and spending controls.

**No Phase 10 implementation or AI briefing generation is authorized by this Phase 9 plan.**
