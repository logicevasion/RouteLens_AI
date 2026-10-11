"""Offline tests for projected selected-route event relevance."""

import json
from pathlib import Path

import pytest
from pyproj import Transformer

from app.road_ahead import DATASETS, CityEvent, _normalize_record
from app.route_relevance import (
    DEFAULT_NEARBY_DISTANCE_METERS,
    DEFAULT_NEARBY_LIMIT,
    PROJECTED_CRS,
    RouteGeometryError,
    match_route_events,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
VANCOUVER_ROUTE = {
    "type": "LineString",
    "coordinates": [[-123.13, 49.28], [-123.12, 49.28]],
}


def event(
    source_record_id: str,
    geometry: dict | None,
    *,
    dataset: str = "closures",
    latitude: float | None = 49.28,
    longitude: float | None = -123.125,
    **metadata,
) -> CityEvent:
    dataset_id = f"road-ahead-{dataset}"
    return CityEvent(
        id=f"{dataset_id}:{source_record_id}",
        source="City of Vancouver Road Ahead",
        source_dataset_id=dataset_id,
        source_record_id=source_record_id,
        event_type="construction" if dataset == "construction" else "road_closure",
        title=f"Event {source_record_id}",
        geometry=geometry,
        latitude=latitude,
        longitude=longitude,
        source_url=f"https://example.test/{source_record_id}",
        source_metadata=metadata,
    )


def line(coords: list[list[float]]) -> dict:
    return {"type": "LineString", "coordinates": coords}


def parallel_line(latitude: float, name: str) -> CityEvent:
    return event(name, line([[-123.13, latitude], [-123.12, latitude]]))


def test_linestring_crossing_is_direct_and_preserves_event() -> None:
    source = event(
        "crossing",
        line([[-123.125, 49.27], [-123.125, 49.29]]),
        comp_date="unknown",
        nested={"retained": True},
    )
    original_geometry = source.geometry.copy()

    result = match_route_events(VANCOUVER_ROUTE, [source])

    assert len(result.direct_overlaps) == 1
    assert result.matches[0].classification == "direct_overlap"
    assert result.matches[0].distance_meters == 0
    assert result.matches[0].event is source
    assert source.geometry == original_geometry
    assert source.source_record_id == "crossing"
    assert source.source_url == "https://example.test/crossing"
    assert source.source_metadata["nested"]["retained"] is True


def test_linestring_nearby_and_far_are_classified_by_geometry_distance() -> None:
    nearby = parallel_line(49.281, "near")
    far = parallel_line(49.29, "far")

    result = match_route_events(VANCOUVER_ROUTE, [nearby, far], nearby_distance_meters=150)

    assert [match.event.id for match in result.matches] == [nearby.id]
    assert result.matches[0].classification == "nearby"
    assert 100 < result.matches[0].distance_meters < 120
    assert result.unmatchable_event_ids == ()


def test_multilinestring_with_crossing_component_is_one_direct_event() -> None:
    multi = {
        "type": "MultiLineString",
        "coordinates": [
            [[-123.125, 49.27], [-123.125, 49.29]],
            [[-123.15, 49.27], [-123.15, 49.29]],
        ],
    }
    result = match_route_events(VANCOUVER_ROUTE, [event("multi-cross", multi)])
    assert len(result.direct_overlaps) == 1


def test_multilinestring_without_crossing_component_can_be_nearby() -> None:
    multi = {
        "type": "MultiLineString",
        "coordinates": [
            [[-123.13, 49.281], [-123.12, 49.281]],
            [[-123.13, 49.282], [-123.12, 49.282]],
        ],
    }
    result = match_route_events(VANCOUVER_ROUTE, [event("multi-near", multi)], nearby_distance_meters=200)
    assert result.matches[0].classification == "nearby"


def test_polygon_crossing_route_is_direct() -> None:
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-123.126, 49.279], [-123.124, 49.279], [-123.124, 49.281],
            [-123.126, 49.281], [-123.126, 49.279],
        ]],
    }
    assert match_route_events(VANCOUVER_ROUTE, [event("polygon-cross", polygon)]).direct_overlaps


