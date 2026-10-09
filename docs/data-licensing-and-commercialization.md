# RouteLens AI — Data Licensing and Commercialization Considerations

## 1. Purpose

This document records the current licensing, attribution, data-retention, and commercialization considerations for external data sources used or considered by RouteLens AI.

It is intended primarily for:

- the human developer;
- future product/commercialization review;
- architectural decision-making;
- provenance and attribution design;
- future legal review if RouteLens moves beyond a portfolio/datathon project.

This document is **engineering and licensing research, not legal advice**.

Terms, pricing, licences, APIs, and provider policies may change. They should be rechecked before public launch or commercialization.

**Original licensing research:** October 7, 2026  
**MVP scope updated:** October 9, 2026

---

# 2. Scope

The main analysis covers the six current RouteLens MVP information-source groups:

1. Vancouver Traffic Webcams
2. Vancouver Road Ahead
3. DriveBC Open511
4. Environment and Climate Change Canada GeoMet / SWOB
5. TransLink GTFS Static + GTFS-Realtime Service Alerts
6. OpenWeather

A separate future/deferred section records sources that are not part of the current MVP:

- DriveBC Cameras
- ECCC weather radar
- Vancouver 311
- Metro Vancouver AirMap
- additional City of Vancouver open-data layers

This document does **not** currently constitute a full terms review of infrastructure/service providers such as:

- MapTiler;
- openrouteservice;
- OpenRouter.

Those services should be reviewed separately before commercial deployment.

---

# 3. Risk Classification

RouteLens uses the following simple classification.

## Green

Clear open-data or similarly permissive reuse posture.

Typically:

- commercial use explicitly permitted;
- modification permitted;
- combination/derivation permitted;
- redistribution permitted subject to attribution;
- no unusual dependence on revocable custom permissions.

Green does not mean:

> no obligations.

Attribution and licence conditions still apply.

## Yellow

Usable, but important terms, limitations, rights ambiguity, commercial conditions, rate limits, or asset-specific restrictions require attention.

A Yellow source may be entirely reasonable for a portfolio/datathon MVP while still deserving review before public deployment or commercialization.

## Red

Use is unsuitable for the intended product without:

- additional permission;
- contractual changes;
- architectural changes;
- or replacement of the source.

No current core RouteLens structured-data source is classified Red.

Certain forms of raw camera-image use could become effectively Red unless adequate rights are established.

---

# 4. Current MVP Licensing Summary

| Source | Risk | Current RouteLens Role | Main Reason |
|---|---|---|---|
| Vancouver Road Ahead | **Green** | Municipal construction and closures | Explicit Open Government Licence – Vancouver |
| Vancouver webcam metadata | **Green** | Camera locations/pages/catalogue | City Open Data material under OGL-Vancouver |
| Vancouver webcam images | **Yellow** | Ephemeral destination visual evidence | Metadata licence does not clearly establish unrestricted rights to linked JPEGs |
| DriveBC Open511 | **Green** | Regional road events | Explicit Open Government Licence – British Columbia |
| ECCC GeoMet / SWOB | **Green** | Measured weather observations | Explicit Open Government Licence – Canada |
| TransLink GTFS Static + Service Alerts | **Yellow** | Transit selection/reference + service alerts | Custom TransLink terms, API approval/key, attribution, usage/commercial conditions |
| OpenWeather | **Yellow** | Structured current and near-term weather | Commercial terms / ODbL, attribution, plan limits, database implications |

Current overall posture:

> **The core structured-data foundation is strong, while the main commercialization attention is concentrated around Vancouver camera imagery, TransLink, and OpenWeather.**

DriveBC camera imagery remains Yellow research but is **not a current MVP dependency**.

---

# 5. City of Vancouver Open Government Licence

The City of Vancouver publishes qualifying open datasets under the **Open Government Licence – Vancouver**.

The licence permits broad lawful reuse of covered information, including commercial use, modification, adaptation, publication, and distribution.

