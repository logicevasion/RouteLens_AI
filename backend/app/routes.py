"""Focused geocoding and destination validation endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.geocoding import (
    GeocodingConfigurationError,
    GeocodingError,
    GeocodingUpstreamError,
    MapTilerGeocoder,
)
from app.geography import validate_destination
from app.models import DestinationValidation, Location

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
