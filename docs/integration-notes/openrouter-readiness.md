# OpenRouter Readiness — Assignment 0D

**Status:** Both roles have preliminary synthetic-request feasibility evidence; human review pending. This does not complete or accept Phase 0.

## Model and configuration

The human-selected provisional model `google/gemma-4-31b-it` was used for both `OPENROUTER_VISION_MODEL` and `OPENROUTER_TEXT_MODEL`. The ignored root `.env` contains a non-empty `OPENROUTER_API_KEY` and both model variables set to that exact identifier. `.env` remains ignored; no local environment value was changed. No alternative models were benchmarked.

OpenRouter's model page and live model-endpoint metadata, checked 2026-10-09, identify Gemma 4 31B as image/text input with text output, with a 262,144-token context. The advertised rate was $0.09 per million input tokens and $0.34 per million output tokens. DeepInfra Turbo endpoint metadata lists those same rates and supports `response_format` / `structured_outputs`; image input is advertised by the model's multimodal architecture. The calls returned provider `DeepInfra`, with reported costs consistent with those rates. Other endpoints have different prices, parameter support, and availability, so model-level capability claims do not guarantee equivalent behavior on every provider. [Model and pricing page](https://openrouter.ai/google/gemma-4-31b-it), [current endpoint metadata](https://openrouter.ai/api/v1/models/google/gemma-4-31b-it/endpoints).

Both application roles remain independently configurable even though they currently use the same selected model. The requests used OpenRouter Chat Completions, `response_format: {type: "json_schema"}`, strict schemas, `provider.require_parameters: true`, and a DeepInfra route with fallbacks disabled for bounded cost and reproducibility. OpenRouter documents multimodal messages as a content array with `text` and `image_url` parts. Its documentation warns that structured-output support is endpoint-specific; the request-level result below is the relevant compatibility evidence. [Multimodal request format](https://openrouter.ai/blog/tutorials/send-image-to-llm/), [structured outputs and endpoint support](https://openrouter.ai/docs/guides/features/structured-outputs).

## Vision readiness

Two distinct 512×320 locally authored synthetic raster illustrations were submitted together in one multimodal request. One depicts wet pavement without visible falling precipitation; the other depicts wet pavement and visible stylized rain. They are illustrative fixtures, not actual Vancouver observations or camera imagery. Their provenance is recorded in [`fixtures/openrouter/README.md`](../../fixtures/openrouter/README.md).

The first paid call returned HTTP 200 from `google/gemma-4-31b-it` via DeepInfra, accepted both images, and reported strict JSON-schema mode, but hit the 240-token output cap (`finish_reason: length`) and did not parse. One allowed corrective request raised the cap to 420 and constrained the note length. It returned parseable JSON with all seven fields: `precipitation_visible=true`, `precipitation_type="rain"`, `road_surface="wet"`, `visibility="reduced"`, `image_quality="limited"`, `confidence=null`, and a note that rain streaks were visible in the second view. The visible rain and wet-surface distinction are plausible for these illustrations; reduced visibility and limited quality are conservative but somewhat subjective. This is a single synthetic example, not an accuracy measure.

Actual final output: [`camera_observation.actual.json`](../../fixtures/openrouter/camera_observation.actual.json). The truncated first response and both request metadata records are retained in the same fixture directory.

## Text readiness

The input in [`journey_evidence.synthetic.json`](../../fixtures/openrouter/journey_evidence.synthetic.json) describes a hypothetical Burnaby-to-Downtown Vancouver drive and contains a nearby, non-overlapping synthetic municipal construction record; synthetic OpenWeather current/forecast context; an explicitly measured-data-provenance ECCC station observation that is 80 minutes old at departure and 7.2 km from the destination; the final illustrative-image camera output; and explicit unknown precipitation amounts, event end time, and travel-time/delay information. No raw feed, HTML, live source data, or real camera data was sent.

The first text response was HTTP 200 and schema-valid JSON, but selected `status="clear"` while its own summary and recommendation described rain, wet pavement, and reduced visibility. One permitted corrective request clarified status semantics. The final response was schema-valid JSON with `status="minor_conditions"`, a concise summary, three evidence-linked highlights, and a calm recommendation. It did not invent a closure, delay, travel-time estimate, or claim that missing values meant normal conditions. Its source distinctions were adequate in the highlights; the concise summary compressed camera-derived rain and forecast conditions together, so production prompts should continue to preserve explicit source labels. The synthetic camera record did not specify a geographic relationship to the selected corridor or destination, while the briefing summarized wet-road conditions in the journey context; that relevance link therefore remains unverified and should not be treated as a route-specific finding. The synthetic-only evidence is too small to establish general grounding reliability.

Actual final output: [`journey_briefing.actual.json`](../../fixtures/openrouter/journey_briefing.actual.json). The first schema-valid but inconsistent output is preserved as `journey_briefing.attempt_1.json`.

## Requests, usage, cost, and provider handling

There were **four paid inference requests total**: two vision calls and two text calls, within the four-request cap. All four returned HTTP 200 from the exact requested model via DeepInfra. One vision output was truncated and invalid JSON; one text output was parseable/schema-valid but had an inconsistent `clear` status. Each role used exactly one corrective request. The final vision and text outputs were parseable and validated. A separate preflight attempt failed at local DNS resolution before an HTTP response; it is not counted as a provider inference request and has no reported usage or cost.

| Call | Result | Prompt / completion tokens | Provider-reported cost | Client latency |
|---|---|---:|---:|---:|
| Vision attempt 1 | HTTP 200; truncated JSON (`length`) | 647 / 240 | $0.00013983 | 9.411 s |
| Vision corrective | HTTP 200; parseable schema output | 640 / 60 | $0.00007800 | 1.698 s |
| Text attempt 1 | HTTP 200; JSON valid, status inconsistent | 872 / 171 | $0.00013662 | 3.773 s |
| Text corrective | HTTP 200; parseable schema output | 930 / 114 | $0.00012246 | 3.276 s |
| **Total** | **4 paid calls; 2 final role outputs** | **3,089 / 585 (3,674 total)** | **$0.00047691** | **18.158 s total** |

Before inference, the four-call hard cap was estimated conservatively at under $0.005 using up to 40,000 combined input tokens (including images) and 1,200 output tokens at the tested endpoint's listed rates. Costs and latency in the table are provider/API-reported values where available (latency measured around each request). The actual total is far below that estimate, the $0.10 assignment limit, and the US$5 project budget. Provider prices and routing availability can change.

OpenRouter's current provider directory lists DeepInfra as “No” for training and “Zero retention”; DeepInfra's privacy policy likewise says inference inputs/outputs are not stored, sold, or used for training without explicit consent. The request did not set OpenRouter's optional `provider.zdr` or `data_collection` controls, and account-level settings were not inspected. DeepInfra's policy describes possible US processing. OpenRouter explains that inputs go to the selected provider and that provider practices vary. These are current published provider claims, not an independent audit. Only synthetic inputs were transmitted. Before any real Vancouver webcam image or user journey data is sent, confirm the current account/provider privacy controls and separately resolve the camera-image rights question recorded in the licensing plan. [OpenRouter provider directory](https://openrouter.ai/providers), [DeepInfra privacy policy](https://deepinfra.com/privacy), [OpenRouter privacy policy](https://openrouter.ai/privacy/).

The model page identifies Gemma 4 under Apache 2.0. That model license does not resolve source-image permissions or provider terms. No live Vancouver imagery was used; the existing licensing research says linked camera-image rights and AI transmission permissions remain unconfirmed.

## Readiness conclusion and remaining limits

- **Authentication/model availability:** Passed for all four requests; exact model accepted.
- **Vision:** Preliminary readiness demonstrated for two-image input and endpoint-enforced schema output after one token-cap correction.
- **Text:** Preliminary readiness demonstrated for compact normalized synthetic evidence and endpoint-enforced schema output after one status-semantics correction.
- **Structured output:** Strict JSON Schema was accepted by the tested DeepInfra endpoint. The first vision response nevertheless truncated, confirming schema mode is not a substitute for completion and post-response validation.
- **Behavior:** Final sample responses were plausible and mostly evidence-based. The initial text status inconsistency, unverified camera-to-route relevance, and subjective vision quality labels show why deterministic schema and semantic validation remain necessary.
- **Not established:** Real-world camera accuracy, broad factual reliability, production prompts, production adapter behavior, provider availability/fallback behavior, live telemetry quality, latency under load, or account-level privacy controls.

For later implementation, retain strict schema validation and add deterministic semantic checks; choose a sufficient output cap; allow only a bounded corrective attempt; and treat provider fallback as a change in price/capability that must be checked. If inference still fails, preserve the rest of the deterministic journey analysis and mark AI output unavailable, consistent with the approved design.

No production adapter, domain model, endpoint, pipeline, cache, or UI was added. Model comparison was intentionally deferred because the developer selected this provisional default for both roles.