Attribution is required.

This makes properly designated City of Vancouver open datasets strong RouteLens foundations.

Important boundary:

> **The licence applies to information actually offered under that licence. It should not automatically be assumed to cover every externally linked or separately delivered asset.**

That distinction is especially important for webcam imagery.

---

# 6. Vancouver Road Ahead

## Status

**GREEN**

RouteLens uses:

- Current Road Closures;
- Projects Under Construction.

These datasets are part of the City of Vancouver open-data ecosystem and are used under the applicable Open Government Licence – Vancouver framework.

## Planned RouteLens Use

```text
fetch
→ validate
→ cache
→ normalize
→ preserve geometry
→ geospatially match against journey
→ selectively enrich relevant events
→ derive journey context
→ display in application
```

This type of transformation and application use is well aligned with an open-government-data licence.

## Persistence

Reasonable planned uses include:

- raw response caching;
- normalized event persistence;
- derived geospatial relevance;
- selective cached enrichment;
- combination with other RouteLens evidence.

## Detail-Page Enrichment

RouteLens may retrieve additional event detail from Road Ahead pages for geographically relevant events.

Because source-detail pages are used to improve interpretation of the licensed dataset, provenance should be retained.

Before a commercial release, verify whether any detail-page material relied upon is clearly covered by the same open-data licence or other applicable permission.

The MVP should avoid bulk republishing entire webpages.

## Commercialization

No major licensing blocker is currently apparent for the core Road Ahead datasets.

Before commercial release:

- preserve attribution;
- preserve provenance;
- confirm the specific datasets remain OGL-Vancouver;
- review any material dependence on separately published detail-page content.

---

# 7. Vancouver Webcam Metadata

## Status

**GREEN**

The City webcam dataset provides structured information such as:

```text
camera/intersection ID
name
coordinates
camera webpage URL
source metadata
```

RouteLens may use this information to build an enriched local camera catalogue.

## Catalogue Enrichment

The current technical design visits each official camera page to discover actual directional image URLs.

This creates an important distinction:

```text
open dataset metadata
        ↓
official camera page
        ↓
directional JPEG URLs
```

The metadata itself can be treated according to the applicable City open-data licence.

The rights governing the linked images remain a separate question.

## Persistence

The following may reasonably be retained as catalogue data:

- intersection ID;
- coordinates;
- page URL;
- directional labels;
- discovered image URLs;
- catalogue refresh timestamp.

The fact that a URL was discovered does not itself expand the licence governing the linked image.

---

# 8. Vancouver Webcam Images

## Status

**YELLOW**

This remains the most important asset-level rights ambiguity in the active MVP.

The core distinction is:

```text
City open-data record
├── location
├── metadata
└── camera webpage URL
        ↓
directional image assets
        ↓
separate rights question
```

An open-data licence covering metadata does **not automatically establish unrestricted rights to every linked image**.

RouteLens should therefore avoid assuming permission to:

- create a permanent mirror;
- build a historical image archive;
- redistribute JPEGs as a standalone service;
- sell image access;
- train models on a large accumulated image corpus;
- sublicense image collections.

---

# 9. Locked Vancouver Camera Image Policy

The current MVP architecture intentionally reduces the image-rights surface area.

## Raw Images

Treat as:

> **ephemeral / cache-only**

Conceptually:

```text
selected camera intersection
        ↓
fetch current directional views
        ↓
temporary local cache
        ↓
display same images
        ↓
one multimodal assessment
        ↓
derived CameraObservation
        ↓
images later overwritten/discarded
```

No historical archive.

No repeated image time series.

## Multiple Views

The current MVP may temporarily hold several directional images from the same selected intersection.

This does not change the retention policy:

> all current views remain ephemeral.

## Derived Observations

Normalized AI output may be persisted where useful.

Example:

```text
camera_intersection_id
view_ids
analysis_timestamp
precipitation_visible
road_surface
visibility
image_quality
confidence
notes
```

Preserve source provenance.

