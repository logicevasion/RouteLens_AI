"""Offline Open511 route-relevance and selected-route fixture checks."""

import json
from itertools import pairwise
from pathlib import Path

import pytest
from pyproj import Transformer

from app.drivebc_open511 import normalize_event
from app.drivebc_relevance import match_drivebc_events
from app.road_ahead import CityEvent
from app.route_relevance import PROJECTED_CRS, RouteGeometryError

ROOT = Path(__file__).resolve().parents[2]
ROUTE = {"type": "LineString", "coordinates": [[-123.13, 49.28], [-123.12, 49.28]]}


def event(event_id: str, geometry: dict | None, **metadata):
    record = {
        "id": event_id,
        "headline": "Synthetic event",
        "status": "ACTIVE",
        "event_type": metadata.pop("event_type", "UNFAMILIAR_TYPE"),
        "severity": metadata.pop("severity", "UNKNOWN"),
        "geography": geometry,
        **metadata,
    }
    normalized = normalize_event(
        record,
        dataset_id="fixture-dataset",
    )
    if normalized is not None:
        return normalized
    return CityEvent(
        id=f"fixture-dataset:{event_id}",
        source="DriveBC Open511",
        source_dataset_id="fixture-dataset",
        source_record_id=event_id,
        event_type=record["event_type"],
        title=record["headline"],
        geometry=geometry,
        severity=record.get("severity"),
        status=record["status"],
        source_metadata={key: value for key, value in record.items() if key != "geography"},
    )


def line(coords: list[list[float]]) -> dict:
    return {"type": "LineString", "coordinates": coords}


def point(lon: float, lat: float) -> dict:
    return {"type": "Point", "coordinates": [lon, lat]}


def test_linestring_direct_nearby_and_distant_use_projected_geometry() -> None:
    direct = event("line-direct", line([[-123.125, 49.27], [-123.125, 49.29]]))
    nearby = event("line-near", line([[-123.13, 49.281], [-123.12, 49.281]]))
    distant = event("line-far", line([[-123.13, 49.29], [-123.12, 49.29]]))

    result = match_drivebc_events(ROUTE, [distant, nearby, direct])

    assert [m.event.source_record_id for m in result.direct_overlaps] == ["line-direct"]
    assert [m.event.source_record_id for m in result.nearby_events] == ["line-near"]
    assert result.nearby_events[0].geometry_basis == "linestring_proximity"
    assert 100 < result.nearby_events[0].distance_meters < 120
    assert [item.event_id for item in result.excluded_events] == ["fixture-dataset:line-far"]
    assert result.unmatchable_events == ()


def test_point_on_route_remains_proximity_and_point_threshold_is_configurable() -> None:
    on_route = event("point-zero", point(-123.125, 49.28))
    within = event("point-within", point(-123.125, 49.2819))
    outside = event("point-outside", point(-123.125, 49.283))

    result = match_drivebc_events(
        ROUTE,
        [outside, on_route, within],
        point_nearby_distance_meters=220,
    )

    assert result.direct_overlaps == ()
    assert [(m.event.source_record_id, m.classification) for m in result.nearby_events] == [
        ("point-zero", "nearby"),
        ("point-within", "nearby"),
    ]
    assert result.nearby_point_events[0].distance_meters < 0.05
    assert result.nearby_point_events[0].geometry_basis == "point_proximity"
    assert result.excluded_events[0].event_id == "fixture-dataset:point-outside"


def test_point_threshold_inside_and_outside_boundaries() -> None:
    transformer = Transformer.from_crs("EPSG:4326", PROJECTED_CRS, always_xy=True)
    route_x, route_y = transformer.transform(-123.125, 49.28)
    # Construct projected offsets, then transform them back to longitude/latitude.
    inverse = Transformer.from_crs(PROJECTED_CRS, "EPSG:4326", always_xy=True)
    inside = point(*inverse.transform(route_x, route_y + 249))
    outside = point(*inverse.transform(route_x, route_y + 251))

    result = match_drivebc_events(
        ROUTE,
        [event("inside", inside), event("outside", outside)],
        point_nearby_distance_meters=250,
    )

    assert [m.event.source_record_id for m in result.nearby_events] == ["inside"]
    assert result.nearby_events[0].distance_meters == pytest.approx(249, abs=0.5)
    assert [x.event_id for x in result.excluded_events] == ["fixture-dataset:outside"]


def test_mixed_geometry_preserves_all_direct_matches_and_caps_only_nearby() -> None:
    direct = [event(f"direct-{i:02}", line([[-123.125, 49.27], [-123.125, 49.29]])) for i in range(12)]
    points = [event(f"point-{i:02}", point(-123.125, 49.28 + i * 0.0001)) for i in range(20)]
    nearby_line = event("near-line", line([[-123.13, 49.2805], [-123.12, 49.2805]]))

    result = match_drivebc_events(ROUTE, [*points, nearby_line, *direct], nearby_limit=3)

    assert len(result.direct_overlaps) == 12
    assert len(result.nearby_events) == 3
    assert len(result.matches) == 15
    assert all(m.geometry_basis == "linestring_intersection" for m in result.direct_overlaps)


