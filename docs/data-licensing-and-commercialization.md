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

**Research status:** October 7, 2026.

---

# 2. Scope

The main analysis covers the seven planned RouteLens MVP information sources:

1. Vancouver webcams
2. Vancouver Road Ahead
3. DriveBC Open511
4. DriveBC cameras
5. Environment and Climate Change Canada GeoMet / SWOB
6. TransLink GTFS-Realtime
7. OpenWeather

A short appendix also records previously considered or possible future sources:

- ECCC weather radar
- Vancouver 311
- Metro Vancouver AirMap
- additional City of Vancouver open-data layers

This document does **not** currently constitute a full terms review of infrastructure/service providers such as:

- MapTiler
- openrouteservice
- OpenRouter

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

Green does not mean “no obligations.”

Attribution and licence terms still apply.

## Yellow

Usable, but important terms, limitations, rights ambiguity, commercial conditions, rate limits, or asset-specific restrictions require attention.

A Yellow source may be entirely reasonable for the MVP while still deserving review before commercialization.

## Red

Use is unsuitable for the intended product without obtaining additional permission, changing the architecture, or replacing the source.

No current core RouteLens structured-data source is classified Red.

Some **forms of use of camera imagery** would become effectively Red unless permission is obtained.

---

# 4. Current MVP Summary

| Source | Current Risk | Main Reason |
|---|---|---|
| Vancouver Road Ahead | **Green** | Explicit Open Government Licence – Vancouver |
| Vancouver webcam metadata | **Green** | City Open Data material under OGL-Vancouver |
| Vancouver webcam images | **Yellow** | Publicly accessible image asset rights are not clearly established by the metadata licence |
| DriveBC Open511 | **Green** | Explicit OGL-BC |
| DriveBC camera imagery | **Yellow** | No clear evidence that Open511/OGL-BC covers the JPEG imagery; general B.C. web copyright is restrictive |
| ECCC GeoMet / SWOB | **Green** | Explicit Open Government Licence – Canada |
| TransLink GTFS-Realtime | **Yellow** | Custom, revocable licence; API approval/key, limits, required attribution, commercial conditions |
| OpenWeather | **Yellow** | Commercial use allowed under current plans, but ODbL, visible attribution, plan limits and database share-alike considerations apply |

The overall RouteLens data posture is therefore:

> **Healthy overall, with the main commercialization attention concentrated around camera imagery, TransLink, and OpenWeather licensing conditions.**

---

# 5. City of Vancouver Open Government Licence

The City of Vancouver publishes its open data under the **Open Government Licence – Vancouver**.

The licence grants a worldwide, royalty-free, perpetual, non-exclusive right to use covered information, including commercially, and permits copying, modification, adaptation, publication and distribution for lawful purposes.

Attribution is required.

This makes properly designated City of Vancouver open datasets strong foundations for RouteLens.

Important limitation:

> The licence covers information offered under that licence. It should not automatically be assumed to cover every externally linked or separately delivered asset.

That distinction is particularly important for webcam images.

---

# 6. Vancouver Road Ahead

## Status

**GREEN**

The Road Ahead current-road-closures dataset explicitly lists:

> Open Government Licence – Vancouver

as its licence. The current dataset also exposes hourly feeds during weekday daytime hours in addition to the portal extract.

## RouteLens Use

Planned operations are well aligned with OGL-Vancouver:

```text
fetch
→ cache
→ normalize
→ geospatially filter
→ combine with other route evidence
→ derive journey insight
→ display in application
```

Commercial use, transformation and redistribution of the licensed information are permitted subject to the licence requirements.

## Persistence

Persistent storage of normalized Road Ahead information is reasonable under the open licence.

Raw response caching is also compatible with the planned architecture.

## Commercialization

No major licence blocker is currently apparent.

Before commercial release:

- preserve attribution;
- preserve provenance;
- recheck that the specific datasets being used remain designated OGL-Vancouver.

---

# 7. Vancouver Webcam Metadata

## Status

**GREEN**

The City's webcam dataset contains locations and URLs for official publicly available webcams. The dataset states that the listed locations are approximate and that webcam images themselves are updated approximately every five minutes.

Because this information is published through the City's open-data system, the metadata can be treated separately from the image asset itself under the City's open-data licensing framework.

## Metadata Suitable for Persistence

Examples:

```text
camera ID
camera location
camera URL
camera name/intersection
source
metadata timestamps
```

