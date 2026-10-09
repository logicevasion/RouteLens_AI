# RouteLens AI — Product Requirements Document

## 1. Purpose

RouteLens AI is a desktop web application that enriches an already-planned journey **into the City of Vancouver** with current public city telemetry.

Navigation applications such as Google Maps are already effective at answering:

> How do I get there?

RouteLens focuses on a different question:

> What is happening around my journey that I should know before I leave?

The product combines near-current visual, transportation, road, transit, and environmental information around an approximate journey corridor and destination, then presents the most relevant findings through an interactive map and concise AI-assisted journey briefing.

RouteLens is designed as a **companion to existing navigation tools**, not a replacement for them.

---

# 2. Product Objective

The MVP should allow a user preparing to travel into Vancouver to quickly understand current conditions relevant to their journey.

The application should help answer questions such as:

- Is it actually raining near my destination right now?
- Do recent Vancouver traffic-camera images show wet pavement or poor visibility?
- Is there active construction near the route I plan to take?
- Are there regional road incidents or closures that may affect the journey?
- If I am taking transit, are there current service alerts relevant to the buses or SkyTrain lines I intend to use?
- Are conditions expected to change materially in the near term?
- Is there anything unusual enough that I should adjust my expectations before leaving?

The goal is not to expose every available data point.

The goal is to identify and communicate **what matters for this particular journey right now**.

---

# 3. Target User

RouteLens is intended broadly for people travelling **into the City of Vancouver** from elsewhere in Vancouver or the surrounding Metro Vancouver / Lower Mainland region.

Potential users include:

- local residents;
- commuters;
- people travelling into Vancouver for appointments or events;
- visitors already using another navigation application;
- drivers;
- transit riders.

The primary first-user scenario is a local person preparing to leave for a destination in Vancouver and wanting a quick check of current conditions.

---

# 4. Core User Problem

Useful current information about Vancouver is fragmented across multiple systems.

A traveller may separately check:

- a navigation application;
- a weather application;
- street cameras;
- road-construction information;
- regional road incident information;
- transit alerts.

RouteLens should reduce that fragmentation.

Rather than requiring the user to manually inspect several sources, RouteLens gathers relevant telemetry around the journey and presents a concise interpretation.

---

# 5. Core Product Thesis

The central product principle is:

> **The route guides relevance; the telemetry provides the value.**

RouteLens does not need to reproduce the user's exact navigation route.

Instead, it provides one or more approximate journey corridors and asks the user to select the option that most closely resembles the journey they already intend to take.

That corridor is then used to prioritize geographic telemetry.

For Transit mode, geographic route context is supplemented by explicit user-selected transit services so that service advisories can be matched using authoritative transit identifiers rather than geography alone.

The user remains responsible for actual navigation through their preferred navigation application.

---

# 6. Geographic Scope

## 6.1 Origin

The origin may be broadly within Metro Vancouver / the Lower Mainland.

Examples include:

- Vancouver
- Burnaby
- New Westminster
- Richmond
- Surrey
- Coquitlam
- North Vancouver
- West Vancouver

The MVP does not require a perfectly defined administrative origin boundary.

The goal is to support realistic journeys into Vancouver from nearby municipalities.

## 6.2 Destination

The destination must be located within the **City of Vancouver**.

If the user selects a destination outside the supported area, RouteLens should clearly block analysis and explain that the MVP currently supports journeys into Vancouver.

Example:

> RouteLens currently analyzes journeys with destinations inside the City of Vancouver.

## 6.3 Trips Out of Vancouver

Journeys whose destination is outside Vancouver are explicitly unsupported in the MVP.

---

# 7. Supported Travel Modes

The MVP supports:

- **Drive**
- **Transit**

Walking and cycling are out of scope.

The selected travel mode changes which sources and insights are emphasized.

---

# 8. Usage Model

RouteLens is an **on-demand, near-departure tool**.

The intended behavior is:

1. the user plans a journey using their normal workflow;
2. shortly before leaving, they open RouteLens;
3. they enter the trip;
4. RouteLens checks current and near-term conditions.

RouteLens is not intended to be used primarily for trips planned many hours or days in advance.

There are no:

- saved journeys;
- recurring monitors;
- background alerts;
- user accounts;
- persistent personal profiles

in the MVP.

---

# 9. Core User Flow

The MVP flow is:

1. User opens RouteLens.
2. User enters an origin.
3. User selects a valid origin from autocomplete results.
4. User enters a destination.
5. User selects a valid Vancouver destination from autocomplete results.
6. User selects:
   - Drive
   - Transit
