# RouteLens AI — Product Requirements Document

## 1. Purpose

RouteLens AI is a desktop web application that enriches an already-planned journey **into the City of Vancouver** with current public city telemetry.

Navigation applications such as Google Maps are already effective at answering:

> How do I get there?

RouteLens focuses on a different question:

> What is happening around my journey that I should know before I leave?

The product combines near-current visual, transportation, road, and environmental information around an approximate journey corridor and destination, then presents the most relevant findings through an interactive map and concise AI-assisted journey briefing.

RouteLens is designed as a **companion to existing navigation tools**, not a replacement for them.

---

# 2. Product Objective

The MVP should allow a user preparing to travel into Vancouver to quickly understand current conditions relevant to their journey.

The application should help answer questions such as:

- Is it actually raining near my destination right now?
- Do recent street-camera images show wet roads or poor visibility?
- Is there active construction near the route I plan to take?
- Are there road incidents or closures that may affect the journey?
- If I am taking transit, are there current service disruptions or delays worth knowing about?
- Are conditions expected to change materially in the near term?
- Is there anything unusual enough that I should adjust my expectations before leaving?

The goal is not to expose every available data point.

The goal is to identify and communicate **what matters for this particular journey right now**.

---

# 3. Target User

RouteLens is intended broadly for people travelling **into the City of Vancouver** from elsewhere in Vancouver or the surrounding Metro Vancouver / Lower Mainland region.

Potential users include:

- local residents
- commuters
- people travelling into Vancouver for appointments or events
- visitors already using another navigation application
- drivers
- transit riders

The primary first-user scenario is a local person preparing to leave for a destination in Vancouver and wanting a quick check of current conditions.

---

# 4. Core User Problem

Useful current information about Vancouver is fragmented across multiple systems.

A traveller may separately check:

- a navigation application
- a weather application
- street cameras
- road-construction information
- road incident information
- transit alerts

RouteLens should reduce that fragmentation.

Rather than requiring the user to manually inspect several sources, RouteLens gathers relevant telemetry around the journey and presents a concise interpretation.

---

# 5. Core Product Thesis

The central product principle is:

> **The route guides relevance; the telemetry provides the value.**

RouteLens does not need to reproduce the user's exact navigation route.

Instead, it provides one or more approximate journey corridors and asks the user to select the option that most closely resembles the journey they already intend to take.

That corridor is then used to prioritize public telemetry.

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

- saved journeys
- recurring monitors
- background alerts
- user accounts
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
8. Where appropriate, the user selects the corridor that most closely resembles their planned journey.
9. RouteLens gathers relevant current telemetry.
10. RouteLens determines which information is geographically and contextually relevant.
11. RouteLens automatically analyzes the primary destination camera where available.
12. RouteLens presents:
    - current destination conditions
    - route-related construction/incidents
    - relevant cameras
    - observed weather
    - near-term forecast
    - transit disruption information when applicable
    - a concise AI-assisted journey briefing
13. User may manually explore nearby telemetry on the map.
14. User may select another camera for detailed visual analysis.

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

- recommended routes
- optimal routes
- authoritative directions

The user's normal navigation application remains responsible for actual routing.

---

# 12. Driving Journey Behavior

For a driving journey:

1. origin and destination are selected;
2. RouteLens obtains plausible driving corridors;
3. the user selects the corridor closest to their intended journey;
4. telemetry is prioritized around that corridor.

Relevant information may include:

- construction
- road closures
- incidents
- Vancouver cameras
- DriveBC cameras where applicable
- weather observations
- near-term forecast information

Driving mode should place stronger emphasis on road-related disruptions.

---

# 13. Transit Journey Behavior

RouteLens does **not** attempt to reconstruct an exact transit itinerary.

It does not need to tell the user:

- which SkyTrain to board
- which bus to take
- where to transfer
- when to exit
- exact arrival times for each leg

Those functions remain the responsibility of dedicated navigation/transit applications.

Transit journeys still use an approximate journey corridor for geographic relevance.

The corridor may be broader than for a driving journey because exact route geometry is less authoritative.

Transit mode should additionally include relevant realtime TransLink information such as:

- service alerts
- delays
- trip disruptions
- other current transit issues likely to affect the journey