This information may be normalized into RouteLens's `Camera` model.

---

# 8. Vancouver Webcam Images

## Status

**YELLOW**

The key distinction is:

```text
City open-data record
├── camera location
├── camera metadata
└── camera URL
        ↓
     linked image
```

An open licence covering the metadata does **not automatically prove that every linked JPEG inherits the same rights**.

The City dataset itself says that it contains links to public cameras and that the City does not control what is displayed by those cameras.

Therefore RouteLens should not assume, without additional confirmation, that it has unrestricted rights to:

- create a historical camera archive;
- redistribute camera JPEGs through a separate data product;
- create a permanent mirror of the imagery;
- train models on an accumulated image corpus;
- sell access to an image archive.

## MVP Architectural Policy

RouteLens should use:

```text
camera URL
     ↓
fetch latest image
     ↓
temporary local cache
     ↓
display same frame
     ↓
multimodal analysis
     ↓
derived CameraObservation
```

Raw image policy:

```text
latest image only
→ overwrite on refresh
→ no historical archive
```

Derived result:

```text
CameraObservation(
    precipitation_visible=...,
    road_surface=...,
    visibility=...,
    traffic_level=...,
    confidence=...
)
```

may be retained as RouteLens application data, subject to future review of derived-data implications.

## Important Caveat

Ephemeral processing **reduces the licensing surface area but does not itself prove that the processing is legally permitted**.

The architecture is deliberately conservative while image rights remain unresolved.

---

# 9. DriveBC Open511

## Status

**GREEN**

DriveBC's official Open511 documentation explicitly states that information supplied by the API is governed by the **Open Government Licence – British Columbia**.

OGL-BC permits covered information to be used commercially and permits copying, modification, publication, adaptation and distribution subject primarily to attribution and other licence conditions.

B.C.'s API terms separately govern how the API itself is accessed while stating that use of the information remains governed by OGL-BC.

## RouteLens Use

This is well suited to:

```text
Open511 events
→ normalize into CityEvent
→ route intersection/distance
→ severity/freshness ranking
→ journey timeline
→ AI briefing evidence
```

## Persistence

Reasonable:

- API caching
- normalized event persistence
- derived ranking
- combination with other licensed sources

subject to OGL attribution.

## Commercialization

Open511 is one of the strongest core RouteLens dependencies from a licensing perspective.

---

# 10. DriveBC Camera Imagery

## Status

**YELLOW**

DriveBC publicly provides highway-camera images for travel information.

Its camera system itself uses an overwrite-oriented current-image model, and the public FAQ notes that newer images replace previous ones rather than maintaining a public historical image archive.

However:

> DriveBC Open511 being OGL-BC does not establish that every DriveBC camera JPEG is licensed under OGL-BC.

The Open511 licence explicitly covers information delivered through that API.

By contrast, the Province's general current website copyright policy states that B.C. government website material is copyrighted and may not be reproduced or redistributed without prior permission unless another applicable licence provides permission.

DriveBC also includes some camera views supplied by third parties; for example, current camera pages can identify Parks Canada as the image provider.

This means source-by-source rights may matter.

## RouteLens Policy

Treat DriveBC camera imagery the same conservatively as Vancouver imagery:

```text
fetch current image
→ temporary/cache-only processing
→ display current frame
→ multimodal inference
→ overwrite on refresh
```

Do not create:

- permanent image archives;
- image resale;
- bulk redistribution;
- training corpora

without confirming permission.

## Commercialization Requirement

Explicitly establish image-use rights before making DriveBC imagery a material commercial dependency.

---

# 11. ECCC GeoMet / SWOB Meteorological Observations

## Status

**GREEN**

Environment and Climate Change Canada's Meteorological Observations dataset is explicitly published under the **Open Government Licence – Canada**.

OGL-Canada permits commercial use, copying, modification, publication, adaptation and distribution, subject to attribution and its stated exceptions.

## RouteLens Use

The planned pipeline is strongly aligned with the licence:

```text
weather observation
→ normalize selected fields
→ associate with destination
→ combine with camera evidence
→ produce journey insight
```

## Persistence

Reasonable:

- normalized observation storage;
- caching;
- correlation;
- derived observations;
- commercial application use.

## Important Data-Quality Note

ECCC notes that near-real-time observations can come from multiple observing-system operators, have limited quality assurance, and should not necessarily be treated as final quality-controlled official values.

This is a product/provenance consideration rather than a licensing blocker.