7. RouteLens generates an approximate journey corridor or candidate corridors.
8. The user selects the corridor that most closely resembles their planned journey.
9. If Transit mode is selected, the user adds the bus routes and/or SkyTrain lines they intend to use, in journey order, with direction where useful.
10. RouteLens gathers relevant current telemetry.
11. Deterministic application logic determines which data is geographically, temporally, or service-specifically relevant.
12. RouteLens automatically selects the nearest usable Vancouver camera intersection to the destination.
13. RouteLens retrieves all usable directional views from that intersection and performs one combined multimodal assessment.
14. RouteLens presents:
    - current destination conditions;
    - route-related construction and closures;
    - regional road incidents;
    - Vancouver camera observations;
    - measured weather observations;
    - current and near-term forecast conditions;
    - relevant transit service alerts when applicable;
    - a concise AI-assisted journey briefing.
15. User may manually explore nearby geographic telemetry on the map.

---

# 10. Origin and Destination Entry

Both origin and destination should use autocomplete/place selection.

The interaction should feel familiar to users of mainstream map applications.

Example:

```text
From:
[ New Westminster Sta... ]

New Westminster Station
New Westminster, BC
...
```

The user must select a recognized result rather than relying entirely on arbitrary free text.

Current-location permissions are not required in the MVP.

Users always enter/select their origin manually.

---

# 11. Route Selection Philosophy

RouteLens should not claim that its displayed route is the exact route the user will take.

For driving journeys, RouteLens may present approximately 1–3 plausible candidate routes.

The UI should ask something like:

> **Which route most closely matches your planned trip?**

The user selects the closest match.

The application should not frame these as:

- recommended routes;
- optimal routes;
- authoritative directions.

The user's normal navigation application remains responsible for actual routing.

---

# 12. Driving Journey Behavior

For a driving journey:

1. origin and destination are selected;
2. RouteLens obtains plausible driving corridors;
3. the user selects the corridor closest to their intended journey;
4. telemetry is prioritized around that corridor.

Relevant information may include:

- Vancouver Road Ahead construction and closures;
- DriveBC Open511 incidents and advisories;
- Vancouver traffic-camera observations;
- measured weather observations;
- current and near-term forecast information.

Driving mode should place stronger emphasis on road-related disruptions.

---

# 13. Transit Journey Behavior

RouteLens does **not** attempt to reconstruct an exact transit itinerary.

It does not need to tell the user:

- which SkyTrain to board;
- which bus to take;
- where to transfer;
- when to exit;
- exact arrival times for each leg.

Those functions remain the responsibility of dedicated navigation/transit applications.

Instead, Transit mode uses two forms of context:

## 13.1 Geographic Journey Context

The approximate selected journey corridor is still used for:

- road events;
- construction;
- weather;
- destination camera conditions.

This route is contextual and does not claim to reproduce the true transit itinerary.

## 13.2 Transit Service Context

The user explicitly selects the transit services they expect to use.

These may include:

- one or more bus routes;
- one or more SkyTrain lines;
- multiple ordered transit legs.

Where useful, the user also selects a passenger-friendly direction or destination.

RouteLens uses the corresponding official transit identifiers to determine whether realtime service alerts may apply.

Core principle:

> **Transit service relevance is determined primarily from GTFS identifiers, not from geographic route proximity alone.**

---

# 14. Transit Service Selection

The Transit-mode UI should allow users to build an ordered list of intended transit legs.

Example:

```text
Leg 1
R5 Hastings
Toward Downtown Vancouver

Leg 2
Expo Line

Leg 3
Bus 172
Selected destination/direction
```

The UI should favor human-readable labels such as:

> Toward UBC

rather than exposing raw transit identifiers or numeric direction IDs.

Internally, RouteLens should preserve the official identifiers associated with each user selection.

The MVP does not require users to select exact boarding or exiting stops.

---

# 15. Transit Alert Scope

The MVP uses **TransLink Service Alerts** as its realtime transit-disruption source.

RouteLens should identify alerts that may apply to the user's selected services.

Relevant alert scopes may include:

- route-wide;
- direction-specific;
- stop-specific;
- trip-specific.

The application must preserve these distinctions.

Examples:

- an alert for a selected route and selected direction is strongly relevant;
- an alert for a route without a direction restriction may apply to either direction;
- an alert affecting only a specific stop must not automatically be described as a line-wide disruption;
- an alert explicitly affecting only the opposite direction should not be treated as a match on that basis;
- a trip-specific notice should not be assumed applicable unless RouteLens has enough information to establish that.

RouteLens should not turn ambiguous service advisories into unsupported claims of delay.

---

# 16. Route Visibility Principle

The selected route only prioritizes automated geographic insights.

It must **not hide nearby geographic telemetry from the user**.

For example:

- route-relevant road events may be visually emphasized;
- regional road events may still remain visible elsewhere on the map.

This allows RouteLens to remain useful when:

- the approximate route differs from the user's real route;
- the user wants to inspect another street or area;
- a regional road event provides useful surrounding context.

Core principle:

> **The route guides prioritization; it does not restrict visibility.**