def test_order_and_duplicate_identity_are_deterministic() -> None:
    records = [
        event("z-line", line([[-123.13, 49.281], [-123.12, 49.281]])),
        event("a-line", line([[-123.13, 49.281], [-123.12, 49.281]])),
        event("a-line", line([[-123.13, 49.281], [-123.12, 49.281]])),
    ]
    forward = match_drivebc_events(ROUTE, records)
    backward = match_drivebc_events(ROUTE, list(reversed(records)))
    assert [m.event.source_record_id for m in forward.matches] == ["a-line", "z-line"]
    assert [m.event.id for m in forward.matches] == [m.event.id for m in backward.matches]


@pytest.mark.parametrize(
    ("event_id", "geometry", "reason"),
    [
        ("missing", None, "missing_geometry"),
        ("bad-point", point(float("nan"), 49.28), "invalid_structure"),
        ("bad-line", line([[-123.1, 49.28]]), "invalid_structure"),
        ("unsupported", {"type": "Polygon", "coordinates": []}, "invalid_structure"),
    ],
)
def test_unmatchable_events_are_isolated_with_reason_codes(event_id, geometry, reason) -> None:
    result = match_drivebc_events(ROUTE, [event(event_id, geometry)])
    assert result.matches == ()
    assert [(item.event_id, item.reason) for item in result.unmatchable_events] == [
        (f"fixture-dataset:{event_id}", reason)
    ]


def test_invalid_selected_route_uses_phase4_route_error() -> None:
    with pytest.raises(RouteGeometryError):
        match_drivebc_events({"type": "Point", "coordinates": [-123.1, 49.2]}, [])


def test_source_metadata_and_uncertainty_are_preserved_without_impact_inference() -> None:
    source = event(
        "future-active",
        line([[-123.125, 49.27], [-123.125, 49.29]]),
        event_type="UNFAMILIAR_TYPE",
        severity="UNKNOWN",
        created="2026-10-11T08:00:00-07:00",
        updated="2026-10-11T09:00:00-07:00",
        schedule={"intervals": ["2030-03-09T15:00/2030-03-09T23:00"]},
        roads=[{"name": "Highway 1", "direction": "WEST", "state": "UNKNOWN"}],
        event_subtypes=["FUTURE_WORK"],
        description="Original source description",
    )
    original_geometry = json.loads(json.dumps(source.geometry))

    match = match_drivebc_events(ROUTE, [source]).matches[0]

    assert match.event is source
    assert match.event.geometry == original_geometry
    assert match.event.source_record_id == "future-active"
    assert match.event.source_metadata["roads"][0]["direction"] == "WEST"
    assert match.evidence.roads == ({"name": "Highway 1", "direction": "WEST", "state": "UNKNOWN"},)
    assert match.evidence.schedule == {"intervals": ["2030-03-09T15:00/2030-03-09T23:00"]}
    assert match.evidence.event_subtypes == ("FUTURE_WORK",)
    assert match.evidence.severity == "UNKNOWN"
    assert match.evidence.event_type == "UNFAMILIAR_TYPE"
    assert match.evidence.direction_assessment == "undetermined"
    assert match.evidence.temporal_applicability == "unknown"
    assert match.evidence.current_impact == "not_established"


@pytest.mark.parametrize(
    "filename",
    [
        "driving_richmond_to_downtown.geojson",
        "driving_new_westminster_station_to_downtown.geojson",
        "driving_metrotown_to_vancouver_city_hall.geojson",
    ],
)
def test_sanitized_regional_events_against_saved_ors_route(filename) -> None:
    payload = json.loads((ROOT / "fixtures/open511/regional_active_observed.json").read_text())
    events = [
        normalized
        for record in payload["events"]
        if (normalized := normalize_event(record, dataset_id="sanitized-regional")) is not None
    ]
    route_doc = json.loads((ROOT / "fixtures/openrouteservice" / filename).read_text())
    route_geometry = route_doc["features"][0]["geometry"]

    result = match_drivebc_events(route_geometry, events)

    assert len(events) == 2
    assert len(result.matches) + len(result.excluded_events) + len(result.unmatchable_events) == 2


@pytest.mark.parametrize(
    "filename",
    [
        "driving_richmond_to_downtown.geojson",
        "driving_new_westminster_station_to_downtown.geojson",
        "driving_metrotown_to_vancouver_city_hall.geojson",
    ],
)
def test_synthetic_open511_events_match_each_saved_ors_route(filename) -> None:
    route_doc = json.loads((ROOT / "fixtures/openrouteservice" / filename).read_text())
    route_geometry = route_doc["features"][0]["geometry"]
    original_route = json.loads(json.dumps(route_geometry))
    coordinates = route_geometry["coordinates"]
    segment = next(
        (start, end)
        for start, end in pairwise(coordinates)
        if start[:2] != end[:2]
    )
    start, end = segment
    midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
    source_line = event("fixture-segment-overlap", line([start[:2], end[:2]]))
    source_point = event("fixture-point-on-route", point(*midpoint))
    original_line = json.loads(json.dumps(source_line.geometry))
    original_point = json.loads(json.dumps(source_point.geometry))

    result = match_drivebc_events(route_geometry, [source_point, source_line])

    assert [(match.event.id, match.classification) for match in result.matches] == [
        (source_line.id, "direct_overlap"),
        (source_point.id, "nearby"),
    ]
    assert all(match.classification != "direct_overlap" for match in result.nearby_point_events)
    assert source_line.geometry == original_line
    assert source_point.geometry == original_point
    assert route_geometry == original_route
