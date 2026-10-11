"""Road Ahead journey-analysis orchestration and API contract tests."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.detail_enrichment import DetailEnrichment
from app.drivebc_open511 import Open511Error, Open511Result, normalize_event
from app.eccc_swob import (
    ATTRIBUTION,
    PrecipitationAccumulation,
    RegionalSwobResult,
    SelectedStationObservation,
    StationObservation,
    SwobDiagnostics,
    SwobSourceStatus,
)
from app.main import app
from app.openweather import (
    CurrentWeather,
    CurrentWeatherResult,
    ForecastCoverage,
    ForecastInterval,
    ForecastWeatherResult,
    OpenWeatherResult,
    WeatherCondition,
    WeatherSourceStatus,
)
from app.road_ahead import (
    DATASETS,
    CityEvent,
    RoadAheadError,
    RoadAheadResult,
    SourceStatus,
    _normalize_record,
)
from app.routing import normalize_response

ROUTE = {"type": "LineString", "coordinates": [[-123.12, 49.27], [-123.11, 49.28]]}
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
OPEN511_FIXTURE_ROOT = FIXTURE_ROOT / "open511"
ANALYSIS_OPEN511_ID = "open511-greater-vancouver-active"


def event(record_id: str, coordinates: list[list[float]], dataset: str = "road-ahead-current-road-closures") -> CityEvent:
    return CityEvent(
        id=f"{dataset}:{record_id}",
        source="City of Vancouver Road Ahead",
        source_dataset_id=dataset,
        source_record_id=record_id,
        event_type="road_closure" if "closures" in dataset else "construction",
        title=record_id,
        geometry={"type": "LineString", "coordinates": coordinates},
        source_url=None,
    )


def source_statuses(closures: bool = True, construction: bool = True) -> list[SourceStatus]:
    return [
        SourceStatus(source="City of Vancouver Road Ahead", dataset_id=DATASETS[0].dataset_id,
                     success=closures, available=closures, error=None if closures else "temporarily unavailable"),
        SourceStatus(source="City of Vancouver Road Ahead", dataset_id=DATASETS[1].dataset_id,
                     success=construction, available=construction, error=None if construction else "temporarily unavailable"),
    ]


def payload(*, destination: dict | None = None) -> dict:
    return {
        "origin": {"name": "Richmond", "latitude": 49.163168, "longitude": -123.137414},
        "destination": destination or {"name": "Vancouver City Hall", "latitude": 49.263, "longitude": -123.114},
        "mode": "drive",
        "selected_route": {
            "candidate_id": "route-2",
            "geometry": ROUTE,
            "distance_meters": 7100,
            "duration_seconds": 900,
            "label": "Alternative 2",
        },
    }


def api(payload_value: object) -> httpx.Response:
    async def request() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/trips/analyze", json=payload_value)

    return asyncio.run(request())


def open511_status(*, available: bool = True, stale: bool = False) -> SourceStatus:
    return SourceStatus(
        source="DriveBC Open511", dataset_id=ANALYSIS_OPEN511_ID,
        success=available and not stale, available=available, stale=stale,
        cache_hit=stale, cache_age_seconds=900 if stale else 0,
        error="Serving the last valid snapshot." if stale else None,
    )


def regional_events() -> list[CityEvent]:
    payload_value = json.loads((OPEN511_FIXTURE_ROOT / "regional_active_observed.json").read_text())
    return [normalize_event(record, dataset_id=ANALYSIS_OPEN511_ID) for record in payload_value["events"]]


@pytest.fixture(autouse=True)
def default_open511(monkeypatch: pytest.MonkeyPatch):
    """Keep legacy Road Ahead tests offline unless they explicitly inject Open511 data."""
    async def get_data():
        return Open511Result(events=[], source_status=open511_status())
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_data)

    async def no_openweather(trip, evaluation_time):
        return OpenWeatherResult(
            current=CurrentWeatherResult(status=WeatherSourceStatus(
                dataset_id="onecall4_current", success=False, available=False, error="offline test"
            )),
            forecast=ForecastWeatherResult(status=WeatherSourceStatus(
                dataset_id="onecall4_timeline_15min", success=False, available=False, error="offline test"
            )),
        )
    async def no_swob(trip, evaluation_time):
        return (
            RegionalSwobResult(
                diagnostics=SwobDiagnostics(),
                status=SwobSourceStatus(success=False, available=False, error="offline test"),
            ),
            [],
        )
    monkeypatch.setattr("app.analysis._destination_openweather", no_openweather)
    monkeypatch.setattr("app.analysis._destination_swob", no_swob)


class FakeEnricher:
    def __init__(self):
        self.event_ids: list[str] = []

    async def enrich_many(self, events: list[CityEvent]) -> list[DetailEnrichment]:
        self.event_ids = [event.id for event in events]
        return [DetailEnrichment(event_id=event.id, source_url=event.source_url, availability="unavailable", error="invalid_source_url") for event in events]


def test_analysis_matches_only_route_relevant_events_and_keeps_partial_dataset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    direct = event("direct", [[-123.12, 49.27], [-123.11, 49.28]])
    nearby = event("nearby", [[-123.109, 49.28], [-123.108, 49.281]], DATASETS[1].dataset_id)
    distant = event("distant", [[-123.3, 49.3], [-123.31, 49.31]])
    data = RoadAheadResult(events=[direct, nearby, distant], source_statuses=source_statuses(True, False))
    enricher = FakeEnricher()
    async def get_data():
        return data
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: enricher)

    response = api(payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    assert [finding["event"]["id"] for finding in body["findings"]] == [direct.id, nearby.id]
    assert [finding["classification"] for finding in body["findings"]] == ["direct_overlap", "nearby"]
    assert body["findings"][1]["distance_meters"] > 0
    assert body["source_statuses"][0]["available"] is True
    assert body["source_statuses"][1]["available"] is False
    assert "Coverage is partial" in body["summary"]
    assert enricher.event_ids == [direct.id, nearby.id]
    assert body["findings"][0]["event"]["geometry"] == direct.geometry


def test_available_data_with_no_relevant_events_is_an_honest_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_data():
        return RoadAheadResult(events=[], source_statuses=source_statuses())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    response = api(payload())
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert response.json()["findings"] == []
    assert "No route-relevant road events were identified" in response.json()["summary"]


def test_both_sources_unavailable_is_distinct_from_empty_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_data():
        return RoadAheadResult(events=[], source_statuses=source_statuses(False, False))
    async def get_open511():
        return Open511Result(events=[], source_status=open511_status(available=False))
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_data)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    response = api(payload())
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["findings"] == []
    assert "no source datasets could be retrieved" in response.json()["summary"]


@pytest.mark.parametrize("bad", [
    {"geometry": {"type": "Point", "coordinates": [-123, 49]}},
    {"geometry": {"type": "LineString", "coordinates": [[-123, 49]]}},
    {"geometry": {"type": "LineString", "coordinates": [[181, 49], [-123, 49]]}},
    {"geometry": {"type": "LineString", "coordinates": [[-123, 49], [-123, 49]]}},
])
def test_invalid_selected_route_is_rejected(bad: dict) -> None:
    value = payload()
    value["selected_route"].update(bad)
    assert api(value).status_code == 422


def test_missing_route_and_wrong_mode_are_rejected() -> None:
    value = payload()
    del value["selected_route"]
    assert api(value).status_code == 422
    value = payload()
    value["mode"] = "transit"
    assert api(value).status_code == 422


def test_outside_vancouver_destination_is_rejected_before_source_access(monkeypatch: pytest.MonkeyPatch) -> None:
    async def should_not_fetch():
        raise AssertionError("destination validation must precede source access")
    monkeypatch.setattr("app.analysis.get_road_ahead_data", should_not_fetch)
    assert api(payload(destination={"name": "Burnaby", "latitude": 49.25, "longitude": -122.98})).status_code == 422


def test_route_geometry_validation_model_rejects_oversized_coordinate_list() -> None:
    value = payload()
    value["selected_route"]["geometry"] = {
        "type": "LineString", "coordinates": [[-123.1, 49.2], [-123.2, 49.3]] * 10_001,
    }
    assert api(value).status_code == 422


def test_fixture_route_analysis_uses_accepted_ors_and_road_ahead_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    route_payload = json.loads((FIXTURE_ROOT / "openrouteservice/driving_richmond_to_downtown.geojson").read_text())
    route_candidate = normalize_response(route_payload)[0]
    normalized_events: list[CityEvent] = []
    for dataset, filename in zip(DATASETS, ["current_road_closures.json", "projects_under_construction.json"], strict=True):
        payload_value = json.loads((FIXTURE_ROOT / "road_ahead" / filename).read_text())
        normalized_events.extend(
            event_value
            for record in payload_value["results"]
            if (event_value := _normalize_record(dataset, record)) is not None
        )
    source_states = source_statuses()
    async def get_data():
        return RoadAheadResult(events=normalized_events, source_statuses=source_states)
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_data)

    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    request = payload()
    request["selected_route"] = {
        "candidate_id": route_candidate.id,
        "geometry": route_candidate.geometry,
        "distance_meters": route_candidate.distance_meters,
        "duration_seconds": route_candidate.duration_seconds,
        "label": route_candidate.label,
    }
    response = api(request)
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert [finding["event"]["id"] for finding in response.json()["findings"]] == [
        "road-ahead-current-road-closures:closure-row-001"
    ]
    assert response.json()["findings"][0]["classification"] == "direct_overlap"


def test_combined_analysis_separates_legacy_road_ahead_and_drivebc_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    ra_direct = event("ra-direct", [[-123.12, 49.27], [-123.11, 49.28]])
    road_data = RoadAheadResult(events=[ra_direct], source_statuses=source_statuses())
    point_on_route = CityEvent(
        id=f"{ANALYSIS_OPEN511_ID}:point-on-route", source="DriveBC Open511",
        source_dataset_id=ANALYSIS_OPEN511_ID, source_record_id="point-on-route",
        event_type="INCIDENT", title="Point event", status="ACTIVE", severity="MINOR",
        geometry={"type": "Point", "coordinates": [-123.12, 49.27]},
        source_metadata={"event_subtypes": ["INCIDENT"], "roads": [{"name": "Sample Road", "direction": "BOTH"}],
                        "schedule": {"intervals": ["unknown"]}},
        attribution="DriveBC test attribution",
    )
    line_direct = CityEvent(
        id=f"{ANALYSIS_OPEN511_ID}:line-direct", source="DriveBC Open511",
        source_dataset_id=ANALYSIS_OPEN511_ID, source_record_id="line-direct", event_type="CONSTRUCTION",
        title="Line event", status="ACTIVE", severity="UNKNOWN",
        geometry={"type": "LineString", "coordinates": [[-123.115, 49.26], [-123.115, 49.29]]},
        source_metadata={"event_subtypes": ["PLANNED_EVENT"], "roads": [], "schedule": None},
        attribution="DriveBC test attribution",
    )
    distant = CityEvent(
        id=f"{ANALYSIS_OPEN511_ID}:distant", source="DriveBC Open511",
        source_dataset_id=ANALYSIS_OPEN511_ID, source_record_id="distant", event_type="CLOSURE",
        title="Distant map event", geometry={"type": "Point", "coordinates": [-123.3, 49.4]},
        attribution="DriveBC test attribution",
    )

    async def get_road(): return road_data
    async def get_open511():
        return Open511Result(events=[point_on_route, distant, line_direct], source_status=open511_status())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())

    response = api(payload())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert len(body["source_statuses"]) == 3
    assert [finding["event"]["id"] for finding in body["findings"]] == [ra_direct.id]
    assert body["findings"][0]["detail"]["availability"] == "unavailable"
    drivebc = body["drivebc_findings"]
    assert [finding["event"]["source_record_id"] for finding in drivebc] == ["line-direct", "point-on-route"]
    assert [finding["classification"] for finding in drivebc] == ["direct_overlap", "nearby"]
    assert [finding["geometry_basis"] for finding in drivebc] == ["linestring_intersection", "point_proximity"]
    assert all(finding["enrichment_applicability"] == "not_applicable" for finding in drivebc)
    assert drivebc[1]["distance_meters"] == pytest.approx(0, abs=0.1)
    assert drivebc[1]["source_evidence"]["current_impact"] == "not_established"
    assert drivebc[1]["source_evidence"]["direction_assessment"] == "undetermined"
    assert drivebc[1]["event"]["attribution"] == "DriveBC test attribution"
    assert [event["source_record_id"] for event in body["regional_events"]] == [
        "point-on-route", "distant", "line-direct",
    ]
    assert all(item["event"]["source"] == "City of Vancouver Road Ahead" for item in body["findings"])
    assert "Road Ahead reports 1 event" in body["summary"]
    assert "DriveBC reports 1 regional LineString event" in body["summary"]
    assert "DriveBC identifies 1 regional event nearby" in body["summary"]


@pytest.mark.parametrize("failed_source", ["road", "open511"])
def test_source_failure_does_not_erase_other_source_findings(monkeypatch: pytest.MonkeyPatch, failed_source: str) -> None:
    ra = event("ra", [[-123.12, 49.27], [-123.11, 49.28]])
    regional = regional_events()
    route_point = CityEvent(
        id=f"{ANALYSIS_OPEN511_ID}:point", source="DriveBC Open511", source_dataset_id=ANALYSIS_OPEN511_ID,
        source_record_id="point", event_type="INCIDENT", title="Point near route",
        geometry={"type": "Point", "coordinates": [-123.12, 49.27]},
    )
    async def get_road():
        if failed_source == "road": raise RoadAheadError("sanitized road outage")
        return RoadAheadResult(events=[ra], source_statuses=source_statuses())
    async def get_open511():
        if failed_source == "open511": raise Open511Error("sanitized Open511 outage")
        return Open511Result(events=[route_point, *regional], source_status=open511_status())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())

    body = api(payload()).json()
    assert body["status"] == "partial"
    assert len(body["findings"]) == (0 if failed_source == "road" else 1)
    assert len(body["drivebc_findings"]) == (1 if failed_source == "road" else 0)
    assert body["source_statuses"][0]["available"] is (failed_source != "road")
    assert body["source_statuses"][2]["available"] is (failed_source != "open511")
    assert "Coverage is partial" in body["summary"]
    assert bool(body["regional_events"]) is (failed_source != "open511")


def test_one_road_ahead_dataset_failure_keeps_other_datasets_and_open511(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_road(): return RoadAheadResult(events=[], source_statuses=source_statuses(True, False))
    async def get_open511(): return Open511Result(events=[], source_status=open511_status())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    body = api(payload()).json()
    assert body["status"] == "partial"
    assert [status["available"] for status in body["source_statuses"]] == [True, False, True]
    assert body["source_statuses"][1]["error"] == "temporarily unavailable"


def test_stale_valid_source_snapshots_remain_available_and_marked_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    road_states = [status.model_copy(update={"success": False, "stale": True, "available": True}) for status in source_statuses()]
    stale_road_event = event("stale-road", [[-123.12, 49.27], [-123.11, 49.28]])
    async def get_road(): return RoadAheadResult(events=[stale_road_event], source_statuses=road_states)
    async def get_open511(): return Open511Result(events=regional_events(), source_status=open511_status(stale=True))
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    body = api(payload()).json()
    assert body["status"] == "available"
    assert [status["stale"] for status in body["source_statuses"]] == [True, True, True]
    assert [status["available"] for status in body["source_statuses"]] == [True, True, True]
    assert len(body["regional_events"]) == 2
    assert [item["event"]["id"] for item in body["findings"]] == [stale_road_event.id]


def test_unmatchable_diagnostics_keep_source_and_dataset_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    ra_bad = event("bad-ra", [])
    ra_bad.geometry = {"type": "Point", "coordinates": [-123.12, 49.27]}
    drivebc_bad = CityEvent(
        id=f"{ANALYSIS_OPEN511_ID}:bad-bc", source="DriveBC Open511",
        source_dataset_id=ANALYSIS_OPEN511_ID, source_record_id="bad-bc", event_type="INCIDENT",
        title="Unsupported collection", geometry={"type": "MultiPoint", "coordinates": []},
    )
    async def get_road(): return RoadAheadResult(events=[ra_bad], source_statuses=source_statuses())
    async def get_open511(): return Open511Result(events=[drivebc_bad], source_status=open511_status())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    body = api(payload()).json()
    assert body["findings"] == body["drivebc_findings"] == []
    assert {(item["source"], item["dataset_id"], item["event_id"]) for item in body["unmatchable_events"]} == {
        ("City of Vancouver Road Ahead", DATASETS[0].dataset_id, ra_bad.id),
        ("DriveBC Open511", ANALYSIS_OPEN511_ID, drivebc_bad.id),
    }


def test_all_source_datasets_unavailable_is_not_a_clear_route(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_road(): return RoadAheadResult(events=[], source_statuses=source_statuses(False, False))
    async def get_open511(): return Open511Result(events=[], source_status=open511_status(available=False))
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_road)
    monkeypatch.setattr("app.analysis.get_drivebc_open511_data", get_open511)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    body = api(payload()).json()
    assert body["status"] == "unavailable"
    assert body["findings"] == body["drivebc_findings"] == body["regional_events"] == []
    assert "unavailable" in body["summary"]
    assert "clear" not in body["summary"].lower()


def test_weather_contract_keeps_partial_sources_destination_and_route_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    at = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    captured: dict[str, object] = {}
    current = CurrentWeather(
        requested_coordinates={"latitude": 49.263, "longitude": -123.114}, observed_at=at,
        fetched_at=at, temperature_c=8.5, condition=WeatherCondition(group="Clouds", description="overcast clouds"),
    )
    async def weather(trip, evaluation_time):
        captured["destination"] = (trip.destination.latitude, trip.destination.longitude)
        captured["route"] = trip.selected_route.candidate_id
        return OpenWeatherResult(
            current=CurrentWeatherResult(weather=current, status=WeatherSourceStatus(
                dataset_id="onecall4_current", success=True, available=True, stale=True,
                cache_age_seconds=900, fetched_at=at,
            )),
            forecast=ForecastWeatherResult(
                intervals=[ForecastInterval(
                    requested_coordinates=current.requested_coordinates, forecast_at=at,
                    fetched_at=at, precipitation_probability_pct=None, temperature_c=8.0,
                )],
                coverage=ForecastCoverage(
                    evaluation_time=at, window_end=at.replace(hour=15), expected_interval_count=12,
                    returned_interval_count=1, missing_intervals=[at.replace(minute=15)], continuous=False,
                ),
                status=WeatherSourceStatus(dataset_id="onecall4_timeline_15min", success=True, available=True),
            ),
        )

    observation = StationObservation(
        station_id="C123456789", station_name="Vancouver Harbour", source_record_id="sample-1",
        latitude=49.29, longitude=-123.12, observed_at=at, retrieved_at=at,
        precipitation=[PrecipitationAccumulation(value=0.0, unit="mm", source_field="pcpn_amt_pst10mts", interval_seconds=600)],
        attribution=ATTRIBUTION,
    )
    selected = SelectedStationObservation(
        observation=observation, distance_meters=3200, observation_age_seconds=1080,
        observation_stale=False, cache_stale=True, useful_measurements=["precipitation"], selection_reason="nearby",
    )
    async def swob(trip, evaluation_time):
        captured["swob_destination"] = (trip.destination.latitude, trip.destination.longitude)
        return (
            RegionalSwobResult(observations=[observation], diagnostics=SwobDiagnostics(),
                              status=SwobSourceStatus(success=False, available=True, stale=True, cache_age_seconds=900)),
            [selected],
        )
    monkeypatch.setattr("app.analysis._destination_openweather", weather)
    monkeypatch.setattr("app.analysis._destination_swob", swob)
    road = event("still-visible", [[-123.12, 49.27], [-123.11, 49.28]])
    async def road_data(): return RoadAheadResult(events=[road], source_statuses=source_statuses())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", road_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())

    body = api(payload()).json()
    weather_body = body["destination_weather"]
    assert captured["destination"] == captured["swob_destination"] == (49.263, -123.114)
    assert captured["route"] == body["trip"]["selected_route"]["candidate_id"] == "route-2"
    assert [finding["event"]["id"] for finding in body["findings"]] == [road.id]
    assert weather_body["openweather_current"]["status"]["stale"] is True
    assert weather_body["openweather_forecast"]["coverage"]["continuous"] is False
    assert weather_body["openweather_forecast"]["intervals"][0]["precipitation_probability_pct"] is None
    assert weather_body["eccc_observations"][0]["distance_meters"] == 3200
    assert weather_body["eccc_observations"][0]["observation_age_seconds"] == 1080
    assert weather_body["eccc_observations"][0]["observation"]["precipitation"][0]["interval_seconds"] == 600


def test_all_weather_unavailable_keeps_successful_road_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    road = event("weather-does-not-mask-road", [[-123.12, 49.27], [-123.11, 49.28]])
    async def road_data(): return RoadAheadResult(events=[road], source_statuses=source_statuses())
    monkeypatch.setattr("app.analysis.get_road_ahead_data", road_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    body = api(payload()).json()
    weather_body = body["destination_weather"]
    assert [finding["event"]["id"] for finding in body["findings"]] == [road.id]
    assert weather_body["openweather_current"]["status"]["available"] is False
    assert weather_body["openweather_forecast"]["status"]["available"] is False
    assert weather_body["eccc_status"]["available"] is False


@pytest.mark.parametrize("failed_product", ["current", "forecast"])
def test_openweather_products_are_reported_independently(monkeypatch: pytest.MonkeyPatch, failed_product: str) -> None:
    at = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    current_available = failed_product != "current"
    forecast_available = failed_product != "forecast"
    current_status = WeatherSourceStatus(
        dataset_id="onecall4_current", success=current_available, available=current_available,
        error=None if current_available else "upstream unavailable",
    )
    forecast_status = WeatherSourceStatus(
        dataset_id="onecall4_timeline_15min", success=forecast_available, available=forecast_available,
        error=None if forecast_available else "upstream unavailable",
    )
    async def weather(trip, evaluation_time):
        return OpenWeatherResult(
            current=CurrentWeatherResult(
                weather=CurrentWeather(requested_coordinates={"latitude": trip.destination.latitude,
                    "longitude": trip.destination.longitude}, observed_at=at, fetched_at=at) if current_available else None,
                status=current_status,
            ),
            forecast=ForecastWeatherResult(
                intervals=[], coverage=None, status=forecast_status,
            ),
        )
    async def swob(trip, evaluation_time):
        return (
            RegionalSwobResult(diagnostics=SwobDiagnostics(),
                status=SwobSourceStatus(success=True, available=True)),
            [],
        )
    monkeypatch.setattr("app.analysis._destination_openweather", weather)
    monkeypatch.setattr("app.analysis._destination_swob", swob)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    weather_body = api(payload()).json()["destination_weather"]
    assert weather_body["openweather_current"]["status"]["available"] is current_available
    assert weather_body["openweather_forecast"]["status"]["available"] is forecast_available
    assert weather_body["eccc_status"]["available"] is True
    assert weather_body["eccc_observations"] == []


@pytest.mark.parametrize("failed_source", ["openweather", "swob"])
def test_unexpected_weather_task_exception_does_not_fail_road_analysis(
    monkeypatch: pytest.MonkeyPatch, failed_source: str
) -> None:
    road = event("provider-error-isolated", [[-123.12, 49.27], [-123.11, 49.28]])
    async def road_data(): return RoadAheadResult(events=[road], source_statuses=source_statuses())
    async def fail(*args, **kwargs): raise RuntimeError("unexpected provider failure")
    monkeypatch.setattr("app.analysis.get_road_ahead_data", road_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    monkeypatch.setattr(
        "app.analysis._destination_openweather" if failed_source == "openweather" else "app.analysis._destination_swob",
        fail,
    )
    response = api(payload())
    assert response.status_code == 200
    body = response.json()
    assert [finding["event"]["id"] for finding in body["findings"]] == [road.id]
    if failed_source == "openweather":
        assert body["destination_weather"]["openweather_current"]["status"]["available"] is False
        assert body["destination_weather"]["openweather_forecast"]["status"]["available"] is False
    else:
        assert body["destination_weather"]["eccc_status"]["available"] is False