def test_polygon_nearby_uses_polygon_boundary_distance() -> None:
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-123.13, 49.281], [-123.12, 49.281], [-123.12, 49.282],
            [-123.13, 49.282], [-123.13, 49.281],
        ]],
    }
    match = match_route_events(VANCOUVER_ROUTE, [event("polygon-near", polygon)], nearby_distance_meters=200).matches[0]
    assert match.classification == "nearby"
    assert 100 < match.distance_meters < 120


def test_geometry_collection_mixed_components_and_multiple_intersections_are_one_event() -> None:
    collection = {
        "type": "GeometryCollection",
        "geometries": [
            line([[-123.125, 49.27], [-123.125, 49.29]]),
            {
                "type": "Polygon",
                "coordinates": [[
                    [-123.126, 49.279], [-123.124, 49.279], [-123.124, 49.281],
                    [-123.126, 49.281], [-123.126, 49.279],
                ]],
            },
        ],
    }
    result = match_route_events(VANCOUVER_ROUTE, [event("mixed", collection)])
    assert len(result.direct_overlaps) == 1
    assert result.direct_overlaps[0].event.geometry == collection


def test_representative_point_does_not_replace_full_geometry() -> None:
    distant_geometry = parallel_line(49.4, "point-is-near")
    source = event("point-is-near", distant_geometry.geometry, latitude=49.28, longitude=-123.125)
    result = match_route_events(VANCOUVER_ROUTE, [source], nearby_distance_meters=500)
    assert result.matches == ()


def test_projection_uses_longitude_latitude_and_realistic_metre_distances() -> None:
    transformer = Transformer.from_crs("EPSG:4326", PROJECTED_CRS, always_xy=True)
    x1, y1 = transformer.transform(-123.125, 49.28)
    x2, y2 = transformer.transform(-123.124, 49.28)
    # At Vancouver latitude, 0.001 degrees longitude is about 73 metres, not 111.
    assert 70 < x2 - x1 < 76
    assert abs(y2 - y1) < 1
    result = match_route_events(VANCOUVER_ROUTE, [parallel_line(49.281, "projected")], nearby_distance_meters=200)
    assert 100 < result.matches[0].distance_meters < 120


def test_null_empty_and_invalid_event_geometries_are_reported_without_crashing() -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[
            [-123.126, 49.279], [-123.124, 49.281], [-123.126, 49.281],
            [-123.124, 49.279], [-123.126, 49.279],
        ]],
    }
    malformed = {"type": "LineString", "coordinates": [[-123.12, 49.28], [float("nan"), 49.28]]}
    result = match_route_events(
        VANCOUVER_ROUTE,
        [event("null", None), event("bad", malformed), event("invalid-topology", bowtie),
         event("empty", {"type": "Polygon", "coordinates": []}),
         parallel_line(49.2805, "valid")],
        nearby_distance_meters=100,
    )
    assert result.unmatchable_event_ids == (
        "road-ahead-closures:bad",
        "road-ahead-closures:empty",
        "road-ahead-closures:invalid-topology",
        "road-ahead-closures:null",
    )
    assert {item.event_id: item.reason for item in result.unmatchable_events} == {
        "road-ahead-closures:bad": "invalid_structure",
        "road-ahead-closures:empty": "empty_geometry",
        "road-ahead-closures:invalid-topology": "invalid_topology",
        "road-ahead-closures:null": "missing_geometry",
    }
    assert [match.event.source_record_id for match in result.matches] == ["valid"]


@pytest.mark.parametrize(
    "geometry",
    [
        None,
        {"type": "Point", "coordinates": [-123.125, 49.28]},
        {"type": "LineString", "coordinates": [[-123.125, 49.28]]},
        {"type": "LineString", "coordinates": [[-123.125, 49.28], [181, 49.28]]},
        {"type": "LineString", "coordinates": [[-123.125, 49.28], [float("inf"), 49.28]]},
        {"type": "LineString", "coordinates": [[-123.125, 49.28], [-123.125, 49.28]]},
    ],
)
def test_malformed_or_unusable_selected_route_is_rejected(geometry) -> None:
    with pytest.raises(RouteGeometryError):
        match_route_events(geometry, [])


