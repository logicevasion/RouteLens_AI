# OpenRouter Assignment 0D fixtures

All request inputs and outputs in this directory are readiness evidence, not application data.

- `illustrative_camera_view_1.png` and `illustrative_camera_view_2.png` — locally authored synthetic raster illustrations. View 1 depicts wet pavement with no visible falling precipitation; view 2 depicts wet pavement and visible stylized rain. They are not photographs, Vancouver camera images, or actual observations.
- `camera_observation.actual.json` — actual final model output for the two illustrative images.
- `camera_observation.failed_attempt_1.json` — actual truncated content from the first paid vision response; retained to document the structured-output failure.
- `camera_request_result*.metadata.json` — sanitized actual response metadata; the unsuffixed file records the successful corrective vision call.
- `journey_evidence.synthetic.json` — compact synthetic normalized evidence for one hypothetical Burnaby-to-Vancouver drive. Timestamps, measurements, event, and location context are fabricated for this test; the camera observation is actual model output over synthetic illustrations.
- `journey_briefing.actual.json` — actual final model output for the synthetic evidence.
- `journey_briefing.attempt_1.json` — actual first text output. Its JSON parsed, but its `clear` status conflicted with its own reported conditions; it was superseded by one corrective request.
- `journey_request_result*.metadata.json` — sanitized actual response metadata; the unsuffixed file records the corrective text call.

No credentials, request authorization headers, or full HTTP exchanges are stored here.
