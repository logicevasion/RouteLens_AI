# Vancouver Cameras — Assignment 7D

**Status:** Implemented — pending human visual acceptance. Phase 7 remains in progress; Phase 8 has not started.

## Frontend integration

The manual Analyze Journey action starts `POST /api/cameras/nearest` alongside the unchanged `POST /api/trips/analyze` request. The camera request uses the canonical selected destination and its own abort controller, monotonically increasing identity, and full journey request key. Origin/destination edits, route regeneration, selected-route changes, new analysis, and unmount clear or invalidate camera state. A late response cannot restore an obsolete result. Camera failures only update camera state and do not replace road/weather analysis state.

The Destination Cameras section appears directly after Destination Weather in the existing intelligence panel. It presents one selected intersection, approximate destination distance, nearby-intersection context, the accepted official page link, source and licence attribution, and all returned views for that intersection. Image references are accepted only in the opaque `/api/cameras/images/{32 lowercase hex}` form. The frontend does not construct or request source JPEG URLs.

Each view preserves its provider direction label, native dimensions/aspect ratio, backend retrieval time, elapsed cache age, and stale status. Source capture time appears only if supplied; the accepted 7C contract currently leaves it unknown. Images lazy-load through the backend path. An individual load error replaces only that view with an unavailable message. The gallery supports variable view counts and switches to one column at the existing 760px breakpoint.

## Verification

- Focused frontend API and panel tests: **Passed** (14 tests); synthetic references only.
- Full frontend test suite: **Passed** (5 test files).
- TypeScript typecheck and production Vite build: **Passed**. Vite emitted its existing large-bundle advisory.
- Frontend lint: **Not run**; no lint script is configured in `frontend/package.json`.
- Focused backend camera API regression: **Passed** (16 tests). No backend files or contracts changed.
- Local FastAPI and Vite health endpoints, camera selection through the Vite `/api` proxy, and image delivery through that proxy: **Passed**.
- Bounded live camera selection: **Passed**; one Vancouver destination returned Hornby St and Robson St at approximately 79.6 m with four usable views.
- Opaque image delivery: **Passed**; one returned reference served HTTP 200 `image/jpeg`, 800×464, with `private, max-age=60, must-revalidate` and `nosniff` headers. A frame was visually inspected; its in-image timestamp is not treated as API capture-time metadata.
- Headless Chrome: desktop and narrow viewport initial-shell screenshots captured. The initial panel showed the no-analysis camera placeholder and no camera images. The map remained on its loading overlay.
- Browser journey interaction, populated gallery rendering, image-error interaction, and full responsive gallery inspection: **Not run**; browser interaction automation was unavailable. Human visual acceptance remains required.

The Vite proxy and endpoint smoke checks do not establish permission for camera-image reuse. Existing 7A image-rights uncertainty and 7C ephemeral-cache boundaries remain unchanged. No image was sent to an AI provider, and no Phase 8 work was performed.

## Human acceptance still required

Verify the complete journey flow, directional labels, source context, freshness wording, partial/unavailable/error states, destination and route invalidation, late-response behavior, image failures, and desktop/mobile gallery layout in a browser. In particular, confirm that stale or obsolete images cannot appear after changing the destination or selected route. Phase 7 must remain pending until these visual checks are accepted.