Transit alert information is an exception to this map-centric model: it is primarily briefing information and does not require transit map overlays in the MVP.

---

# 17. Core MVP Data Sources

The MVP has six core external information-source groups:

1. Vancouver Traffic Webcams
2. Vancouver Road Ahead
3. DriveBC Open511
4. Environment and Climate Change Canada GeoMet / SWOB
5. TransLink GTFS Static + GTFS-Realtime Service Alerts
6. OpenWeather

DriveBC Cameras are explicitly deferred from the MVP.

---

# 18. Vancouver Traffic Webcams

Vancouver public traffic cameras provide near-current visual conditions near the destination.

These cameras are one of the most important sources in RouteLens.

Primary uses include:

- observing whether precipitation appears visibly present;
- identifying wet or dry-looking pavement;
- understanding approximate visibility;
- observing fog, haze, glare, or poor image conditions;
- providing current visual context near the destination.

The MVP does **not** need to analyze many camera intersections along the journey.

Instead, RouteLens should automatically select:

> **one nearest usable Vancouver camera intersection to the destination**

and use all available directional views from that intersection.

---

# 19. Destination Camera Selection

RouteLens should identify the nearest usable camera intersection to the destination.

A camera intersection is considered usable when RouteLens can retrieve one or more valid current directional images.

Expected behavior:

1. find nearby Vancouver camera intersections;
2. choose the nearest candidate;
3. verify that usable current images are available;
4. if not, try the next-nearest candidate;
5. select one usable intersection.

The MVP does not require automatic analysis of multiple camera intersections.

---

# 20. Multi-View Camera Assessment

A selected Vancouver camera intersection may expose multiple directional views.

Typical examples include:

- north-facing;
- south-facing;
- east-facing;
- west-facing.

RouteLens should retrieve all available usable views from the selected intersection and perform:

> **one combined multimodal assessment**

rather than making separate AI calls for every direction.

This allows the AI to use multiple perspectives of the same local conditions while controlling latency and cost.

---

# 21. Camera AI Responsibilities

The camera assessment should focus on directly observable conditions such as:

- visible falling rain or snow where discernible;
- wet or dry-looking pavement;
- visibility;
- fog or haze;
- image quality limitations;
- uncertainty caused by glare, obstruction, resolution, or camera angle.

The model should distinguish observation from inference.

Examples:

> Wet pavement is visible.

is acceptable when supported by the image.

> It is definitely raining.

is not acceptable solely because the roadway is wet.

Likewise:

> No falling rain is visible.

must not automatically become:

> It is not raining.

---

# 22. Camera Image Storage Policy

Camera imagery is ephemeral for the MVP.

Locked behavior:

- fetch current images on demand;
- temporarily cache them as needed for display and inference;
- overwrite or discard them after refresh;
- do not build a historical camera archive;
- do not repeatedly poll cameras to create a time series for a single journey;
- derived AI observations and metadata may be retained where useful.

AI image upscaling is not required for the MVP because generated visual detail could reduce observational trustworthiness.

---

# 23. No Usable Camera Behavior

A usable destination camera may not always be available.

In that case RouteLens should still provide:

- ECCC measured weather;
- OpenWeather current/near-term weather;
- road incidents;
- construction;
- transit information when applicable;
- general journey briefing.

The UI should clearly indicate that no suitable visual observation was available.

The overall journey analysis must not fail solely because camera imagery is unavailable.

---

# 24. Vancouver Road Ahead

Vancouver Road Ahead provides municipal construction and road-restriction information.

The MVP uses both:

- **Current Road Closures**
- **Projects Under Construction**

Relevant information may include:

- construction;
- road closures;
- restrictions;
- affected road segments;
- project information;
- operating schedules or exceptions where available.

RouteLens should use the actual road geometry to determine geographic relevance.

---

# 25. Road Ahead Relevance

Road Ahead information serves two product purposes:

## Map Context

Relevant municipal construction and closure geometry should appear on the map.

## Journey Interpretation

Events that directly overlap or are meaningfully near the selected route may be candidates for the journey briefing.

An important product rule is:

> **All direct route overlaps must be preserved before limiting the number of additional nearby events.**

RouteLens should not discard directly intersecting road restrictions simply because many are present.

---

# 26. Road Ahead Detail Context

Short Road Ahead dataset records may not contain enough information to determine whether a restriction applies during the user's journey.

Where additional source detail is available for a geographically relevant event, RouteLens may use it to improve understanding of:

- full project/location description;
- status;
- work schedule;
- operating hours;
- exceptions;
- type of road restriction.

RouteLens must not assume that a short completion-date field alone proves an event has ended.

Likewise, a broad event status alone must not be interpreted as proof that a restriction is active at the current moment.

Missing schedule details should remain unknown.

---

# 27. DriveBC Open511

DriveBC Open511 provides regional road-event information.

Potentially relevant information includes:

- traffic incidents;
- closures;
- construction;
- road restrictions;
- maintenance;
- weather-related road conditions;
- special events and advisories.

This source provides broader Lower Mainland context beyond Vancouver municipal data.

---

# 28. Open511 Regional Map Context

DriveBC Open511 should serve both:

- the overall regional map;
- journey-specific relevance assessment.

RouteLens may display active Open511 events throughout the supported regional area even when they are not part of the selected journey briefing.

This supports situational awareness without requiring the application to refetch all events whenever the user selects a different route.

---

# 29. Open511 Journey Relevance

An Open511 event being geographically close to the selected route does not automatically prove that it affects the journey.

Where the source provides enough information, RouteLens should consider:

- route overlap or proximity;
- affected travel direction;
- event schedule;
- current temporal applicability;
- severity;
- event type;
- source description.

An event marked active may still describe a future scheduled restriction.

RouteLens should not overstate applicability.

---

# 30. Cross-Source Road Events

Road Ahead and DriveBC Open511 may sometimes describe overlapping or related road activity.

The MVP does not require sophisticated cross-source deduplication.

When uncertain, it is preferable to preserve two clearly attributed events rather than incorrectly merge distinct events into one.

---

# 31. ECCC GeoMet / SWOB

ECCC SWOB provides physical weather-station observations.

Its role is to provide **measured weather evidence** that complements:

- OpenWeather;
- Vancouver camera observations.

Potentially useful measurements include:

- temperature;
- recent precipitation accumulation;
- wind where available;
- visibility where available;
- snow depth where available;
- station coordinates;
- observation timestamps.

SWOB should not be treated as a hyperlocal weather map.

---

# 32. SWOB Interpretation

SWOB coverage around Vancouver is sparse and uneven.

Therefore:

- the nearest station is not automatically representative of the destination;
- zero precipitation at one station does not prove that another neighborhood is dry;
- recent precipitation accumulation does not prove that precipitation is falling at the current moment;
- missing measurement data does not mean zero;
- RouteLens should not interpolate sparse station readings into neighborhood-level rainfall estimates in the MVP.

When choosing useful SWOB evidence, RouteLens should consider:

- distance;
- observation freshness;
- measurement availability.

The nearest station is not necessarily the most useful station if it lacks the measurement needed for the current question.

---

# 33. OpenWeather

OpenWeather provides structured current and near-term weather information for selected coordinates.

Its role differs from SWOB and camera imagery.

## OpenWeather

Provides:

- structured current weather;
- coordinate-based coverage;
- near-term forecast information.

## SWOB

Provides:

- measured physical weather-station observations.

## Vancouver Cameras

Provide:

- visual evidence near the destination.

These sources are complementary.

RouteLens should not treat them as three identical confirmations of the same fact.

---

# 34. Current Weather vs Forecast Weather

The product must clearly distinguish between:

## Measured Observations

Primarily sourced from:

> ECCC SWOB

Examples:

- measured temperature;
- precipitation accumulation;
- station visibility.

## Structured Current / Near-Term Conditions

Primarily sourced from:

> OpenWeather

Examples may include:

- current temperature;
- current weather classification;
- predicted precipitation;
- near-term changes.

## Visual Observation

Sourced from:

> Vancouver traffic cameras

Examples:

- wet pavement;
- visible falling precipitation;
- fog/haze;
- visibility limitations.

The UI and AI briefing should preserve these evidence categories rather than collapsing them into one unlabeled weather state.

---

# 35. Near-Term Weather Use Case

RouteLens is designed for use near departure time.

The product should focus on current and near-term weather rather than long-range trip planning.

The exact OpenWeather lookahead and sampling strategy will be finalized after API validation.

RouteLens should be especially interested in meaningful changes that may affect a journey beginning soon.

The product does not require a user-entered ETA.

---

# 36. Combining Weather Evidence

RouteLens should combine weather evidence conservatively.

Example:

```text
Camera:
wet roadway visible
no clearly visible falling rain

SWOB:
recent station precipitation = 0 mm

OpenWeather:
light rain forecast near destination
```

A reasonable RouteLens interpretation might be:

> Roads near the destination appear wet, while nearby measured precipitation is limited. Light rain is forecast near the destination, so conditions may be localized or changing.

RouteLens should acknowledge meaningful disagreement between sources rather than forcing an artificial consensus.

---

# 37. TransLink GTFS Static

GTFS Static provides reference data needed to turn user-friendly transit selections into authoritative service identifiers.

For the MVP it supports:

- bus route selection;
- SkyTrain line selection;
- passenger-friendly direction choices.

RouteLens should not expose raw GTFS identifiers directly as the primary UI.

---

# 38. Transit Direction Handling

Bus routes may have multiple scheduled trips and headsigns.

RouteLens should derive user-meaningful direction choices from GTFS data rather than presenting every scheduled trip.

Direction IDs must not be interpreted generically.

