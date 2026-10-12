"""Focused geocoding and destination validation endpoints."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.analysis import JourneyAnalysis, Trip, analyze_journey
from app.camera_images import (
    CameraImageConfigurationError,
    DestinationCameraRequest,
    DestinationCameraResult,
    DestinationCameraService,
    NearbyCameraRequest,
    NearbyCameraResult,
)
from app.geocoding import (
    GeocodingConfigurationError,
    GeocodingError,
    GeocodingUpstreamError,
    MapTilerGeocoder,
)
from app.geography import validate_destination
from app.models import DestinationValidation, DrivingRouteRequest, DrivingRoutesResponse, Location
from app.openrouter_vision import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AdapterResult,
    CameraObservation,
    OpenRouterVisionAdapter,
)
from app.routing import (
    OpenRouteServiceRouter,
    RoutingAuthenticationError,
    RoutingConfigurationError,
    RoutingNoRouteError,
    RoutingRateLimitError,
    RoutingTimeoutError,
    RoutingUpstreamError,
)

router = APIRouter(prefix="/api")
camera_service: DestinationCameraService | None = None
vision_adapter: OpenRouterVisionAdapter | None = None


def _camera_service() -> DestinationCameraService:
    global camera_service
    if camera_service is None:
        camera_service = DestinationCameraService()
    return camera_service


def _vision_adapter() -> OpenRouterVisionAdapter:
    global vision_adapter
    if vision_adapter is None:
        vision_adapter = OpenRouterVisionAdapter()
    return vision_adapter


def _vision_failure(code: str, *, status: str = "unavailable") -> AdapterResult:
    """Return a fixed, provenance-free result for failures before adapter validation."""
    return AdapterResult(
        observation=CameraObservation(
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
            status=status,
            failure_code=code,
        )
    )


@router.get("/geocoding/search", response_model=list[Location])
async def search_locations(
    q: str = Query(min_length=2, max_length=200),
) -> list[Location]:
    """Return normalized suggestions using Metro Vancouver as search proximity."""
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Query must contain at least 2 characters.")
    try:
        return await MapTilerGeocoder().search(query)
    except GeocodingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except GeocodingUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    except GeocodingError:
        raise HTTPException(status_code=502, detail="Location search is temporarily unavailable.") from None


@router.post("/locations/validate-destination", response_model=DestinationValidation)
async def validate_selected_destination(location: Location) -> DestinationValidation:
    """Validate a canonical destination against the municipal boundary."""
    return validate_destination(location)


@router.post("/routes/driving", response_model=DrivingRoutesResponse)
async def get_driving_routes(request: DrivingRouteRequest) -> DrivingRoutesResponse:
    """Return available ORS driving candidates for canonical selected places."""
    validation = validate_destination(request.destination)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_destination",
                "message": validation.reason or "Destination is outside the supported area.",
            },
        )

    try:
        candidates = await OpenRouteServiceRouter().routes(request.origin, request.destination)
    except RoutingConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "routing_not_configured", "message": str(error)},
        ) from None
    except RoutingAuthenticationError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "routing_authentication_failed", "message": str(error)},
        ) from None
    except RoutingRateLimitError as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "routing_rate_limited", "message": str(error)},
        ) from None
    except RoutingNoRouteError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "no_route_found", "message": str(error)},
        ) from None
    except RoutingTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail={"code": "routing_timeout", "message": str(error)},
        ) from None
    except RoutingUpstreamError as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "routing_provider_unavailable", "message": str(error)},
        ) from None

    return DrivingRoutesResponse(routes=candidates)


@router.post("/trips/analyze", response_model=JourneyAnalysis)
async def analyze_trip(trip: Trip) -> JourneyAnalysis:
    """Analyze municipal and regional road evidence against the selected route."""
    try:
        return await analyze_journey(trip)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_journey", "message": str(error)},
        ) from None


@router.post("/cameras/nearest", response_model=DestinationCameraResult)
async def nearest_destination_camera(request: DestinationCameraRequest) -> DestinationCameraResult:
    """Retrieve current validated camera views for a canonical Vancouver destination."""
    try:
        return await _camera_service().nearest(request.destination)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_destination", "message": str(error)},
        ) from None
    except CameraImageConfigurationError:
        raise HTTPException(
            status_code=503,
            detail={"code": "camera_configuration_invalid", "message": "Camera retrieval is unavailable."},
        ) from None


@router.post("/cameras/observe", response_model=AdapterResult)
async def observe_destination_cameras(trip: Trip) -> AdapterResult:
    """Return internal vision evidence for the backend-selected destination intersection."""
    service = _camera_service()
    try:
        selection = await service.nearest(trip.destination)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_destination", "message": str(error)},
        ) from None
    except CameraImageConfigurationError:
        return _vision_failure("configuration_missing")

    # Selection and request travel together through this stateless operation. A
    # changed or substituted destination cannot reuse the selection's frames.
    if selection.destination != trip.destination:
        return _vision_failure("journey_context_mismatch", status="error")

    catalogue_result = await service.catalogue_store.get_catalogue()
    return await _vision_adapter().analyze_selected_intersection(
        selection,
        catalogue_result.catalogue,
        service.image_store,
    )


@router.post("/cameras/nearby", response_model=NearbyCameraResult)
async def nearby_destination_cameras(request: NearbyCameraRequest) -> NearbyCameraResult:
    """Return nearby official camera catalogue metadata without fetching images."""
    try:
        return await _camera_service().nearby(
            request.destination, request.selected_intersection_id
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_destination", "message": str(error)},
        ) from None


@router.get("/cameras/images/{image_reference}")
async def get_camera_image(image_reference: str):
    """Serve only a verified current frame mapped to an accepted catalogue view."""
    service = _camera_service()
    catalogue = await service.catalogue_store.get_catalogue()
    frame = service.image_store.get_by_reference(catalogue, image_reference)
    if frame is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "camera_image_unavailable", "message": "Camera image is unavailable."},
        )
    metadata, body = frame
    return Response(
        content=body,
        media_type=metadata.content_type,
        headers={
            "Cache-Control": "private, max-age=60, must-revalidate",
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(len(body)),
        },
    )