## Important Caveat

Ephemeral use **reduces risk but does not prove that all processing, proxying, display, or AI analysis rights are granted**.

Before serious public/commercial deployment, image-use rights should be specifically confirmed.

---

# 10. DriveBC Open511

## Status

**GREEN**

DriveBC Open511 information is governed by the **Open Government Licence – British Columbia** according to the source's API documentation.

OGL-BC permits broad reuse of covered information, including commercial use, subject to its conditions and attribution.

## Planned RouteLens Use

```text
regional Open511 events
        ↓
cache
        ↓
normalize into CityEvent
        ↓
regional map
        +
journey-specific deterministic filtering
        ↓
timeline / briefing evidence
```

## Persistence

Reasonable uses include:

- regional API caching;
- normalized event persistence;
- geospatial matching;
- derived relevance;
- combination with Road Ahead and other sources.

## Regional Fetching

RouteLens's decision to cache a regional Open511 dataset rather than query only one route does not fundamentally alter the licensing posture.

It should still:

- respect API terms;
- avoid abusive request patterns;
- preserve attribution;
- retain provenance.

## Commercialization

DriveBC Open511 remains one of RouteLens's strongest potential commercial data foundations.

---

# 11. ECCC GeoMet / SWOB

## Status

**GREEN**

Environment and Climate Change Canada's applicable meteorological-observation data is published under the **Open Government Licence – Canada**.

OGL-Canada permits covered information to be:

- used commercially;
- copied;
- modified;
- adapted;
- published;
- redistributed

subject to applicable licence conditions and attribution.

## Planned RouteLens Use

```text
recent SWOB observations
        ↓
validate
        ↓
group by station
        ↓
select latest useful observations
        ↓
normalize measurements
        ↓
associate with journey/destination
        ↓
weather evidence
```

## Persistence

Reasonable uses include:

- short-lived raw caching;
- normalized observation storage;
- correlation with journey location;
- combination with camera/OpenWeather evidence.

## Data-Quality Consideration

Near-realtime environmental observations may have limitations or incomplete measurements.

This is primarily a provenance/product-quality issue rather than a licensing blocker.

RouteLens should preserve:

- station;
- timestamp;
- measurement semantics;
- missing values.

---

# 12. TransLink GTFS Static + GTFS-Realtime Service Alerts

## Status

**YELLOW**

TransLink is not treated as OGL-style open-government data.

The earlier terms review found a custom TransLink licence/access model with:

- registration/approval requirements;
- API-key access;
- a limited/revocable licence;
- request limits;
- required attribution;
- possible additional commercial conditions.

This makes TransLink usable but architecturally important to isolate.

---

# 13. TransLink MVP Scope

The RouteLens MVP now uses TransLink narrowly.

## GTFS Static

Used for:

- route lookup;
- bus/SkyTrain selection;
- route IDs;
- direction/headsign reference.

## GTFS-Realtime

Used only for:

> **Service Alerts**

Deferred:

- Trip Updates;
- Vehicle Positions;
- exact trip prediction;
- realtime vehicle tracking.

This narrower architecture reduces both technical complexity and the volume/type of realtime data RouteLens depends upon.

---

# 14. TransLink Terms Scope Caveat

The previous legal research primarily examined the TransLink developer/API terms applicable to realtime API access.

Before public or commercial release, RouteLens should verify:

- the exact current terms governing GTFS Static distribution/use;
- the exact current terms governing GTFS-Realtime;
- whether the same attribution wording applies to both;
- permitted caching/persistence;
- commercial-use conditions;
- request limits.

Do not assume that because GTFS Static is downloadable, it necessarily has the same rights structure as OGL government data.

---

# 15. TransLink Architecture Consequence

TransLink must remain an independently removable dependency.

Correct:

```text
TransLink unavailable

Road Ahead         ✓
Open511            ✓
Vancouver camera   ✓
SWOB               ✓
OpenWeather        ✓
Journey briefing   ✓

Transit alerts     unavailable
```