---

# 12. TransLink GTFS-Realtime / Open API

## Status

**YELLOW**

TransLink does not offer this API under an OGL-style open-government licence.

Its current terms require users to provide information about:

- who will use the data;
- where the data will be distributed;
- whether the use is commercial or non-commercial.

Access is subject to TransLink approval and issuance of an API key.

The current terms state that:

- TransLink retains rights in the data;
- users receive a limited, revocable, non-exclusive licence;
- the normal API-key limit is 1,000 requests per day;
- TransLink may alter limits;
- the licence/API key may be terminated on notice;
- a specific attribution legend must be prominently displayed;
- additional terms or compensation may be required when a commercial user charges users for access involving the data.

## Architecture Consequence

TransLink must remain behind an independent adapter.

RouteLens should still produce useful results when TransLink is unavailable.

Correct:

```text
TransLink unavailable

Road Ahead        ✓
Open511           ✓
Cameras           ✓
Weather           ✓
Journey briefing  ✓
Transit insight   unavailable
```

Incorrect:

```text
TransLink unavailable
→ RouteLens unusable
```

## Commercialization

Before offering a paid RouteLens product that materially uses TransLink data:

1. contact/reconfirm TransLink-approved commercial use;
2. confirm request limits;
3. confirm caching/storage rules for the intended implementation;
4. confirm required attribution;
5. determine whether additional commercial fees or conditions apply.

This should happen **before** TransLink becomes an indispensable commercial dependency.

---

# 13. OpenWeather

## Status

**YELLOW**

Unlike the government open-data sources, OpenWeather is a commercial weather-data provider operating under subscription/licensing terms.

Its current self-service documentation states that self-service API plans operate under the **Open Database License (ODbL)** and permit commercial as well as non-commercial use. Visible attribution is required.

The current pricing documentation also states that standard commercial use includes applications such as:

- websites;
- mobile applications;
- SaaS;
- dashboards;
- analytics tools;
- internal business systems.

This means RouteLens can use OpenWeather in a commercial derivative application under an appropriate self-service plan, but the licence has conditions that differ materially from OGL data.

## Attribution

Current OpenWeather guidance requires visible attribution.

Its FAQ specifies attribution requirements for applicable self-service plans, including identifying OpenWeather, linking to its website, and displaying its provided logo.

Current detailed pricing also recommends:

> “Weather data © OpenWeather”

Attribution should appear in the visible application rather than only in deeply buried documentation.

## Database / Share-Alike Consideration

OpenWeather's current documentation draws an important distinction between:

### Normal application use

Using weather results to power RouteLens.

This requires attribution but does not require RouteLens application code or business logic to be open-sourced.

### Creating an externally distributed derived weather database/API

If OpenWeather data is substantially stored, restructured, combined or enriched into a reusable weather database and that resulting database is distributed externally, current guidance states that ODbL share-alike requirements may apply to that database.

RouteLens therefore should avoid accidentally turning its OpenWeather cache into a separately redistributed weather database.

## MVP Use

The intended RouteLens use is narrow:

```text
destination
→ near-term API lookup
→ temporary/cacheable forecast
→ normalize useful values
→ journey interpretation
```

That is substantially simpler than operating a derived weather-data service.

## Commercialization

Before commercial launch:

- select an appropriate OpenWeather subscription;
- implement required visible attribution;
- review expected API volume;
- review storage/redistribution design;
- reassess ODbL implications if RouteLens begins exposing stored weather datasets or an API;
- consider Enterprise/custom terms if broader licensing flexibility is needed.

Current self-service plans explicitly permit standard commercial use, while Enterprise is positioned for broader/custom licensing requirements.

---

# 14. Raw Camera Image Policy

RouteLens adopts the following project-wide policy for both Vancouver and DriveBC cameras while rights remain incompletely verified.

## Metadata

May be retained normally where the metadata source is appropriately licensed.

## Raw Camera Images

Treat as:

> **ephemeral / cache-only**

Implementation:

```text
camera
  ↓
fetch latest frame
  ↓
cache temporarily
  ↓
display + analyze
  ↓
new frame replaces old frame
```

Do not intentionally create a historical image collection.

## Derived AI Observations

May be persisted separately:

```text
camera_id
source
image timestamp
analysis timestamp
precipitation_visible
road_surface
traffic_level
visibility
confidence
```

Preserve provenance connecting the derived observation to its source.

