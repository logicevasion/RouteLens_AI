"""City of Vancouver destination boundary validation."""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import polygonize, unary_union

from app.models import DestinationValidation, Location

BOUNDARY_DATASET = "City of Vancouver Open Data Portal: city-boundary"
BOUNDARY_PATH = Path(__file__).parent / "data" / "city-boundary.geojson"


def load_city_boundary():
    """Build the city polygon from the City's published legal boundary linework."""
    payload = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    features = payload.get("features")
    if payload.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise RuntimeError("The City of Vancouver boundary data is malformed.")

    lines = [
        shape(feature["geometry"])
        for feature in features
        if isinstance(feature, dict)
        and isinstance(feature.get("geometry"), dict)
        and feature["geometry"].get("type") in {"LineString", "MultiLineString"}
    ]
    polygons = list(polygonize(unary_union(lines))) if lines else []
    if len(polygons) != 1 or not polygons[0].is_valid:
        raise RuntimeError("The City of Vancouver boundary could not form one valid polygon.")
    return polygons[0]


CITY_OF_VANCOUVER = load_city_boundary()


def validate_destination(location: Location) -> DestinationValidation:
    """Accept points covered by the official polygon, including its boundary."""
    point = Point(location.longitude, location.latitude)
    if CITY_OF_VANCOUVER.covers(point):
        return DestinationValidation(valid=True)
    return DestinationValidation(
        valid=False,
        reason="Destination must be inside the City of Vancouver municipal boundary.",
    )
