# RouteLens AI — Alpha UX v1

## Status and purpose

Approved requirements supplied by the human developer for a small, protected private alpha with friends. This document prepares future implementation; no Alpha UX code is implemented or authorized by this documentation task. The accepted datathon MVP and QAR-1, QAR-2, USER-001, and USER-002 form the baseline. [BUILD_PLAN.md](../BUILD_PLAN.md) separates the two implementation slices; [PROJECT_STATE.md](../PROJECT_STATE.md) records actual status.

The objective is faster access to deterministic journey evidence while retaining the dark visual style and existing source semantics. Authentication, usage tracking, protection mechanisms, and deployment remain separately scoped work; this specification does not establish that a hosted alpha is protected or ready to deploy.

## Stage 1 — Plan Your Journey

Retain the top header and existing origin, destination, Find Routes, and Analyze Journey controls. Keep validation, canonical locations, explicit route selection, candidate rendering, selection colours, and highlighting. On desktop the interactive map occupies approximately 65% and the route-selection panel approximately 35%.

Remove the unused pre-analysis AI Journey Briefing placeholder. Before candidates exist, provide concise guidance to choose locations and find routes. Once candidates are available, reuse the existing Choose Your Route UI, including approximate distance/duration and explicit selection. Preserve loading, no-route, validation, and error feedback. Never select the first candidate automatically.

## Stage 2 — Understand Your Journey

A valid Analyze Journey action enters Stage 2 immediately, before analysis or AI completes. Retain the header and journey controls. Lead with a full-width responsive primary summary, initially using approximately equal camera and weather columns on desktop and stacking them when space requires. Do not defer this summary behind an AI spinner. Each evidence area presents its own available, loading, stale, empty, or unavailable state. On each valid transition into Stage 2, bring the beginning of the “Understand Your Journey” section into view once. Do not move keyboard focus. Later evidence or briefing state updates must not repeat the scroll, and ordinary user scrolling after entry must remain undisturbed. Keep the transition compatible with the existing page layout and accessible navigation.

### Primary summary

1. **Destination cameras:** Display one directional image at a time with accessible direction navigation and current position/total. Use the actual usable returned views at the selected intersection, including clearly marked stale views under existing fallback semantics; never assume four directions. Zero views shows an unavailable state; one view needs no active navigation. Preserve full direction labels, intersection name, approximate destination distance, source attribution, official source link, retrieval timestamp and age, supplied capture timestamp or explicit capture-time unavailability, and partial/stale warnings. Navigation is presentation only: it must not trigger analysis, new retrieval, or inference, or change the backend-selected inference image. Reset or clamp the view selection when the result changes and retain image-load failure isolation.
2. **OpenWeather current conditions:** Show temperature, condition, feels-like, humidity, wind speed, visibility, observation time, and freshness when supplied. Retain units and source identity. Unavailable values stay unknown, never zero or inferred.
3. **Next hour:** Show upcoming, actually available 15-minute OpenWeather forecast points in an approximately 60-minute window starting from the current analysis time. Use actual returned forecast timestamps and exclude intervals already elapsed at analysis time. Retain and show the provider evaluation timestamp and existing freshness/stale indicators; these do not shift the display window. Sort by forecast timestamp and retain gaps and incomplete coverage warnings. Do not fill missing intervals, interpolate, or select more distant points merely to obtain four entries. Show actual times and available measurements; probability is not precipitation amount. Preserve the full returned three-hour forecast in supporting information. This is a display selection only: do not alter normalized forecast data or evidence supplied to the briefing.
4. **One ECCC station:** Among returned observations with `observation_stale === false` and at least one useful, available measurement, choose the closest by `distance_meters`; use station ID as a stable tie-breaker. Reuse normalized `useful_measurements` and freshness flags rather than inventing a new age threshold. Show station name/ID, distance, observation timestamp/age, available measurements with units/accumulation periods, and cache-stale warning where applicable. If none qualifies, say no sufficiently recent useful station is available. This is a nearby measured observation, distinct from coordinate-based destination weather; no interpolation or substitution. Other returned stations remain supporting data.
5. **Road Ahead count:** Count existing Road Ahead findings classified `direct_overlap` only. Exclude nearby findings, regional map context, and DriveBC from this count. Suggested wording: “N Road Ahead events intersect the selected route in available data.” If sources are partial/stale, qualify the count; if unavailable or not yet checked, show that state rather than a reassuring zero. A successful zero means no intersections identified in available datasets, never that roads are clear.

### Supporting sections and order

Below the primary summary, show the existing interactive map beside route-intersecting Road Ahead events, stacking responsively. Preserve route and construction highlighting, source-scoped event identity, selection and event-to-map focus, and existing map overlays including metadata-only camera markers and regional context.