## Before Commercial Image Use

Separately establish rights before:

- long-term image retention;
- creating historical replay;
- republishing images at scale;
- redistributing raw images through an API;
- licensing image access to third parties;
- model training using accumulated frames;
- selling an image archive or derived image corpus.

---

# 15. Provenance Should Survive Normalization

Normalization should not erase licensing information.

A useful future model pattern is:

```python
SourceMetadata(
    source="drivebc_open511",
    provider="Province of British Columbia",
    license_id="OGL-BC-2.0",
    attribution_required=True,
    raw_asset_policy="persistent_allowed",
)
```

versus:

```python
SourceMetadata(
    source="vancouver_webcam",
    provider="City of Vancouver",
    metadata_license="OGL-Vancouver",
    raw_asset_policy="ephemeral_pending_rights_review",
    derived_data_policy="persistent",
)
```

The exact schema belongs in technical design/implementation work, but the principle should remain:

> **Every important observation should retain enough source provenance to determine where it came from and what obligations follow it.**

Useful fields might eventually include:

```text
source
provider
source_record_id
source_url
fetched_at
observed_at
license_id
attribution
raw_asset_policy
```

---

# 16. Attribution Requirements

RouteLens should eventually expose a visible:

> Sources / Attribution

section.

Attribution should be driven by source metadata rather than scattered hardcoded UI strings where practical.

---

## City of Vancouver Open Data

Suggested attribution:

> Contains information licensed under the Open Government Licence – Vancouver.

This is the fallback attribution provided by the licence where a more specific statement is not supplied.

---

## DriveBC Open511 / OGL-BC

Suggested attribution:

> Contains information licensed under the Open Government Licence – British Columbia.

This is the standard OGL-BC fallback attribution.

Where useful, RouteLens may additionally identify:

> Source: DriveBC

without implying endorsement.

---

## ECCC / OGL-Canada

Suggested attribution:

> Contains information licensed under the Open Government Licence – Canada.

This is the standard OGL-Canada fallback attribution.

A product-facing source label can additionally identify:

> Environment and Climate Change Canada

---

## TransLink

TransLink's terms currently require a specific prominent attribution legend.

RouteLens should use the **exact current TransLink wording from the provider's terms rather than inventing a shorter paraphrase**.

Implementation placeholder:

```text
[Exact TransLink required legend from current API Terms]
```

Recheck the wording immediately before public release.

---

## OpenWeather

Current guidance requires visible OpenWeather attribution for self-service usage.

Recommended implementation:

```text
Weather data © OpenWeather
[link to OpenWeather]
[required OpenWeather logo where applicable]
```

Current FAQ and pricing documentation should be rechecked against the exact subscription used.

---

## Camera Imagery

Until image-specific rights are confirmed, display an explicit source label such as:

```text
Current image source: City of Vancouver
```

or:

```text
Current image source: DriveBC
```

This attribution does **not** substitute for obtaining any permission that may actually be required.

---

# 17. Datathon / Portfolio MVP

The MVP's risk posture is deliberately conservative.

Reasonable approach:

### Green sources

Use normally with attribution:

- Road Ahead
- Open511
- ECCC observations

### TransLink

Use through the authorized API under the registered key and current terms.

Respect:

- rate limits;
- required attribution;
- approved use.

### OpenWeather

Use under the active account/subscription terms.

Provide visible attribution.

### Camera imagery

Use current publicly accessible frames conservatively:

```text
short-lived fetch
→ display
→ inference
→ overwrite
```

Do not create a historical archive.

This architecture makes the portfolio MVP substantially less dependent on unresolved long-term content rights.

---

# 18. Public Free Application

Moving from a private/local datathon project to an internet-accessible free application increases the importance of terms compliance.

Before public launch:

- implement all OGL attributions;
- ensure TransLink's registered use accurately reflects the public application;
- display the current required TransLink legend;
- confirm OpenWeather plan and visible attribution;
- confirm public image-proxy behavior is acceptable for Vancouver/DriveBC camera imagery;
- reconsider whether RouteLens should proxy images or instead reference/display them in another permitted manner;
- document data freshness and source limitations.

A free public product should **not** be treated as legally equivalent to private prototyping simply because users are not charged.

---

# 19. Commercial / SaaS Product

Commercialization requires a stronger review.

## Green Government Sources

Road Ahead, Open511 and ECCC remain strong building blocks because their current open licences expressly allow commercial use.

## TransLink