Incorrect:

```text
TransLink unavailable
→ entire RouteLens analysis fails
```

The product should remain useful even when Transit data is absent.

---

# 16. TransLink Commercialization

Before offering a paid RouteLens product materially using TransLink data:

1. re-read the current developer/licensing terms;
2. contact TransLink if required for the intended commercial model;
3. confirm applicable request limits;
4. confirm GTFS Static storage/use rights;
5. confirm Service Alerts caching/storage rights;
6. confirm the exact required attribution;
7. determine whether charging users creates additional fees or conditions.

TransLink should not become an indispensable paid-product dependency without resolving these questions.

---

# 17. OpenWeather

## Status

**YELLOW**

Unlike the Green government sources, OpenWeather is a commercial weather-data provider operating under provider-specific terms.

The prior terms review found that current self-service usage supports commercial application use subject to:

- the applicable subscription;
- visible attribution;
- ODbL-related conditions;
- usage limitations;
- potential database share-alike implications.

## Current RouteLens Role

OpenWeather is intended to provide:

- coordinate-based current conditions;
- near-term forecast information.

The exact API endpoint and fields remain subject to technical validation.

---

# 18. OpenWeather Attribution

Visible attribution is required under the previously reviewed self-service terms.

Practical placeholder:

```text
Weather data © OpenWeather
[link to OpenWeather]
[logo if required by active terms]
```

The exact wording/display requirements should be rechecked against the subscription in use.

---

# 19. OpenWeather Database / Share-Alike Consideration

The architecture should distinguish between:

## Normal Application Use

```text
OpenWeather request
→ temporary/application cache
→ normalize selected fields
→ journey analysis
```

This is the intended MVP usage.

## Derived Weather Database Product

A materially different architecture would be:

```text
large OpenWeather ingestion
→ persistent reconstructed database
→ externally distributed database/API
```

That architecture could create additional ODbL/share-alike implications.

RouteLens should avoid accidentally turning a normal weather cache into a separately redistributed weather-data product.

---

# 20. OpenWeather Commercialization

Before commercial launch:

- confirm the exact subscription tier;
- confirm the endpoint is permitted under that tier;
- implement visible attribution;
- review expected API volume;
- review storage/caching behavior;
- review ODbL implications of the final architecture;
- consider custom/Enterprise terms if RouteLens requires broader rights.

---

# 21. Active MVP Camera Policy

Because DriveBC Cameras are no longer in the MVP, the current raw-camera policy primarily applies to:

> **Vancouver Traffic Webcams**

## Metadata

Retain normally where licensed.

## Current Images

Treat as:

> ephemeral / cache-only.

## Derived AI Observations

May be retained separately, with provenance.

## Historical Images

Disabled.

## Model Training

Do not accumulate camera frames for model training under the current project assumptions.

## Commercial Image Use

Requires a fresh rights review.

---

# 22. Provenance Should Survive Normalization

Normalization should not erase licensing provenance.

Conceptual:

```python
SourceMetadata(
    source="drivebc_open511",
    provider="Province of British Columbia",
    license_id="OGL-BC",
    attribution_required=True,
    raw_asset_policy="persistent_allowed",
)
```

versus:

```python
SourceMetadata(
    source="vancouver_webcam_image",
    provider="City of Vancouver / applicable image provider",
    metadata_license="OGL-Vancouver",
    raw_image_license="unconfirmed",
    raw_asset_policy="ephemeral_only",
)
```

The precise runtime schema belongs in technical design/implementation.

The legal principle is:

> **Important evidence should remain traceable to the provider and licence/terms that governed it.**

Useful provenance may include:

```text
source
provider
source_record_id
source_url
fetched_at
observed_at
updated_at
license_id
attribution
raw_asset_policy
```

---

# 23. AI Synthesis Must Not Erase Provenance

RouteLens may combine:

```text
Road Ahead
+
Open511
+
SWOB
+
OpenWeather
+
camera AI
+
TransLink
        ↓
JourneyBriefing
```