The exact method for determining transit relevance may be refined through testing.

---

# 14. Route Visibility Principle

The selected route only prioritizes automated insights.

It must **not hide nearby telemetry from the user**.

The map should continue to expose relevant nearby information outside the exact route corridor.

For example:

- route-relevant telemetry may be visually emphasized;
- nearby telemetry may remain visible but visually muted.

This allows RouteLens to remain useful when:

- the approximate route differs from the user's real route;
- the user wants to inspect another street or area;
- the user wants to manually inspect another camera.

Core principle:

> **The route guides prioritization; it does not restrict visibility.**

---

# 15. Core Data Sources

The MVP has seven planned core external information sources.

---

## 15.1 Vancouver Webcams

Vancouver public street/traffic cameras provide near-current visual conditions.

These cameras are one of the most important sources in RouteLens.

Primary uses include:

- seeing whether precipitation is visibly occurring;
- identifying wet or dry road surfaces;
- understanding approximate visibility;
- visually inspecting traffic conditions;
- inspecting current conditions near the destination.

RouteLens should show relevant Vancouver webcams by default around the destination and selected journey area.

---

## 15.2 Vancouver Road Ahead

Vancouver Road Ahead provides current information about:

- active construction
- road closures
- affected streets
- affected road segments

RouteLens should use this information to identify construction and closures that may matter to the selected journey.

Relevant construction should be visible on the map and may appear in the journey briefing or timeline.

---

## 15.3 DriveBC Open511

DriveBC Open511 provides dynamic road-event information.

Potentially relevant information includes:

- incidents
- closures
- construction
- maintenance
- weather-related road events
- other road disruptions

This source is especially useful for journey segments approaching Vancouver from surrounding municipalities.

---

## 15.4 DriveBC Cameras

DriveBC cameras provide current visual conditions on:

- highways
- bridges
- major provincial roads
- major Vancouver approaches

These cameras should be surfaced only where geographically relevant to the journey.

They should not clutter the map by default.

Typical relevant scenarios include journeys involving:

- Highway 1
- Highway 99
- bridge approaches
- North Shore approaches
- other major regional corridors

---

## 15.5 Environment and Climate Change Canada GeoMet / SWOB

ECCC SWOB provides current observed weather and environmental conditions.

Relevant information may include:

- temperature
- precipitation
- humidity
- wind speed
- wind direction
- observation timestamp

SWOB should provide the primary authoritative current-weather observation layer.

It should complement, not replace, camera imagery.

---

## 15.6 TransLink GTFS-Realtime

TransLink realtime information is used when:

> `mode = transit`

The MVP should primarily use:

- service alerts
- delay/trip-update information
- current disruption information

RouteLens does not need to animate vehicles or reproduce full transit navigation.

---

## 15.7 OpenWeatherMap

OpenWeatherMap provides simple near-term forecast information.

Its role is distinct from ECCC SWOB.

### SWOB

Answers:

> What has actually been observed recently?

### OpenWeatherMap

Answers:

> Is anything expected to change materially in the near term?

RouteLens should focus primarily on forecast changes relevant within approximately:

> **30 minutes to 2 hours**

rather than attempting long-range trip planning.

---

# 16. Destination Conditions

Destination conditions are the highest-priority output of the product.

The user should quickly be able to understand:

> What does it appear to be like at my destination right now?

Destination conditions should prioritize:

1. recent nearby camera imagery
2. structured camera analysis
3. current ECCC weather observations
4. near-term OpenWeatherMap forecast
5. other highly relevant nearby telemetry

---

# 17. Camera Selection

RouteLens should automatically identify a small number of useful cameras near the destination.

Expected behavior:

- select one primary destination camera;
- display it prominently;
- display a small number of alternative nearby cameras as thumbnails;
- allow the user to select any visible camera from the map.

The exact ranking method may consider factors such as:

- proximity
- freshness
- geographic usefulness

but implementation details belong in the technical design.

---

# 18. Automatic Primary Camera Analysis

When a journey analysis is performed, RouteLens should automatically analyze the primary destination camera.

The result should provide structured observations such as:

- precipitation visibly present or absent
- likely precipitation type where observable
- road surface wet/dry
- approximate traffic level
- visibility
- confidence
- short observation note

