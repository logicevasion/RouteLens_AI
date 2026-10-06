# RouteLens AI

**Public city telemetry, interpreted for your journey.**

RouteLens AI is a Vancouver-focused journey intelligence application that adds real-time context to a trip you are already planning.

Google Maps and other navigation tools are already excellent at answering:

> **How do I get there?**

RouteLens focuses on a different question:

> **What is happening around my journey that I should know before I leave?**

The application combines public city, transportation, environmental, and visual telemetry around an estimated travel corridor into a concise view of current conditions.

Rather than replacing a navigation app, RouteLens acts as a companion to it.

---

## Why RouteLens?

Vancouver is a particularly good environment for this idea.

Weather can vary significantly across relatively short distances. A forecast showing a 50% chance of rain does not necessarily answer whether it is currently dry, drizzling, or pouring at your destination.

At the same time, useful information about the city is spread across multiple systems:

- public street cameras
- construction and road closures
- road incidents
- highway cameras
- observed weather conditions
- transit service information

Individually, these sources are useful.

RouteLens brings them together around a specific journey.

A recent street-camera image near the destination can provide immediate visual evidence of current conditions. Construction and incident data can highlight potential disruptions along the way. Weather observations provide environmental context, while transit data can surface relevant service issues when travelling by public transport.

The result is a focused answer to:

> **What should I know about this trip right now?**

---

## Intended User Flow

RouteLens is designed for **journeys into the City of Vancouver**, with origins potentially elsewhere in Metro Vancouver.

A typical workflow is:

1. Enter a starting point.
2. Enter a Vancouver destination.
3. Select a travel mode:
   - Drive
   - Transit
4. RouteLens generates a small set of estimated route corridors.
5. Select the route that most closely resembles the journey you are already planning.
6. RouteLens gathers relevant public telemetry around that route and destination.
7. The application presents:
   - current destination conditions
   - relevant construction and road events
   - nearby public camera imagery
   - weather observations
   - transit issues when applicable
   - a concise AI-generated journey briefing

RouteLens does **not** attempt to replace turn-by-turn navigation or determine the best route.

The selected route is used primarily as a **relevance filter** for city telemetry.

Users remain free to explore cameras, construction zones, incidents, and other visible information outside the selected corridor directly from the map.

---

## Core Product Idea

RouteLens separates the journey into three contexts:

### Starting Point

What are conditions like where the journey begins?

### Along the Route

Are there noteworthy conditions such as:

- active construction
- road closures
- incidents
- unusual road conditions
- transit disruptions

### Destination

What does the destination actually look and feel like right now?

This is where public camera imagery and current weather observations become especially valuable.

A nearby camera may show:

- visible rain
- wet or dry road surfaces
- reduced visibility
- traffic conditions

These visual observations can then be considered alongside official weather telemetry.

---

## Planned Core Data Sources

The initial RouteLens build is planned around six public data integrations.

### 1. Vancouver Webcams

Public street and traffic camera imagery providing near-current visual conditions, typically refreshed approximately every few minutes.

This is a central RouteLens data source because it provides direct visual evidence of conditions near a destination or journey corridor.

### 2. Vancouver Road Ahead

City of Vancouver information covering:

- active construction
- road closures
- affected streets and road segments

This allows RouteLens to identify municipal work that may be relevant to a selected journey.

### 3. DriveBC Open511

Dynamic road-event information including:

- incidents
- closures
- construction
- maintenance
- road and weather-related events

This extends RouteLens beyond City of Vancouver datasets and helps provide context along approaches into Vancouver.

### 4. DriveBC Cameras

Public highway, bridge, and major-route camera imagery.

These cameras complement Vancouver municipal cameras, particularly for journeys involving major approaches, bridges, or provincial highways.

### 5. Environment and Climate Change Canada GeoMet / SWOB

Current observed environmental conditions from official weather stations.

Relevant observations may include:

- temperature
- precipitation
- humidity
- wind speed
- wind direction
- observation timestamp

These observations provide an authoritative environmental signal that can be combined with nearby camera imagery.

### 6. TransLink GTFS-Realtime

Used when the selected travel mode is **Transit**.

Planned use focuses primarily on:

- service alerts
- trip updates
- delay information

RouteLens is not intended to reproduce full transit navigation or tell users where to transfer or when to get off. Existing navigation applications remain responsible for those tasks.

---

## AI in RouteLens

AI is used as an **interpretation layer**, not as the source of geographic truth.

### Multimodal Camera Analysis

Recent public camera imagery can be analyzed for observable conditions such as:

- apparent precipitation
- wet or dry road surfaces
- visibility
- approximate traffic density

Camera analysis is treated as one source of evidence rather than an authoritative weather measurement.

Where possible, visual observations are considered alongside official environmental telemetry.

### Journey Briefing

Once RouteLens has deterministically gathered and filtered telemetry relevant to the selected journey, an LLM produces a short human-readable briefing.

For example:

> **Your trip looks mostly clear.**
>
> Light rain appears likely near your destination, with wet road surfaces visible on a recent nearby camera. One active construction project is located near the selected corridor. No major DriveBC incidents were identified.

The LLM does not determine which events are geographically relevant.