but the resulting application should retain the underlying source distinctions.

The LLM should not transform:

> six independently governed sources

into:

> apparently proprietary RouteLens facts with no provenance.

The output may be a RouteLens interpretation, while underlying evidence still retains source attribution.

---

# 24. Attribution Requirements

RouteLens should eventually expose a visible:

> **Sources / Attribution**

area.

Attribution should ideally be driven from source metadata/configuration rather than duplicated manually across many UI components.

---

# 25. City of Vancouver Open Data Attribution

Suggested fallback wording:

> Contains information licensed under the Open Government Licence – Vancouver.

Applicable to qualifying Vancouver open-data datasets such as Road Ahead and webcam metadata.

Do not imply that this automatically resolves raw camera-image rights.

---

# 26. DriveBC Open511 / OGL-BC Attribution

Suggested fallback wording:

> Contains information licensed under the Open Government Licence – British Columbia.

The UI may additionally identify:

> Source: DriveBC

without implying endorsement.

---

# 27. ECCC / OGL-Canada Attribution

Suggested fallback wording:

> Contains information licensed under the Open Government Licence – Canada.

A product-facing label may also identify:

> Environment and Climate Change Canada

---

# 28. TransLink Attribution

TransLink's terms require provider-specific attribution.

RouteLens should use the **exact current wording required by TransLink**, not an invented summary.

Implementation placeholder:

```text
[Exact current TransLink attribution legend]
```

Recheck immediately before public release.

---

# 29. OpenWeather Attribution

Current working placeholder:

```text
Weather data © OpenWeather
[link]
[logo where required]
```

Recheck the exact current requirements under the active account/subscription.

---

# 30. Vancouver Camera Attribution

Until image-specific rights are confirmed, display clear source identification such as:

```text
Current image source: City of Vancouver
```

where appropriate.

Source attribution does **not** substitute for any permission that may ultimately be required.

---

# 31. Datathon / Portfolio MVP

The MVP deliberately uses a conservative risk posture.

## Green Structured Sources

Use normally with attribution:

- Vancouver Road Ahead;
- DriveBC Open511;
- ECCC SWOB.

## TransLink

Use under the authorized account/key and current terms.

Respect:

- request limits;
- attribution;
- approved-use requirements.

## OpenWeather

Use under the active plan.

Provide required attribution.

## Vancouver Camera Imagery

Use conservatively:

```text
current images
→ temporary cache
→ display
→ multi-view multimodal inference
→ overwrite/discard
```

Do not create:

- historical archive;
- bulk mirror;
- training dataset.

## DriveBC Cameras

Not part of MVP.

No rights dependency is required for MVP success.

---

# 32. Public Free Application

Moving RouteLens from a private/local MVP to an internet-accessible free application materially increases terms-compliance requirements.

Before public launch:

- implement OGL-Vancouver attribution;
- implement OGL-BC attribution;
- implement OGL-Canada attribution;
- confirm TransLink's approved use matches the public application;
- use exact TransLink attribution;
- review GTFS Static terms;
- review GTFS-Realtime Service Alert terms;
- confirm TransLink request limits;
- confirm OpenWeather plan;
- implement OpenWeather visible attribution;
- confirm public Vancouver camera proxy/display behavior is acceptable;
- reconsider proxying if direct/reference-based presentation has clearer rights;
- document source freshness and limitations.

A free public application should not be assumed equivalent to a local portfolio prototype merely because no money is charged.

---

# 33. Commercial / SaaS Product

Commercialization requires a stronger review.

## Green Government Sources

The following remain strong foundations:

- Road Ahead;
- DriveBC Open511;
- ECCC SWOB.

Their applicable open-government licences are designed to support reuse, including commercial use when conditions are satisfied.

## TransLink

Commercial charging may create additional conditions or compensation requirements.

Do not assume current prototype approval automatically extends to a paid SaaS product.

