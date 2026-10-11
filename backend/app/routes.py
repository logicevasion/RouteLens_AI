"""Focused geocoding and destination validation endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.geocoding import (
    GeocodingConfigurationError,
    GeocodingError,
    GeocodingUpstreamError,
    MapTilerGeocoder,
)
from app.geography import validate_destination
from app.models import DestinationValidation, DrivingRouteRequest, DrivingRoutesResponse, Location
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