For example:

> `direction_id = 0`

does **not** universally mean:

- eastbound;
- inbound;
- downtown;
- northbound.

Direction meaning should be associated with the route's actual trip/headsign information.

---

# 39. TransLink GTFS-Realtime Service Alerts

For the MVP, the only required GTFS-Realtime capability is:

> **Service Alerts**

The following are explicitly deferred:

- Trip Updates;
- Vehicle Positions.

This keeps Transit mode focused on current service disruption and advisory information rather than realtime vehicle tracking or exact delay prediction.

---

# 40. Transit Alert Interpretation

RouteLens should preserve both structured alert metadata and source text.

Not every useful alert has a meaningful standardized effect or cause.

The product should therefore retain:

- alert header;
- description where available;
- active period;
- affected service selectors;
- effect/cause where available;
- source URL where available.

RouteLens must not infer unsupported delays or service impacts solely from incomplete enum fields.

---

# 41. Transit Alert Temporal Applicability

Long-running alerts may remain valid even if their start date is old.

An open-ended active period does not necessarily indicate stale data.

At the same time, a broad active period may not fully express recurring operating hours described in the alert text.

For the MVP:

- preserve structured active periods;
- assess whether the alert is temporally relevant to the intended journey;
- preserve timing qualifications from the source;
- do not make unsupported claims that a restriction applies continuously.

---

# 42. Transit Map Policy

Transit data is primarily used for journey interpretation.

The MVP does **not** require:

- transit-network overlays;
- bus markers;
- train markers;
- realtime vehicle positions;
- station/stop map clutter;
- transfer-path visualization.

The geographic map remains focused on:

- selected journey route;
- Vancouver Road Ahead;
- DriveBC Open511;
- weather context where useful;
- Vancouver cameras.

---

# 43. Destination Conditions

Destination conditions are the highest-priority output of the product.

The user should quickly be able to understand:

> What does it appear to be like at my destination right now?

Destination conditions should prioritize:

1. selected Vancouver camera intersection imagery;
2. structured multi-view camera analysis;
3. current OpenWeather conditions;
4. nearby useful ECCC/SWOB observations;
5. near-term OpenWeather forecast;
6. other highly relevant nearby telemetry.

---

# 44. Along-Route Conditions

RouteLens should surface only noteworthy conditions along or around the selected journey.

Potential findings include:

- active construction;
- road closures;
- road incidents;
- road advisories;
- significant weather conditions;
- relevant camera-derived destination conditions;
- transit service alerts in Transit mode.

The product should not repeat every matching source record in the automated journey summary.

---

# 45. Journey Relevance Principles

Relevance should be established deterministically before information reaches the LLM.

Three important rules apply.

## 45.1 Geographic Proximity Is Not Proof of Impact

A road event near the route may not affect the selected direction.

A nearby weather station may not represent exact destination conditions.

## 45.2 Structured Identifiers Take Precedence Where Appropriate

Transit alert matching should use official GTFS route/direction identifiers rather than an LLM's interpretation of route names or geographic proximity.

## 45.3 Directly Applicable Events Must Not Be Lost to Candidate Limits

Direct route overlaps should remain eligible even when many events exist.

Candidate limits should primarily restrict supplemental nearby information.

---

# 46. Insight Density

The automated journey experience should prioritize approximately:

> **3–6 important findings maximum**

This is a usability constraint.

RouteLens should not become a wall of telemetry.

Additional geographic data may remain accessible through the map.

---

# 47. Journey Timeline

RouteLens should provide a compact journey timeline organized approximately as:

```text
START
  │
  ● noteworthy route issue
  │
  ● regional road condition
  │
  ● significant weather context
  │
DESTINATION
  ● current destination conditions
```

Transit-specific service alerts may also appear where they are sufficiently relevant.

The timeline should summarize only significant findings.

It should not reproduce every map marker.

---

# 48. AI Journey Briefing

Every completed journey analysis should produce a short human-readable briefing.

The briefing should be concise and actionable.

Example:

> **Your journey looks mostly clear.**
>
> Roads near your destination appear wet in recent camera imagery. One construction restriction overlaps the selected route, while no major regional road incident was identified. Light rain remains possible near the destination.

The briefing should not become a long conversational response.

---

# 49. AI Responsibilities

AI has two primary product responsibilities.

## 49.1 Multimodal Camera Interpretation

Analyze the available directional images from one selected Vancouver camera intersection and convert visible evidence into structured observations.

## 49.2 Journey Briefing

Convert already-selected and normalized journey evidence into concise human-readable insight.

---

# 50. Deterministic Responsibilities

AI should **not** perform first-pass data selection or matching.

Conventional application logic should determine:

- route corridor;
- road-event geometry;
- camera location;
- nearest usable camera intersection;
- source freshness;
- event schedule applicability where deterministically available;
- geographic proximity;
- direct route intersection;
- GTFS route and direction matching;
- source identifiers;
- which telemetry qualifies as a briefing candidate;
- which mode-specific sources should be queried.