## OpenWeather

Commercial application use is supported under the applicable provider terms, subject to:

- plan level;
- attribution;
- usage restrictions;
- ODbL considerations;
- possible database share-alike implications.

## Vancouver Camera Images

Obtain clearer rights before a commercial architecture materially relies on:

- republishing;
- persistent storage;
- redistribution;
- image API access;
- image licensing;
- accumulated model-training use.

If adequate rights cannot be established, redesign the commercial product so raw camera images can be:

- removed;
- replaced;
- externally referenced;
- or provided through a properly licensed alternative.

## DriveBC Cameras

Because they are deferred, no DriveBC image-rights resolution is required to commercialize the **current** MVP architecture.

If they are later added, their rights must be reviewed before becoming a material product dependency.

---

# 34. Architectural Independence

The current source architecture supports licensing resilience.

Conceptually:

```text
Road Ahead ──────┐
Open511 ─────────┤
SWOB ────────────┤
OpenWeather ─────┤
TransLink ───────┼── normalization → journey evidence
Vancouver camera ┘
```

Every source should remain replaceable/removable.

A future licensing or provider-policy change should not require redesigning the whole application.

This matters most for Yellow dependencies.

---

# 35. Avoiding Data-Licence Contamination

Combining data in one analysis does not make all underlying source data licence-free.

Preserve the ability to answer:

```text
Which provider contributed this fact?

What licence or terms applied?

When was it retrieved?

Was the raw asset persistent or ephemeral?

What attribution is required?
```

The unified journey model should improve application ergonomics without erasing legal provenance.

---

# 36. Deferred / Future Source: DriveBC Cameras

## Status

**YELLOW**

## MVP Status

> **Explicitly deferred.**

DriveBC camera imagery is not required for the current RouteLens MVP.

## Potential Future Role

Possible future uses include:

- highway weather context;
- bridge approaches;
- regional visibility;
- routes originating outside Vancouver;
- coverage beyond Vancouver municipal cameras.

## Rights Research

The previous review did not establish that DriveBC Open511's OGL-BC licence automatically applies to DriveBC camera JPEGs.

That remains an unresolved asset-specific rights question.

In addition, some camera images may originate from third-party providers.

## Future Policy

If DriveBC cameras are later implemented, use the same conservative pattern as Vancouver imagery:

```text
fetch current image
→ temporary/cache-only use
→ display/analyze
→ derived observation
→ overwrite/discard
```

Until rights are clarified, avoid:

- historical archives;
- bulk redistribution;
- resale;
- training corpora.

## Commercialization Requirement

Explicitly review rights before DriveBC camera imagery becomes a material commercial dependency.

Because this source is currently deferred, this is **not a blocker for the MVP**.

---

# 37. Deferred / Future Source: ECCC Weather Radar

## Status

**GREEN**

Relevant ECCC radar datasets can be available under OGL-Canada.

Potential future use:

```text
Vancouver camera
+
SWOB station
+
ECCC radar
        ↓
stronger precipitation context
```

Radar could improve geographic precipitation awareness without introducing a proprietary weather-data dependency.

Not required for MVP.

---

# 38. Deferred / Future Source: Vancouver 311

## Status

**GREEN, with privacy-awareness requirement**

Applicable Vancouver 311 open data is available through the City's open-data system.

Possible future uses:

- route-adjacent municipal issues;
- neighborhood activity patterns;
- additional city-state context.

RouteLens should not attempt to:

- reconstruct suppressed addresses;
- identify individuals;
- reverse privacy protections.

Not required for MVP.

---

# 39. Deferred / Future Source: Metro Vancouver AirMap

## Status

**YELLOW**

The previously reviewed AirMap terms differ materially from OGL-style open data.

The data is described as protected by copyright/proprietary rights.

Do not assume permission for:

- bulk storage;
- commercial redistribution;
- derivative databases;
- commercial reuse

without further review.

Air quality therefore remains an optional future integration rather than a core RouteLens dependency.