Camera analysis should remain conservative.

The model should describe observable evidence rather than presenting visual interpretation as calibrated meteorological truth.

---

# 19. Alternative Camera Analysis

Alternative nearby cameras do not need to be analyzed automatically.

When the user deliberately selects another camera:

1. RouteLens displays the selected camera;
2. if a sufficiently fresh analysis is unavailable, RouteLens triggers a new multimodal analysis;
3. the user sees the structured visual-condition result.

This reduces unnecessary AI cost and latency.

---

# 20. No Nearby Camera Behavior

A useful destination camera may not always be available.

In that case RouteLens should still provide:

- ECCC observed weather
- OpenWeatherMap near-term forecast
- road incidents
- construction
- transit information when applicable
- general journey briefing

The UI should clearly indicate that no suitable nearby visual observation was available.

The overall journey analysis must not fail solely because a camera is unavailable.

---

# 21. Current Weather vs Forecast Weather

The product must clearly distinguish between:

## Current observed conditions

Primarily sourced from:

> ECCC SWOB

Examples:

- observed temperature
- observed wind
- recent precipitation

## Near-term expected conditions

Primarily sourced from:

> OpenWeatherMap

Examples:

- rain expected within the next hour
- temperature change
- changing conditions within approximately 30 minutes–2 hours

The UI must not blur observations and forecasts into one unlabeled weather state.

---

# 22. Weather Use Case

A key RouteLens use case is Vancouver's highly variable precipitation.

A conventional forecast may say:

> 50% chance of rain

but this does not necessarily answer:

- Is it raining near the destination now?
- Is it drizzle or heavier rain?
- Are roads already wet?
- Are conditions different from the origin?
- Is precipitation expected to begin soon?

RouteLens should combine multiple current signals to provide a more useful interpretation.

Example:

```text
Camera:
wet roadway
possible visible drizzle

SWOB:
recent precipitation observed

Forecast:
light rain expected in the next hour
```

Possible RouteLens interpretation:

> Light rain appears likely near your destination and may continue through the near term.

---

# 23. Along-Route Conditions

RouteLens should surface only noteworthy conditions along the selected corridor.

Potential findings include:

- active construction
- road closure
- road incident
- relevant visual camera condition
- major transit disruption
- significant weather condition

The product should not display every matching data record in the journey summary.

---

# 24. Insight Density

The automated journey experience should prioritize approximately:

> **3–6 important events maximum**

This is a usability constraint.

RouteLens should not become a wall of telemetry.

Additional information can remain accessible through the map.

---

# 25. Journey Timeline

RouteLens should provide a compact journey timeline organized approximately as:

```text
START
  │
  ● relevant origin condition
  │
  ● noteworthy route issue
  │
  ● relevant camera / incident
  │
DESTINATION
  ● current destination conditions
```

The timeline should summarize only significant events.

It should not reproduce every map marker.

---

# 26. AI Journey Briefing

Every completed journey analysis should produce a short human-readable briefing.

The briefing should be concise and actionable.

Example:

> **Your journey looks mostly clear.**
>
> Light rain appears likely near your destination, and recent camera imagery shows wet road surfaces downtown. One construction zone is located near the selected corridor. No major road incidents were identified.

The briefing should not become a long conversational response.

---

# 27. AI Responsibilities

AI has two primary product responsibilities.

## 27.1 Multimodal Camera Interpretation

Analyze camera imagery and convert visible evidence into structured observations.

## 27.2 Journey Briefing

Convert already-selected structured journey evidence into concise human-readable insight.

---

# 28. Deterministic Responsibilities

AI should **not** determine core geographic truth.

Conventional application logic should determine:

- route corridor
- event location
- camera location
- geographic proximity
- route intersection
- source freshness
- which telemetry qualifies as relevant
- which mode-specific sources should be queried

The LLM interprets selected evidence.

It does not decide which citywide data is geographically relevant.

---

# 29. Journey Briefing When Nothing Is Wrong

The journey briefing should always be generated.

If no major issues exist, RouteLens should explicitly communicate that.

Example:

> **Your journey looks clear.**
>
> No significant construction, road incidents, or transit disruptions were identified. Conditions near the destination currently appear dry.