The LLM interprets selected evidence.

It does not perform:

- raw pagination;
- geometry calculations;
- GTFS joins;
- route-ID resolution;
- source-data scraping;
- first-pass event filtering.

---

# 51. Missing Information Policy

RouteLens must not silently interpret missing values as normal conditions.

Examples:

- missing precipitation is not zero precipitation;
- missing transit direction is not a known direction;
- missing schedule information is not 24-hour applicability;
- missing delay information is not on-time service;
- unavailable camera imagery is not evidence of clear conditions.

Unknown values should remain unknown.

---

# 52. Journey Briefing When Nothing Is Wrong

The journey briefing should always be generated.

If no major issues exist, RouteLens should explicitly communicate that.

Example:

> **Your journey looks clear.**
>
> No significant construction, regional road incidents, or matching transit service alerts were identified. No major weather concern is apparent from the available evidence.

Core principle:

> **No news is good news.**

RouteLens should not manufacture urgency simply because many sources were queried.

---

# 53. Interactive Map

The map is a primary exploration surface.

It should allow the user to see:

- approximate selected journey corridor;
- Vancouver traffic-camera locations where useful;
- Vancouver Road Ahead road geometry;
- DriveBC Open511 regional road events;
- other relevant geographic telemetry.

Users should be able to click relevant map items for more information where practical.

The map should remain useful independently of the automated briefing.

Transit services do not require map visualization in the MVP.

---

# 54. Map and Panel Responsibilities

The product should follow this principle:

> **Map for exploration, panel for interpretation.**

The map answers:

> Where is everything?

The journey panel answers:

> What matters to this trip?

---

# 55. Main Desktop Layout

The MVP is desktop-only.

The primary screen should contain:

## Top

Journey controls:

- origin;
- destination;
- mode;
- Transit service selection when applicable;
- analysis action.

## Left, approximately 65%

Interactive map.

## Right, approximately 35%

Journey intelligence panel.

Conceptually:

```text
┌─────────────────────────────────────────────────────────┐
│ From [...] → To [...]   Mode [Drive]   [Analyze]        │
├───────────────────────────────┬─────────────────────────┤
│                               │ JOURNEY STATUS          │
│                               │                         │
│                               │ DESTINATION CONDITIONS  │
│            MAP                │                         │
│                               │ ALONG YOUR ROUTE        │
│                               │                         │
│                               │ JOURNEY TIMELINE        │
│                               │                         │
│                               │ AI BRIEFING             │
│                               │                         │
│                               │ SOURCES / FRESHNESS     │
└───────────────────────────────┴─────────────────────────┘
```

---

# 56. Right-Panel Information Hierarchy

The locked visual priority is:

1. destination camera / current conditions;
2. overall journey status;
3. route issues;
4. transit alerts where applicable;
5. supporting telemetry / provenance.

The destination-condition experience should be one of the strongest visual elements in the product.

---

# 57. Journey Overview Panel

The normal right-side panel should contain, in order:

1. **Journey Status**
2. **Destination Conditions**
3. **Along Your Route**
4. **Transit Alerts** when applicable
5. **Journey Timeline**
6. **RouteLens AI Briefing**
7. **Sources / Freshness**

Exact grouping may be adjusted for visual clarity.

---

# 58. Camera Detail Presentation

The destination-condition experience should make the selected camera intersection visually prominent.

It should support:

- available directional images;
- intersection name/location;
- image freshness where available;
- structured AI visual observations;
- relevant current weather context.

A dedicated camera-detail state may still be used if helpful, but the MVP does not require alternative camera exploration as a core workflow.

---

# 59. Visual Style

RouteLens should use a polished, dark **city intelligence** aesthetic.

Desired characteristics:

- dark charcoal / deep navy background;
- subdued basemap;
- high-contrast selected route;
- restrained accent colors;
- clean modern typography;
- visually prominent camera images;
- compact telemetry markers;
- small source/freshness badges;
- elevated or glass-like panels where appropriate;
- minimal visual clutter.

The interface should feel like a modern situational-awareness product rather than a municipal open-data dashboard.

---

# 60. Motion and Animation

The MVP should include restrained animation for polish.

Desired behavior includes:

- route visually reveals after analysis;
- result cards fade or slide into place;
- camera panel transitions smoothly where applicable;
- subtle live-status pulse;
- small weather-state animation if straightforward.

Motion should support comprehension rather than becoming decorative noise.

---

# 61. Desktop-Only Requirement

Mobile responsiveness is explicitly out of scope.

The product should be optimized for a large desktop/laptop viewport.

Development effort should not be spent creating:

- mobile navigation;
- compact phone layouts;
- touch-first interactions;
- responsive redesigns