Place the AI Journey Briefing below that map/construction section and label it **Experimental**. Retain its source-grounded content, loading, insufficient-evidence, and failure states. Its loading and failure never block deterministic evidence. Avoid spatial copy such as “results below” when results now appear above.

Put the complete returned three-hour forecast, additional ECCC observations, nearby construction events, detailed source statuses, and secondary context in supporting sections collapsed by default. Keep primary stale/unavailable warnings visible without requiring expansion. Retain access to existing DriveBC findings and their map interactions without giving empty DriveBC content large primary space. Deferred Transit Mode must not occupy a large empty content section; do not enable transit or redesign the retained controls.

Collapsible sections and camera navigation must be keyboard operable, expose their state and accessible names, and preserve readable content, attribution, and focus. Preserve the existing dark style. No mobile feature expansion is implied by responsive stacking.

## Lifecycle and accepted safeguards

| Trigger | Presentation and lifecycle |
|---|---|
| Initial load | Stage 1 guidance and map; no pre-analysis AI placeholder. |
| Find Routes, including from Stage 2 | Immediately return to Stage 1, invalidate prior analysis using existing cancellation/identity guards, then show route loading/results/errors. |
| Valid Analyze Journey | Immediately enter Stage 2 with independent loading states and perform the one-time viewport adjustment; show camera imagery and deterministic results as their existing requests settle. |
| Invalid Analyze Journey | Preserve validation/disabled behavior; create no attempt or requests. |
| Journey inputs edited or selected route changed | Inputs remain editable in Stage 2. Preserve existing invalidation and cancellation; return to Stage 1 so stale evidence is not presented as current. |
| Analysis failure or partial source failure | Keep Stage 2 feedback and independently available camera evidence; never fabricate weather or road success. Allow existing retry behavior. |
| Later camera/briefing completion | Update only the matching active attempt; never restore Stage 2 after invalidation or dispatch another briefing. |

During Stage 2, keep origin/destination editable and Find Routes available; invoking it returns to Stage 1 and invalidates prior analysis through existing safeguards. Analyze Journey must preserve its current loading/disabled and validation behavior and must not create a duplicate logical attempt on repeated clicks while that analysis is active. Do not add a new journey-locking system. Camera navigation, map interactions, and supporting sections stay usable while AI inference is pending; briefing completion or failure is never a prerequisite for changing journeys. Preserve USER-001 UUID v4 identity per logical Analyze attempt and numeric lifecycle guards. Preserve USER-002's camera opportunity measured from inference initiation with the inclusive 15-second cutoff: timely settlement remains eligible even if analysis finishes later; late evidence cannot alter the single frozen briefing snapshot. Retain the independent 70-second camera deadline, 30-second backend and 35-second frontend briefing deadlines, cancellation, request identity checks, and at most one briefing dispatch per logical attempt. Stage changes, direction navigation, and section expansion must not create attempts or provider calls.

The analysis API currently delivers roads and weather together; this UX does not require streaming or splitting that response. Camera imagery is independently available. Reuse existing components, normalized data, evidence bundle, and orchestration; summary filtering must not truncate or alter the evidence sent to the existing briefing.

## Implementation boundaries and verification

No backend changes, new sources, API/normalized contract changes, new inference, dependencies, infrastructure, authentication, tracking, or deployment. Do not modify model, prompt, provider routing, budget ledgers, quotas, or paid controls. QAR-1 aggregate accounting and QAR-2 offline test isolation remain intact.

Alpha-UX-1 covers stage transitions and primary summary. Existing supporting content may remain below the summary as an interim arrangement; the final map/events composition, Experimental placement, and disclosure organization belong to separately authorized Alpha-UX-2. Completion of the first slice is not completion of Alpha UX v1.

Future verification uses deterministic fixtures and mocked transports only, with no external requests or paid inference. Cover transitions/invalidation, independent completion/failure orders, variable camera counts, missing forecast intervals, station eligibility, qualified road counts, UUID/timing/one-dispatch regressions, and final map/disclosure interactions. Human visual review owns desktop proportions, responsive readability, and acceptance; automated checks do not establish visual acceptance. Detailed slice criteria are in [BUILD_PLAN.md](../BUILD_PLAN.md).

## Baseline observations

At checkpoint `40df498`, `App.tsx` owns controls, route selection, briefing presentation, and orchestration in a persistent map/sidebar shell. `DestinationCameraPanel` renders all views; `DestinationWeatherPanel` renders the full forecast and all stations; `RoadAheadPanel` combines direct/nearby findings and source statuses. Existing camera panel tests assert multiple simultaneous images and must be revised during Alpha-UX-1. Existing weather tests protect timestamps, missing values, and provenance; briefing/evidence tests protect UUIDs, cancellation, cutoff timing, and one dispatch. These are implementation considerations, not authorization to edit source/tests now.