Core principle:

> **No news is good news.**

RouteLens should not manufacture urgency simply because many sources were queried.

---

# 30. Interactive Map

The map is a primary exploration surface.

It should allow the user to see:

- approximate selected journey corridor
- Vancouver cameras
- relevant DriveBC cameras
- construction
- road incidents
- other relevant telemetry

Users should be able to click relevant items for more information.

The map should remain useful independently of the automated briefing.

---

# 31. Map and Panel Responsibilities

The product should follow this principle:

> **Map for exploration, panel for interpretation.**

The map answers:

> Where is everything?

The journey panel answers:

> What matters to this trip?

---

# 32. Main Desktop Layout

The MVP is desktop-only.

The primary screen should contain:

## Top

Journey controls:

- origin
- destination
- mode
- analysis action

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

# 33. Right-Panel Information Hierarchy

The locked visual priority is:

1. destination camera / current conditions
2. overall journey status
3. route issues
4. supporting telemetry / provenance

The destination-condition experience should be one of the strongest visual elements in the product.

---

# 34. Journey Overview Panel

The normal right-side panel should contain, in order:

1. **Journey Status**
2. **Destination Conditions**
3. **Along Your Route**
4. **Journey Timeline**
5. **RouteLens AI Briefing**
6. **Sources / Freshness**

---

# 35. Camera Detail Panel

When the user selects a camera, the journey panel should transition into a dedicated camera-detail state.

The camera-detail view should contain:

- large camera image
- camera name/location
- image freshness/capture time
- AI visual observations
- relevant current weather context where useful
- Back control

The Back control returns to the Journey Overview.

A separate modal is not required.

---

# 36. Visual Style

RouteLens should use a polished, dark **city intelligence** aesthetic.

Desired characteristics:

- dark charcoal / deep navy background
- subdued basemap
- high-contrast selected route
- restrained accent colors
- clean modern typography
- visually prominent camera images
- compact telemetry markers
- small source/freshness badges
- elevated or glass-like panels where appropriate
- minimal visual clutter

The interface should feel like a modern situational-awareness product rather than a municipal open-data dashboard.

---

# 37. Motion and Animation

The MVP should include restrained animation for polish.

Desired behavior includes:

- route visually reveals after analysis
- result cards fade or slide into place
- camera-detail panel transitions smoothly
- subtle live-status pulse
- small weather-state animation if straightforward

Motion should support comprehension rather than becoming decorative noise.

---

# 38. Desktop-Only Requirement

Mobile responsiveness is explicitly out of scope.

The product should be optimized for a large desktop/laptop viewport.

Development effort should not be spent creating:

- mobile navigation
- compact phone layouts
- touch-first interactions
- responsive redesigns

unless necessary to prevent the desktop experience from breaking.

---

# 39. Data Freshness

Because RouteLens focuses on current conditions, freshness must be visible to the user.

Examples:

```text
Camera · captured 4m ago
ECCC · observed 8m ago
DriveBC · updated 3m ago
Road Ahead · updated 42m ago
```

Users should be able to distinguish:

- recent observations
- older observations
- forecast information

Stale data should not silently appear current.

---

# 40. Data Provenance

The UI should preserve enough provenance for the user to understand where important information came from.

Examples:

- City of Vancouver
- DriveBC
- ECCC
- TransLink
- OpenWeatherMap
- camera AI inference

AI-derived observations should be distinguishable from authoritative source data.

---

# 41. Partial Success

Every external data source should be treated as independently fallible.

If one source fails, RouteLens should still return useful results from the remaining sources.

Example:

```text
Vancouver Cameras   Available
Road Ahead          Available
DriveBC             Available
ECCC                 Available
TransLink            Unavailable
Forecast             Available
```

The user might see:

> TransLink realtime information is currently unavailable. Other journey conditions are shown normally.

One failed source must not cause the entire journey analysis to fail unless that failure truly prevents the basic workflow from continuing.

---

# 42. Error Handling

Errors should be:

- understandable
- localized
- non-catastrophic where possible

Examples include:

- destination outside supported area
- no route corridor available
- no nearby camera available
- upstream API unavailable
- stale source information
- AI image analysis unavailable

The application should degrade gracefully.

---

