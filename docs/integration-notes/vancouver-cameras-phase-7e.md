# Vancouver Cameras and Road Ahead — Assignment 7E

**Status:** Implemented; pending human visual acceptance. Phase 7 remains in progress; Phase 8 has not started.

## Nearby camera metadata API

`POST /api/cameras/nearby` accepts a canonical `destination` and an optional `selected_intersection_id`. It reuses the existing `VancouverCameraCatalogueStore`, validates the destination with the City boundary utility, and ranks all catalogue intersections within 2,000 m by WGS84 geodesic distance and stable `intersection_id`. Records with invalid coordinates, unbounded display names/IDs, or non-allowlisted official page URLs are excluded. The result is limited to four records and includes the echoed destination, status (`available`, `stale`, or `unavailable`), stable ID, name, coordinates, approximate distance in metres, official page URL, source, and attribution.

When the gallery-selected ID is within the radius but falls outside the closest four catalogue locations, it replaces the fourth slot; the response remains capped at four and sorted by distance/ID. A missing or unavailable gallery selection leaves the nearest metadata records. The metadata method does not call `CameraImageStore`, retrieve image bytes, or require discovered directional views. `unavailable` is returned when no validated catalogue is available or there are no in-radius candidates; cached catalogue fallback is represented by `stale` when it carries stale enrichment. API failures remain camera-specific.

## Frontend and map behavior

The nearby request starts only from the explicit Analyze Journey handler and runs alongside the existing primary journey analysis and camera gallery request. It initially asks for the four nearest catalogue locations. If the authoritative `/api/cameras/nearest` result later identifies a gallery intersection missing from those four, a sequence-guarded follow-up asks the metadata API to reserve it. If gallery selection fails, the initial nearby markers remain usable. The selected marker is matched by stable intersection ID.

Up to four small MapLibre DOM markers show a camera icon; the selected gallery location receives a teal fill and outline. There are no permanent labels or image previews. Hover continues to show the intersection name. Clicking opens the validated official City camera page directly in a new tab with `noopener,noreferrer`, and stops propagation to map interactions. The link comes from the catalogue record; no popup, guessed filename, or image URL is involved. The developer confirmed the marker appearance, click navigation, hover names, and existing Destination Cameras gallery in browser review.

Origin/destination edits, route regeneration/selection changes, a new analysis, and unmount abort or invalidate requests and clear marker state. Nearby responses use the same canonical journey key and camera sequence guard plus a metadata request sequence, so older results cannot restore markers. Marker updates remove prior MapLibre markers before replacing them.

## Road Ahead selection reset

The map's Road Ahead emphasis is represented by a selected finding ID, serialized into each finding's GeoJSON `selected` property, then rendered by dedicated selected fill/casing/line layers. No MapLibre feature-state selection is used. The empty-findings map sync removes the five Road Ahead layers and its source; route and independent DriveBC layers remain untouched. **Known MVP limitation:** A selected Road Ahead event's bold route styling may persist after changing journey inputs or regenerating routes. The highlight clears when Analyze Journey is executed again. The developer has elected to defer further correction because this is a nonblocking visual issue. Do not treat the source/layer reset path or the earlier selection validity guard as a complete fix.

## Map legend and bottom-right line cleanup

The map legend was removed entirely with its unused `.map-legend` and legend-swatch CSS rules.

The bottom-right horizontal bar was the expanded MapLibre attribution row. `AttributionControl({ compact: false })` forced the row to remain expanded. It now uses MapLibre's compact mode, which keeps the attribution control collapsed during ordinary map use while leaving the City/provider credits accessible through the control. The final headless desktop run showed the app shell, but the map remained behind its loading overlay and the attribution control was not rendered, so this run did not visually verify the map chrome. The obsolete `.maplibregl-popup-content` override was also removed; no popup is created by the current frontend.

Offline regressions cover selected event data, ordinary unselected styling, and the source/layer teardown helper, while asserting route and DriveBC layers remain. These tests do not establish that the browser-observed highlight persistence is fixed. Camera click tests cover direct new-tab navigation, `noopener,noreferrer`, propagation prevention, and rejection of deceptive or unsafe URLs. A headless desktop screenshot confirms the legend and horizontal attribution row are gone; narrow-screen visual review remains outstanding.

## Verification

| Check | Result |
|---|---|
| Focused frontend camera and Road Ahead tests | **Passed** — marker navigation/safety and Road Ahead source/layer lifecycle tests |
| Full frontend test suite | **Passed** — 6 test files |
| TypeScript and production Vite build | **Passed** — `tsc -b` and Vite build; existing large MapLibre chunk advisory remains |
| Frontend lint | **Not run** — no lint script is configured |
| Focused nearby-camera backend tests | **Passed** — 23 tests in `test_camera_images.py` |
| Full backend pytest regression | **Passed** — 335 tests |
| Ruff | **Passed** — `ruff check backend/app backend/tests` |
| Backend import/route smoke | **Passed** — nearby route registered |
| Local API health and bounded nearby sample | **Passed** — local health returned 200; nearby returned four catalogue records for Vancouver City Centre, including stable IDs, distances, attribution, and validated official links |
| Nearby-path image retrieval | **Passed** — deterministic test confirms zero image-store upstream requests; the live sample called only the metadata endpoint |
| Browser reproduction of direct marker navigation and stale Road Ahead highlight | **Partial** — headless Chrome loaded the shell, backend health, map canvas, and MapLibre controls, but the MapTiler map remained behind its loading overlay; marker and event interactions could not be reached |
| Desktop map chrome screenshot | **Passed** — full legend is absent; expanded attribution row is collapsed to a compact, accessible control |
| Road Ahead reset and narrow viewport visual checks | **Not run in Codex browser** — the developer reports the highlight limitation; narrow layout remains for human review |
| `git diff --check` and runtime camera-cache ignore check | **Passed** |

No camera image bytes, credentials, new dependencies, or live-provider fixtures were added. Existing camera gallery and image-cache code was not changed. The frontend package does not configure a lint command.

## Human acceptance still required

The developer confirmed marker visibility/appearance, direct official-page navigation, marker hover names, and the existing gallery. The final cleanup removes the map legend and switches the attribution control to compact mode to avoid a persistent horizontal row while retaining access to credits. The final local screenshot could not verify map chrome because the map stayed behind its loading overlay; narrow-screen review also remains pending. The accepted Road Ahead persistence after input/route changes is a documented, nonblocking MVP limitation; the highlight clears after Analyze Journey. Phase 7 acceptance remains with the developer.