Commercial charging may trigger additional terms or compensation requirements.

Contact TransLink before relying on its feed as a paid-product dependency.

## OpenWeather

Commercial application use is supported under current self-service terms, subject to:

- appropriate subscription;
- attribution;
- ODbL requirements;
- usage limits;
- share-alike implications if building/distributing a derivative weather database.

## Camera Images

Obtain explicit clarity or permission before a commercial architecture relies on:

- republishing;
- storing;
- redistributing;
- training on;
- selling access to

raw camera imagery.

If satisfactory rights cannot be established, design the commercial product so cameras can be:

- removed;
- replaced;
- linked rather than proxied;
- or used through a licensed alternative.

---

# 20. Architectural Independence

Licensing considerations support the existing RouteLens adapter architecture.

Each external source should be independently removable.

Conceptually:

```text
Road Ahead ───────┐
Open511 ──────────┤
ECCC ─────────────┤
OpenWeather ──────┤
TransLink ────────┼── normalization → journey model
Camera sources ───┘
```

A provider changing its terms should not require rewriting the entire system.

This is particularly important for Yellow dependencies.

---

# 21. Avoiding Data-Licence Contamination

Combining sources into an analysis does not mean RouteLens should treat every resulting object as licence-free proprietary data.

Preserve sufficient provenance to know:

```text
Which source contributed this fact?
What licence governed it?
Was the raw asset persistent or ephemeral?
Is attribution required?
```

For example, an AI briefing can combine:

```text
Road Ahead
+
ECCC
+
OpenWeather
+
camera observation
```

while the underlying evidence still retains separate provenance.

Do not allow the LLM synthesis layer to erase those distinctions from the system's data model.

---

# 22. Previously Considered / Future Sources

## 22.1 ECCC Weather Radar

### Status

**GREEN**

Current ECCC radar datasets such as DPQPE are available through the Government of Canada Open Data system under OGL-Canada.

Some accumulation products are continually updated; for example, ECCC's 24-hour accumulation product is made available every six minutes.

This could later strengthen precipitation inference:

```text
camera
+
station observation
+
radar
```

without introducing another problematic licence dependency.

---

## 22.2 Vancouver 311

### Status

**GREEN, with privacy-awareness requirement**

Current Vancouver 311 service-request data is offered through the City Open Data Portal under OGL-Vancouver. The City also suppresses some location information for certain request types to protect privacy.

Possible future uses:

- route-adjacent municipal issues;
- neighborhood activity patterns;
- contextual city-state signals.

RouteLens should use the information as published and should not attempt to reverse-engineer suppressed or identifying information.

---

## 22.3 Metro Vancouver AirMap

### Status

**YELLOW**

Metro Vancouver's AirMap terms state that near-real-time data is preliminary and may be inaccurate, and that the data and information are protected under copyright and other proprietary laws.

This is materially different from OGL-style government open data.

Do not assume:

- commercial reuse;
- bulk storage;
- redistribution;
- derived-data rights

without reviewing or obtaining clarification on the applicable terms.

AirMap should remain an optional future integration rather than a core dependency.

---

## 22.4 Additional Vancouver Open-Data Layers

### Status

**Generally GREEN when the individual dataset explicitly carries OGL-Vancouver**

Potential examples:

- road infrastructure;
- construction datasets;
- neighborhood boundaries;
- static geographic context;
- municipal facilities.

Always check the licence of the specific dataset before integration.

The fact that information appears on a government website alone is not enough; the OGL designation is the useful boundary.

---

# 23. Sources Not Yet Reviewed in This Document

The following RouteLens dependencies have separate contractual/usage considerations and should receive their own review before commercial release:

```text
MapTiler
openrouteservice
OpenRouter
```

Potential issues include:

- API usage limits;
- caching restrictions;
- basemap/tile attribution;
- commercial plan requirements;
- model-provider terms;
- data retention by AI providers;
- redistribution restrictions.

These are infrastructure/service-provider questions rather than the public city-data licensing question addressed primarily here.

---

# 24. Before Public Release Checklist

Before RouteLens becomes a public application:

