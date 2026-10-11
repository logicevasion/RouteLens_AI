"""Road Ahead journey-analysis orchestration and API contract tests."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.detail_enrichment import DetailEnrichment
from app.main import app
from app.road_ahead import DATASETS, CityEvent, RoadAheadResult, SourceStatus, _normalize_record
from app.routing import normalize_response

ROUTE = {"type": "LineString", "coordinates": [[-123.12, 49.27], [-123.11, 49.28]]}
FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"


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
                     success=closures, available=closures),
        SourceStatus(source="City of Vancouver Road Ahead", dataset_id=DATASETS[1].dataset_id,
                     success=construction, available=construction),
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
    assert "partially available" in body["summary"]
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
    assert "No Road Ahead events were identified" in response.json()["summary"]


def test_both_sources_unavailable_is_distinct_from_empty_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get_data():
        return RoadAheadResult(events=[], source_statuses=source_statuses(False, False))
    monkeypatch.setattr("app.analysis.get_road_ahead_data", get_data)
    monkeypatch.setattr("app.analysis.RoadAheadDetailEnricher", lambda: FakeEnricher())
    response = api(payload())
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["findings"] == []
    assert response.json()["summary"] == "Road Ahead data is unavailable for this analysis."


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