---

# 40. Deferred / Future Vancouver Open-Data Layers

## Status

**Generally GREEN where the individual dataset explicitly carries OGL-Vancouver**

Possible examples:

- road infrastructure;
- administrative boundaries;
- static geographic context;
- facilities;
- additional construction/context layers.

Always verify the individual dataset's licence.

Government-hosted does not automatically mean openly licensed.

---

# 41. Sources Not Fully Reviewed Here

The following RouteLens dependencies require separate service-provider terms review before serious commercial deployment:

```text
MapTiler
openrouteservice
OpenRouter
```

Potential considerations include:

- commercial plan requirements;
- API quotas;
- tile attribution;
- caching restrictions;
- geocoding storage restrictions;
- model-provider image/data handling;
- AI-provider retention policies;
- redistribution restrictions.

These are service/infrastructure-contract questions rather than primarily city/open-data licensing questions.

---

# 42. AI Provider and Camera Images

Because RouteLens sends camera imagery to a multimodal model provider, a future commercial review should consider not only:

> May RouteLens fetch/display this image?

but also:

> May RouteLens transmit this image to the selected AI provider for inference under both the image provider's rights and the AI provider's terms?

The current ephemeral architecture reduces local retention but does not remove this question.

Before commercial launch, review:

- OpenRouter terms;
- selected underlying model-provider terms where relevant;
- image retention/training policies;
- any provider-specific restrictions on submitted imagery.

---

# 43. Before Public Release Checklist

Before RouteLens becomes a public application:

- [ ] Verify every active dataset still has the recorded licence/terms.
- [ ] Record the date of the review.
- [ ] Add OGL-Vancouver attribution.
- [ ] Add OGL-BC attribution.
- [ ] Add OGL-Canada attribution.
- [ ] Recheck TransLink GTFS Static terms.
- [ ] Recheck TransLink GTFS-Realtime terms.
- [ ] Add exact current TransLink attribution.
- [ ] Confirm registered TransLink use accurately describes RouteLens.
- [ ] Confirm current TransLink request limits.
- [ ] Add required OpenWeather attribution.
- [ ] Confirm active OpenWeather plan permits selected endpoint(s).
- [ ] Re-evaluate Vancouver camera-image rights.
- [ ] Confirm public proxy/display behavior for Vancouver images.
- [ ] Ensure raw Vancouver images remain non-historical unless rights are established.
- [ ] Ensure provenance survives normalization.
- [ ] Review MapTiler terms.
- [ ] Review openrouteservice terms.
- [ ] Review OpenRouter / multimodal-provider data-use terms.

DriveBC camera-image review is not required for current MVP publication because that integration is deferred.

---

# 44. Before Commercialization Checklist

Before charging users, selling RouteLens, licensing outputs, or materially commercializing the system:

- [ ] Re-read every active licence and provider agreement.
- [ ] Record licence/version/date relied upon.
- [ ] Confirm commercial use of active City/BC/Canada datasets.
- [ ] Confirm Road Ahead detail-page usage assumptions.
- [ ] Contact/reconfirm TransLink commercial use as appropriate.
- [ ] Confirm GTFS Static commercial/use terms.
- [ ] Confirm GTFS-Realtime Service Alert commercial/use terms.
- [ ] Confirm TransLink caching/storage limits.
- [ ] Confirm whether additional TransLink commercial fees apply.
- [ ] Confirm OpenWeather subscription tier.
- [ ] Review OpenWeather ODbL implications against the final architecture.
- [ ] Ensure RouteLens is not unintentionally redistributing a derivative weather database.
- [ ] Consider OpenWeather custom/Enterprise terms if needed.
- [ ] Obtain clearer rights for commercial Vancouver camera-image use.
- [ ] Do not commercialize a raw camera archive without established rights.
- [ ] Review AI-provider terms for transmitting camera images.
- [ ] Review MapTiler commercial terms.
- [ ] Review openrouteservice commercial terms.
- [ ] Implement complete in-product source/attribution UI.
- [ ] Preserve evidence of the terms relied upon at launch.
- [ ] Obtain professional legal review if RouteLens becomes a serious commercial product.