def test_nearby_sort_is_distance_then_stable_identity_even_for_equal_distances() -> None:
    events = [
        parallel_line(49.281, "z-record"),
        parallel_line(49.281, "a-record"),
        parallel_line(49.2805, "closer"),
    ]
    forward = match_route_events(VANCOUVER_ROUTE, events, nearby_distance_meters=200)
    backward = match_route_events(VANCOUVER_ROUTE, list(reversed(events)), nearby_distance_meters=200)
    expected = ["closer", "a-record", "z-record"]
    assert [match.event.source_record_id for match in forward.nearby_events] == expected
    assert [match.event.source_record_id for match in backward.nearby_events] == expected


def test_supplemental_limit_never_truncates_direct_overlaps() -> None:
    direct = [
        event(f"direct-{index:02}", line([[-123.125, 49.27], [-123.125, 49.29]]))
        for index in range(8)
    ]
    nearby = [parallel_line(49.2801 + index * 0.0001, f"near-{index:02}") for index in range(12)]
    result = match_route_events(
        VANCOUVER_ROUTE,
        direct + nearby,
        nearby_distance_meters=500,
        nearby_limit=5,
    )
    assert len(result.direct_overlaps) == 8
    assert len(result.nearby_events) == 5
    assert len(result.matches) == 13


def test_zero_nearby_limit_and_zero_matches_are_supported() -> None:
    result = match_route_events(
        VANCOUVER_ROUTE,
        [event("direct", line([[-123.125, 49.27], [-123.125, 49.29]])), parallel_line(49.281, "near")],
        nearby_limit=0,
    )
    assert len(result.direct_overlaps) == 1
    assert result.nearby_events == ()
    assert match_route_events(VANCOUVER_ROUTE, [parallel_line(49.4, "far")]).matches == ()
    assert match_route_events(VANCOUVER_ROUTE, []).matches == ()


@pytest.mark.parametrize(
    ("distance", "limit"),
    [(-1, 1), (float("nan"), 1), (float("inf"), 1), (100, -1), (100, True)],
)
def test_invalid_matching_configuration_is_rejected(distance, limit) -> None:
    with pytest.raises(ValueError):
        match_route_events(VANCOUVER_ROUTE, [], nearby_distance_meters=distance, nearby_limit=limit)


def test_duplicate_identity_is_returned_once_but_distinct_events_at_same_geometry_remain() -> None:
    geometry = line([[-123.125, 49.27], [-123.125, 49.29]])
    first = event("same", geometry)
    distinct = event("other", geometry)
    result = match_route_events(VANCOUVER_ROUTE, [first, first.model_copy(deep=True), distinct])
    assert [match.event.source_record_id for match in result.direct_overlaps] == ["other", "same"]
    assert all(match.event.source_dataset_id == first.source_dataset_id for match in result.direct_overlaps)


def test_road_ahead_and_ors_sanitized_fixtures_are_accepted() -> None:
    closures = json.loads((FIXTURE_ROOT / "road_ahead/current_road_closures.json").read_text())
    construction = json.loads((FIXTURE_ROOT / "road_ahead/projects_under_construction.json").read_text())
    route = json.loads((FIXTURE_ROOT / "openrouteservice/driving_richmond_to_downtown.geojson").read_text())
    route_geometry = route["features"][0]["geometry"]
    normalized = [
        event
        for dataset, payload in zip(DATASETS, [closures, construction], strict=True)
        for record in payload["results"]
        if (event := _normalize_record(dataset, record)) is not None
    ]

    result = match_route_events(route_geometry, normalized, nearby_distance_meters=DEFAULT_NEARBY_DISTANCE_METERS)

    assert normalized
    assert all(match.event in normalized for match in result.matches)
    assert len({match.event.id for match in result.matches}) == len(result.matches)
    assert DEFAULT_NEARBY_LIMIT == 10