unless necessary to prevent the desktop experience from breaking.

---

# 62. Data Freshness

Because RouteLens focuses on current conditions, freshness must be visible to the user.

Examples:

```text
Camera · image retrieved 4m ago
ECCC · observed 8m ago
DriveBC · updated 3m ago
Road Ahead · dataset fetched 6h ago
Transit · updated 35s ago
```

Users should be able to distinguish:

- recent observations;
- cached source data;
- stale fallback data;
- forecast information.

Stale data should not silently appear current.

---

# 63. Stale-Data Behavior

Where appropriate, RouteLens may continue using the last valid cached source data after a refresh failure.

When this happens:

- the previous valid data may remain available;
- its age must remain visible;
- the application should identify the source as stale;
- the failed refresh should not silently replace valid data with an invalid payload.

Camera imagery follows its separate ephemeral policy.

---

# 64. Data Provenance

The UI and normalized journey evidence should preserve enough provenance for the user and system to understand where important information came from.

Examples:

- City of Vancouver;
- DriveBC;
- ECCC;
- TransLink;
- OpenWeather;
- camera AI inference.

Normalized observations should preserve, where relevant:

- source;
- source record identifier;
- event/observation timestamp;
- retrieval timestamp.

AI-derived observations should be distinguishable from authoritative source data.

---

# 65. Partial Success

Every external data source should be treated as independently fallible.

If one source fails, RouteLens should still return useful results from the remaining sources.

Example:

```text
Vancouver Cameras   Available
Road Ahead          Available
DriveBC Open511     Available
ECCC                Available
OpenWeather         Available
TransLink           Unavailable
```

The user might see:

> TransLink realtime information is currently unavailable. Other journey conditions are shown normally.

One failed source must not cause the entire journey analysis to fail unless that failure truly prevents the basic workflow from continuing.

---

# 66. Error Handling

Errors should be:

- understandable;
- localized;
- non-catastrophic where possible.

Examples include:

- destination outside supported area;
- no route corridor available;
- no usable destination camera;
- upstream API unavailable;
- stale source information;
- AI image analysis unavailable;
- transit alert feed unavailable.

The application should degrade gracefully.

---

# 67. Functional Requirements

The MVP must allow the user to:

## Journey Input

- enter an origin;
- select an origin from autocomplete;
- enter a destination;
- select a destination from autocomplete;
- reject destinations outside Vancouver;
- choose Drive or Transit.

## Route Context

- generate an approximate journey corridor;
- select/accept an approximate corridor;
- view the selected route on the map;
- understand that the corridor is for context rather than authoritative navigation.

## Vancouver Cameras

- select the nearest usable destination camera intersection automatically;
- retrieve available directional images from that intersection;
- receive one combined multimodal analysis across usable views;
- see current visual-condition insight;
- continue receiving a useful journey analysis if no usable camera is available.

## Road Conditions

- view Vancouver Road Ahead construction/closures;
- view active regional DriveBC Open511 events;
- inspect road events spatially on the map;
- preserve directly overlapping road events as briefing candidates;
- use enriched Road Ahead schedule/restriction detail where available.

## Weather

- see structured current and near-term OpenWeather information;
- see relevant measured ECCC/SWOB observations;
- see camera-derived visual weather evidence;
- clearly distinguish measured, forecast/structured, and visually inferred evidence.

## Transit

When Transit mode is selected:

- add one or more bus routes and/or SkyTrain lines;
- select passenger-friendly direction information where useful;
- preserve resolved GTFS identifiers;
- query TransLink Service Alerts;
- match alerts deterministically to selected transit services;
- distinguish route-wide, direction-specific, stop-specific, and trip-specific alert scope;
- surface relevant service advisories without claiming unsupported delays.

## Insights

- receive a concise overall journey status;
- receive approximately 3–6 meaningful automated findings maximum;
- receive a short AI journey briefing;
- receive a “journey looks clear” result where appropriate;
- see uncertainty or limitations when evidence is incomplete.

## Exploration

- inspect regional and route-adjacent geographic telemetry on the map;
- inspect relevant source-derived details.

## Reliability

- receive partial results when individual upstream sources fail;
- see stale-data warnings where cached fallback data is used.

---

# 68. Non-Functional Requirements

## 68.1 Usability

The main journey flow should be understandable without documentation.

The user should quickly understand:

- what to enter;
- what route selection means;
- what Transit service selection means;
- what the map represents;
- what conditions matter.

## 68.2 Responsiveness

The application should feel interactive enough for a near-departure check.

Individual slow external sources should not unnecessarily block all useful results.

## 68.3 Reliability

External API failure should degrade the experience gracefully.

## 68.4 Explainability

Important findings should preserve:

- source;
- freshness;
- applicability/relevance where useful;
- distinction between observation, forecast, source-reported information, and AI inference.

## 68.5 Information Density

The product should prioritize concise useful insight rather than maximum data exposure.