- [ ] Verify each currently used dataset still has the recorded licence.
- [ ] Add OGL-Vancouver attribution.
- [ ] Add OGL-BC attribution.
- [ ] Add OGL-Canada attribution.
- [ ] Add exact current TransLink attribution legend.
- [ ] Confirm TransLink registration accurately describes the public use.
- [ ] Confirm current TransLink request limits.
- [ ] Add required OpenWeather visible attribution.
- [ ] Confirm the active OpenWeather plan supports the chosen endpoints and usage.
- [ ] Re-evaluate Vancouver camera image rights.
- [ ] Re-evaluate DriveBC camera image rights.
- [ ] Ensure raw camera images remain non-historical unless rights are established.
- [ ] Ensure source/provenance metadata survives normalization.
- [ ] Review MapTiler/openrouteservice/OpenRouter terms separately.

---

# 25. Before Commercialization Checklist

Before charging users, selling RouteLens, licensing its outputs, or materially commercializing the system:

- [ ] Re-read all current licences and provider terms.
- [ ] Record the licence/version/date reviewed for every core dependency.
- [ ] Confirm commercial use of all current City/BC/Canada datasets.
- [ ] Contact TransLink regarding the intended commercial model.
- [ ] Confirm whether additional TransLink commercial fees or conditions apply.
- [ ] Confirm TransLink storage/caching expectations.
- [ ] Confirm OpenWeather subscription tier.
- [ ] Review OpenWeather ODbL requirements for the final data architecture.
- [ ] Ensure any externally distributed weather database does not accidentally violate share-alike requirements.
- [ ] Consider OpenWeather Enterprise/custom licensing if needed.
- [ ] Obtain explicit clarity or permission for Vancouver camera-image use.
- [ ] Obtain explicit clarity or permission for DriveBC camera-image use.
- [ ] Do not commercialize a raw camera archive without established rights.
- [ ] Review AI-provider terms for sending public camera imagery to multimodal models.
- [ ] Review MapTiler and openrouteservice commercial terms.
- [ ] Implement a complete in-product attribution/source panel.
- [ ] Preserve evidence of the terms/licences relied upon at the time of launch.
- [ ] Obtain professional legal review if RouteLens becomes a serious commercial product.

---

# 26. Recommended Data-Source Record

For future maintainability, maintain a lightweight source register.

Example:

```yaml
source: drivebc_open511
provider: Province of British Columbia
risk: green
license: Open Government Licence - British Columbia
commercial_use: allowed
attribution_required: true
raw_cache: allowed
normalized_persistence: allowed
external_redistribution: allowed_subject_to_license
last_terms_review: 2026-10-07
```

Example for imagery:

```yaml
source: vancouver_webcam_image
provider: City of Vancouver / linked camera provider
risk: yellow
metadata_license: Open Government Licence - Vancouver
raw_image_license: unconfirmed
raw_cache: ephemeral_only
historical_archive: disabled
derived_observation_persistence: allowed_pending_future_review
commercial_image_use: requires_review
last_terms_review: 2026-10-07
```

This could eventually become:

```text
docs/data-sources.md
```

or structured configuration if RouteLens grows.

It is not necessary for the datathon MVP.

---

# 27. Core Legal/Architecture Principle

The most important lesson for RouteLens is:

> **Publicly accessible does not mean public domain, and the licence attached to metadata does not necessarily extend to every linked asset.**

That principle explains why:

```text
Road Ahead record      → GREEN
Open511 event           → GREEN
ECCC observation        → GREEN

camera metadata         → potentially GREEN
camera JPEG             → separate rights question

TransLink data          → custom terms
OpenWeather data        → commercial licence / ODbL terms
```

Licensing therefore influences architecture rather than being paperwork added after development.

---

# 28. Current RouteLens Conclusion

The RouteLens concept remains well positioned from a data-rights perspective.

Its core structured city-state foundation relies heavily on government datasets with explicit open licences:

- Vancouver Road Ahead;
- DriveBC Open511;
- ECCC weather observations.

These licences expressly permit commercial reuse when their conditions are followed.

The principal areas requiring continued attention are:

1. **Vancouver and DriveBC raw camera imagery**
2. **TransLink's custom/revocable API terms**
3. **OpenWeather subscription, attribution and ODbL obligations**

The current architecture already reduces these risks by:

- isolating every provider behind an adapter;
- allowing partial source failure;
- keeping camera imagery ephemeral;
- persisting derived observations rather than historical image archives;
- keeping provenance available;
- preventing any one Yellow source from defining the entire product.

For the datathon/portfolio MVP, this is a reasonable engineering posture.

For a serious public commercial product, the Yellow dependencies should receive a fresh terms review and, where appropriate, direct provider clarification or professional legal advice.