If DriveBC cameras are later brought back into scope:

- [ ] perform a separate DriveBC image-rights review before launch.

---

# 45. Recommended Data-Source Register

For future maintainability, RouteLens may maintain a lightweight source register.

Example:

```yaml
source: drivebc_open511
provider: Province of British Columbia
mvp_status: included
risk: green
license: Open Government Licence - British Columbia
commercial_use: allowed
attribution_required: true
raw_cache: allowed
normalized_persistence: allowed
external_redistribution: allowed_subject_to_license
last_terms_review: 2026-10-07
```

Vancouver image example:

```yaml
source: vancouver_webcam_image
provider: City of Vancouver / applicable linked image provider
mvp_status: included
risk: yellow
metadata_license: Open Government Licence - Vancouver
raw_image_license: unconfirmed
raw_cache: ephemeral_only
historical_archive: disabled
derived_observation_persistence: allowed_pending_future_review
commercial_image_use: requires_review
last_terms_review: 2026-10-07
```

Deferred DriveBC example:

```yaml
source: drivebc_camera_image
provider: Province of British Columbia / possible third parties
mvp_status: deferred
risk: yellow
raw_image_license: unconfirmed
commercial_image_use: requires_review_before_integration
```

This may eventually become:

```text
docs/data-sources.md
```

or structured configuration if the project grows.

It is not necessary for the datathon MVP.

---

# 46. Core Legal / Architecture Principle

The central principle remains:

> **Publicly accessible does not mean public domain, and the licence attached to metadata does not necessarily extend to every linked asset.**

That distinction explains why the current source posture can look like:

```text
Road Ahead structured data     → GREEN

Open511 structured data        → GREEN

ECCC observations              → GREEN

Vancouver camera metadata      → GREEN

Vancouver camera JPEGs         → YELLOW

TransLink data                 → YELLOW / custom terms

OpenWeather data               → YELLOW / provider terms + ODbL

DriveBC camera JPEGs           → YELLOW, but DEFERRED
```

Licensing is therefore an architectural concern, not merely paperwork added after implementation.

---

# 47. Why the Current MVP Scope Improves the Legal Posture

Removing DriveBC Cameras from the MVP simplifies the rights surface.

The current MVP now has only one active raw-image integration:

> Vancouver Traffic Webcams.

This means the project can demonstrate:

- geospatial camera selection;
- directional image handling;
- multimodal inference;
- ephemeral image caching

without simultaneously resolving the separate DriveBC image-rights question.

The deferred integration can later reuse the same camera architecture if legal and product value justify it.

This is preferable to adding a second Yellow image dependency merely for broader coverage.

---

# 48. Current RouteLens Conclusion

The current RouteLens MVP remains well positioned from a data-rights perspective.

Its core structured-data foundation relies heavily on clearly reusable government information:

- Vancouver Road Ahead;
- DriveBC Open511;
- ECCC weather observations.

The principal **active MVP** licensing/commercialization issues are now:

1. **Vancouver raw camera imagery**
2. **TransLink's custom/revocable terms**
3. **OpenWeather subscription, attribution, and ODbL obligations**

DriveBC camera-image rights remain a useful research note, but they are no longer an MVP blocker because the source has been explicitly deferred.

The architecture further limits risk by:

- isolating providers behind adapters;
- allowing independent source failure;
- keeping raw camera imagery ephemeral;
- avoiding historical image archives;
- persisting derived observations rather than image collections;
- preserving provenance;
- using deterministic source matching before AI;
- preventing Yellow providers from becoming the entire product.

For the datathon/portfolio MVP, this remains a reasonable engineering posture.

For a serious public or commercial product, the active Yellow dependencies should receive a fresh terms review and, where appropriate, direct provider clarification or professional legal advice.