## 68.6 Visual Quality

The MVP should look intentionally designed and presentation-ready.

Visual polish is a product requirement, not merely post-MVP cleanup.

## 68.7 Data Integrity

Missing, stale, ambiguous, or unavailable values should not silently be converted into false certainty.

---

# 69. Success Criteria / Definition of Done

The MVP is considered successful when a user can:

1. select a valid origin;
2. select a valid Vancouver destination;
3. choose Drive or Transit;
4. select or accept an approximate journey corridor;
5. see the route on an interactive map;
6. see relevant Vancouver Road Ahead construction/closure information;
7. see relevant regional DriveBC Open511 events;
8. inspect a selected destination camera intersection when usable imagery exists;
9. receive a multi-view camera-derived visual-condition assessment;
10. see current and near-term OpenWeather information;
11. see relevant measured ECCC/SWOB context;
12. in Transit mode, select the bus routes/SkyTrain lines they intend to use;
13. receive relevant TransLink Service Alerts when applicable;
14. receive a concise journey briefing;
15. see clear uncertainty/source context where appropriate;
16. still receive useful partial results if an individual source fails.

The route does not need to exactly reproduce Google Maps for the MVP to be successful.

---

# 70. Explicit Non-Goals

The MVP does not include:

- exact Google Maps route reproduction;
- turn-by-turn navigation;
- route optimization;
- authoritative route recommendations;
- full transit itinerary reconstruction;
- automatic transit transfer planning;
- bus/train navigation instructions;
- boarding-stop or exiting-stop selection;
- exact transit trip selection;
- GTFS-Realtime Trip Updates;
- GTFS-Realtime Vehicle Positions;
- realtime transit vehicle tracking;
- transit network overlays;
- transit station/stop map visualization;
- natural-language transit itinerary parsing;
- user accounts;
- authentication;
- saved trips;
- persistent user profiles;
- recurring monitoring;
- push notifications;
- current-location permissions;
- mobile UI;
- mobile responsiveness;
- walking mode;
- cycling mode;
- historical city analytics;
- historical camera archive;
- camera time-series analysis;
- multiple Vancouver camera intersections per journey;
- camera-based traffic-speed inference;
- AI image upscaling;
- complex cross-source road-event deduplication;
- weather-station interpolation;
- neighborhood-level weather interpolation;
- DriveBC camera integration;
- citywide traffic simulation;
- citywide digital-twin simulation;
- general journeys whose destination is outside Vancouver;
- long-range travel planning.

---

# 71. Deferred Data Source: DriveBC Cameras

DriveBC camera imagery is explicitly removed from the MVP.

It remains a possible future integration for:

- highway weather context;
- bridge approaches;
- regional visual coverage;
- trips beginning outside Vancouver.

If added later, DriveBC cameras should reuse the existing camera-selection and multimodal-analysis architecture rather than creating a second vision pipeline.

For the MVP, Vancouver cameras are sufficient to demonstrate the camera capability.

---

# 72. Product Boundaries

The product should preserve the following division of responsibility:

```text
Navigation application
→ How do I get there?

RouteLens route corridor
→ Approximately where is my journey happening?

Transit service selection
→ Which buses / SkyTrain lines am I planning to use?

Public telemetry
→ What is happening around that journey or those services?

Deterministic matching
→ Which observations actually appear relevant?

AI
→ How can those selected observations be explained concisely?
```

Implementation should not drift toward making RouteLens a navigation or transit-planning replacement.

---

# 73. Evidence Model

RouteLens should distinguish between different kinds of evidence.

Examples:

## Source-Reported

- road closure;
- construction;
- transit service alert;
- Open511 incident.

## Measured

- SWOB temperature;
- SWOB precipitation accumulation;
- SWOB visibility.

## Forecast / Structured Weather

- OpenWeather forecast conditions;
- predicted precipitation.

## Visually Observed / AI-Derived

- wet pavement visible;
- falling precipitation possibly visible;
- poor visibility;
- camera image quality limitations.

The final briefing should retain these distinctions whenever they affect confidence or interpretation.

---

# 74. MVP Product Summary

RouteLens AI should provide a fast, visually polished answer to:

> **What should I know about my journey into Vancouver before I leave?**

The MVP succeeds by combining:

- an approximate selected journey corridor;
- municipal construction data;
- regional road-event data;
- one nearby multi-view Vancouver camera assessment;
- structured weather;
- measured weather observations;
- and, when Transit is selected, service-specific TransLink alerts.

RouteLens then turns that fragmented information into a small number of understandable, evidence-backed journey insights.

The product should remain:

- Vancouver-specific;
- near-current;
- route-aware;
- service-aware in Transit mode;
- camera-centric at the destination;
- deterministic before AI;
- concise;
- transparent about uncertainty;
- transparent about provenance;
- complementary to existing navigation applications.