Route relevance is handled through conventional geospatial logic before data is provided to the model.

---

## Map Experience

The map is intended to remain useful even when the automatically selected journey corridor is only an approximation.

The route guides prioritization.

It does not restrict exploration.

Users can directly inspect nearby:

- camera locations
- camera imagery
- construction zones
- road incidents
- environmental observations

Telemetry considered most relevant to the selected journey is emphasized, while nearby information remains available for manual inspection.

This allows RouteLens to remain useful even when a user's actual navigation route differs somewhat from the estimated route shown in the application.

---

## Planned Interface

RouteLens uses a desktop-first, dark **city intelligence** visual style.

The primary interface is divided into three areas:

### Journey Input

A compact control area for:

- origin
- destination
- travel mode
- journey analysis

Address and place inputs are planned to use autocomplete to simplify Metro Vancouver location selection.

### Interactive Map

The main map displays:

- estimated journey corridor
- public cameras
- construction
- incidents
- other relevant telemetry

Telemetry directly relevant to the selected journey is visually emphasized.

### Journey Intelligence Panel

The side panel prioritizes:

1. destination camera and current conditions
2. overall journey status
3. important route issues
4. journey timeline
5. AI journey briefing
6. source provenance and freshness

Selecting a camera transitions the panel into a dedicated camera-detail view containing a larger image and current-condition analysis.

---

## Journey Timeline

A compact journey timeline provides a second way to understand the trip:

```text
START
  │
  ● Current conditions
  │
  ● Construction / incident
  │
  ● Relevant camera
  │
DESTINATION
  ● Current camera + weather conditions
```

The timeline is intentionally selective.

Only a small number of noteworthy events are surfaced automatically so that RouteLens remains an insight tool rather than a raw telemetry dashboard.

---

## Design Principles

### Navigation Is Not the Product

RouteLens does not attempt to outperform Google Maps, Apple Maps, Waze, or dedicated transit applications.

Those products determine how to get somewhere.

RouteLens enriches the journey with public city-state information.

### The Route Is an Estimate

The selected route is primarily used to identify which telemetry is likely relevant.

Users choose the candidate corridor that most closely resembles their planned journey.

Exact navigation remains the responsibility of the user's preferred navigation application.

### No News Is Good News

RouteLens should not create noise merely because many APIs are available.

If no significant conditions are found, the appropriate result may simply be:

> **Your journey looks clear. No significant construction, incidents, or transit disruptions were identified.**

### Current Conditions Matter

Data freshness is treated as an important part of the result.

Where possible, RouteLens displays how recently information was:

- observed
- captured
- reported
- updated

### Partial Success Is Better Than Total Failure

External public-data services may occasionally be unavailable.

RouteLens is designed so that one unavailable source does not invalidate the entire journey analysis.

Other available data should still be presented.

### Map for Exploration, Panel for Interpretation

The map answers:

> **Where is everything?**

The journey panel answers:

> **What matters to me?**

---

## Data Provenance and Usage

RouteLens relies on public and open-government information from multiple organizations.

Data provenance is treated as part of the application rather than hidden implementation detail.

Where applicable, RouteLens aims to preserve:

- original source
- observation or update timestamp
- attribution requirements
- data freshness
- distinction between reported, observed, and AI-inferred information

Core government datasets are reviewed for applicable usage rights before being treated as application dependencies.

Public accessibility alone is not assumed to imply unrestricted reuse.

Camera imagery is treated separately from camera metadata, and source-specific usage terms remain relevant when determining how imagery may be fetched, processed, stored, or redistributed.

---

## Current Status

RouteLens AI is currently in active development.

The data integrations described above represent the **planned core implementation** and should not be interpreted as completed integrations until reflected in the codebase.

Implementation status will be updated as development progresses.

---

## Demo

> **TODO:** Add live demo link and demonstration video.

---

## Screenshots

> **TODO:** Add RouteLens journey overview, map, destination camera analysis, and journey briefing screenshots.

---

## Technology

Implementation details will be documented as development progresses.

The project is expected to use a lightweight web architecture built around:

- a Python API backend
- a browser-based TypeScript frontend
- interactive geospatial visualization
- local lightweight persistence
- geospatial relevance filtering
- external public-data adapters
- multimodal and text LLM APIs

The emphasis is on a small, understandable architecture appropriate for rapidly integrating heterogeneous public telemetry.

---

## Project Scope

The initial scope is intentionally narrow:

> **Provide current public-data insights for journeys into Vancouver.**

RouteLens is not currently intended to become:

- a full navigation platform
- a turn-by-turn directions system
- a traffic-routing optimizer
- a citywide simulation
- a general-purpose municipal dashboard

Additional telemetry sources or broader functionality will only be considered where they materially improve the core journey-intelligence experience.

---

## Summary

RouteLens AI explores a simple idea:

> **Google Maps is already good at telling you how to get somewhere. What happens when Vancouver's public real-time data is layered around the journey you're already planning?**

By combining current camera imagery, roadwork, road incidents, environmental observations, and transit information, RouteLens aims to turn fragmented public telemetry into a concise understanding of what a traveller can expect before heading into Vancouver.