# 43. Functional Requirements

The MVP must allow the user to:

### Journey Input

- enter an origin
- select an origin from autocomplete
- enter a destination
- select a destination from autocomplete
- reject destinations outside Vancouver
- choose Drive or Transit

### Route Context

- generate an approximate journey corridor
- select/accept an approximate corridor
- view the selected route on the map
- understand that the corridor is for context rather than navigation

### Cameras

- view relevant Vancouver cameras
- view relevant DriveBC cameras where applicable
- automatically receive analysis of a primary destination camera
- see alternative destination camera thumbnails
- manually select another camera
- receive on-demand analysis for a selected alternative camera

### Road Conditions

- view relevant Vancouver Road Ahead construction/closures
- view relevant DriveBC road events
- inspect them spatially on the map

### Weather

- see current observed destination weather
- see relevant near-term forecast changes
- clearly distinguish observed and forecast information

### Transit

When Transit mode is selected:

- query relevant TransLink realtime information
- surface service alerts/delays/disruptions where applicable

### Insights

- receive a concise overall journey status
- receive approximately 3–6 meaningful automated findings maximum
- receive a short AI journey briefing
- receive a “journey looks clear” result where appropriate

### Exploration

- inspect nearby map telemetry outside the exact selected route
- manually select information of interest

### Reliability

- receive partial results when individual upstream sources fail

---

# 44. Non-Functional Requirements

## 44.1 Usability

The main journey flow should be understandable without documentation.

The user should quickly understand:

- what to enter
- what route selection means
- what the map represents
- what conditions matter

## 44.2 Responsiveness

The application should feel interactive enough for a near-departure check.

Individual slow external sources should not unnecessarily block all useful results.

## 44.3 Reliability

External API failure should degrade the experience gracefully.

## 44.4 Explainability

Important findings should preserve:

- source
- freshness
- distinction between observation and inference

## 44.5 Information Density

The product should prioritize concise useful insight rather than maximum data exposure.

## 44.6 Visual Quality

The MVP should look intentionally designed and presentation-ready.

Visual polish is a product requirement, not merely post-MVP cleanup.

---

# 45. Success Criteria / Definition of Done

The MVP is considered successful when a user can:

1. select a valid origin;
2. select a valid Vancouver destination;
3. choose Drive or Transit;
4. select or accept an approximate journey corridor;
5. see the route on an interactive map;
6. inspect relevant cameras;
7. receive camera-derived current-condition insight;
8. see relevant construction and road incidents;
9. see current observed weather;
10. see near-term forecast weather;
11. see relevant transit disruption information when applicable;
12. receive a concise journey briefing;
13. explore nearby telemetry manually;
14. still receive useful partial results if an individual source fails.

The route does not need to exactly reproduce Google Maps for the MVP to be successful.

---

# 46. Explicit Non-Goals

The MVP does not include:

- exact Google Maps route reproduction
- turn-by-turn navigation
- route optimization
- authoritative route recommendations
- full transit itinerary reconstruction
- bus/train navigation instructions
- user accounts
- authentication
- saved trips
- persistent user profiles
- recurring monitoring
- push notifications
- current-location permissions
- mobile UI
- mobile responsiveness
- walking mode
- cycling mode
- historical city analytics
- historical camera archive
- citywide traffic simulation
- citywide digital-twin simulation
- general journeys whose destination is outside Vancouver
- long-range travel planning
- long-range weather forecasting

---

# 47. Product Boundaries

The product should preserve the following division of responsibility:

```text
Navigation application
→ How do I get there?

RouteLens route corridor
→ Approximately where is my journey happening?

Public telemetry
→ What is happening around that journey?

AI
→ How can those selected observations be explained concisely?
```

Implementation should not drift toward making RouteLens a navigation replacement.

---

# 48. MVP Product Summary

RouteLens AI should provide a fast, visually polished answer to:

> **What should I know about my journey into Vancouver before I leave?**

The MVP succeeds by combining an approximate journey corridor with current public city telemetry and turning fragmented information into a small number of understandable, evidence-backed insights.

The product should remain:

- Vancouver-specific
- near-current
- route-aware
- camera-centric
- exploratory
- concise
- transparent about its evidence
- complementary to existing navigation applications
