import asyncio
import json
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.openweather import (
    DailyRequestBudget,
    OpenWeatherClient,
    OpenWeatherError,
    WeatherCoordinates,
    _ExpectedSourceFailure,
    normalize_current,
    normalize_timeline,
)

ROOT = Path(__file__).resolve().parents[2]
CURRENT_FIXTURE = json.loads((ROOT / "fixtures/openweather/onecall4_current_vancouver_phase6a.json").read_text())
TIMELINE_FIXTURE = json.loads((ROOT / "fixtures/openweather/onecall4_15min_vancouver_phase6a.json").read_text())
COORDS = WeatherCoordinates(latitude=49.2827, longitude=-123.1207)
NOW = datetime.fromtimestamp(TIMELINE_FIXTURE["data"][0]["dt"], timezone.utc)


def _record_budget_attempt(arguments):
    path, now = arguments
    try:
        DailyRequestBudget(path, limit=7).record_attempt(now)
        return True
    except _ExpectedSourceFailure:
        return False


def test_normalize_current_preserves_utc_metric_units_and_unknown_precipitation():
    current = normalize_current(CURRENT_FIXTURE, COORDS, NOW)
    assert current.observed_at == datetime.fromtimestamp(CURRENT_FIXTURE["data"][0]["dt"], timezone.utc)
    assert current.fetched_at == NOW
    assert current.temperature_c == 7.53
    assert current.wind_speed_m_s == 0.89
    assert current.visibility_m == 10000
    assert current.rain_1h_mm is None
    assert current.snow_1h_mm is None
    assert current.requested_coordinates == COORDS


def test_normalize_timeline_limits_three_hours_and_reports_intervals():
    intervals, coverage = normalize_timeline(TIMELINE_FIXTURE, COORDS, NOW, NOW)
    assert len(intervals) == 13
    assert intervals[0].forecast_at == NOW
    assert intervals[-1].forecast_at == NOW + timedelta(hours=3)
    assert all(interval.forecast_at.tzinfo == timezone.utc for interval in intervals)
    assert intervals[0].precipitation_probability_pct == 0
    assert intervals[0].rain_1h_mm is None
    assert coverage.continuous is True
    assert coverage.expected_interval_count == 13
    assert coverage.initial_page_only is True


def test_timeline_missing_and_malformed_records_are_not_fabricated():
    payload = {**TIMELINE_FIXTURE, "next": "https://example.invalid/?appid=secret"}
    payload["data"] = [
        TIMELINE_FIXTURE["data"][0],
        TIMELINE_FIXTURE["data"][0],
        {**TIMELINE_FIXTURE["data"][1], "dt": "bad"},
        TIMELINE_FIXTURE["data"][3],
    ]
    intervals, coverage = normalize_timeline(payload, COORDS, NOW, NOW)
    assert [item.forecast_at for item in intervals] == [NOW, NOW + timedelta(minutes=45)]
    assert coverage.duplicate_records == 1
    assert coverage.malformed_records == 1
    assert len(coverage.missing_intervals) == 11
    assert coverage.continuous is False
    assert "next" not in json.dumps([item.model_dump(mode="json") for item in intervals])


def test_timeline_excludes_out_of_window_and_invalid_probability():
    data = [
        {**TIMELINE_FIXTURE["data"][0], "dt": int(NOW.timestamp()) - 900},
        {**TIMELINE_FIXTURE["data"][1], "pop": 1.2},
        TIMELINE_FIXTURE["data"][2],
    ]
    intervals, coverage = normalize_timeline({**TIMELINE_FIXTURE, "data": data}, COORDS, NOW, NOW)
    assert len(intervals) == 1
    assert intervals[0].forecast_at == NOW + timedelta(minutes=30)
    assert coverage.malformed_records == 1
    assert coverage.continuous is False


def test_coordinates_reject_invalid_inputs():
    with pytest.raises(ValueError):
        WeatherCoordinates(latitude=91, longitude=0)
    with pytest.raises(ValueError):
        WeatherCoordinates(latitude=0, longitude=float("nan"))


def test_daily_budget_persists_rolls_over_and_fails_closed(tmp_path):
    state = tmp_path / "budget.json"
    budget = DailyRequestBudget(state, limit=2)
    budget.record_attempt(NOW)
    # A separately constructed guard observes persisted state after a restart.
    budget = DailyRequestBudget(state, limit=2)
    budget.record_attempt(NOW)
    with pytest.raises(Exception, match="budget exhausted"):
        budget.record_attempt(NOW)
    assert json.loads(state.read_text())["attempts"] == 2
    budget.record_attempt(NOW + timedelta(days=1))
    assert json.loads(state.read_text()) == {"attempts": 1, "utc_date": (NOW + timedelta(days=1)).date().isoformat()}
    state.write_text("corrupt")
    with pytest.raises(OpenWeatherError):
        budget.record_attempt(NOW + timedelta(days=1))


def test_missing_budget_state_after_initialization_fails_closed_even_on_day_rollover(tmp_path):
    state = tmp_path / "budget.json"
    budget = DailyRequestBudget(state, limit=2)
    budget.record_attempt(NOW)
    state.unlink()

    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache", budget_path=state,
        transport=httpx.MockTransport(handler), now=lambda: NOW + timedelta(days=1),
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert calls == []
    assert not result.current.status.available
    assert not result.forecast.status.available
    assert state.exists() is False
    assert "guard state is unavailable" in (result.current.status.error or "")


def test_unwritable_budget_state_fails_closed(tmp_path, monkeypatch):
    state = tmp_path / "budget.json"
    budget = DailyRequestBudget(state, limit=2)
    budget.record_attempt(NOW)
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    def fail_write(_path, _payload):
        raise PermissionError("simulated unwritable state")

    monkeypatch.setattr("app.openweather._atomic_json", fail_write)
    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache", budget_path=state,
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert calls == []
    assert not result.current.status.available and not result.forecast.status.available
    assert "guard state is unavailable" in (result.current.status.error or "")
    assert json.loads(state.read_text())["attempts"] == 1
    state.write_text(json.dumps({"utc_date": "not-a-date", "attempts": 0}))
    with pytest.raises(OpenWeatherError):
        budget.record_attempt(NOW + timedelta(days=1))


def test_daily_budget_rejects_limit_above_ceiling(tmp_path):
    with pytest.raises(ValueError):
        DailyRequestBudget(tmp_path / "budget.json", limit=101)


def test_environment_budget_can_only_lower_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENWEATHER_DAILY_REQUEST_LIMIT", "15")
    client = OpenWeatherClient(api_key="test", cache_dir=tmp_path / "cache")
    assert client.budget.limit == 15
    monkeypatch.setenv("OPENWEATHER_DAILY_REQUEST_LIMIT", "101")
    with pytest.raises(ValueError):
        OpenWeatherClient(api_key="test", cache_dir=tmp_path / "other")


def test_concurrent_budget_attempts_cannot_exceed_limit(tmp_path):
    path = tmp_path / "budget.json"
    with ProcessPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(_record_budget_attempt, [(path, NOW)] * 24))
    assert sum(outcomes) == 7
    assert json.loads(path.read_text())["attempts"] == 7


def test_timeline_cache_is_rewindowed_for_new_evaluation_time(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    first = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    later_eval = NOW + timedelta(minutes=30)
    second = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=later_eval))
    assert first.forecast.intervals[0].forecast_at == NOW
    assert second.forecast.intervals[0].forecast_at == later_eval
    assert second.forecast.status.cache_hit
    assert len(calls) == 2


def test_current_and_timeline_have_independent_cache_and_status(tmp_path):
    requests = []

    def handler(request):
        requests.append(request.url.path)
        body = CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE
        return httpx.Response(200, json=body)

    client = OpenWeatherClient(
        api_key="test-key", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    first = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert first.current.status.refreshed and first.current.status.available
    assert first.forecast.status.refreshed and first.forecast.status.available
    assert set(requests) == {"/data/4.0/onecall/current", "/data/4.0/onecall/timeline/15min"}
    budget_state = json.loads((tmp_path / "cache/request-budget.json").read_text())
    assert budget_state["attempts"] == 2

    second = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert second.current.status.cache_hit and second.forecast.status.cache_hit
    assert len(requests) == 2
    assert json.loads((tmp_path / "cache/request-budget.json").read_text())["attempts"] == 2


def test_failure_is_independent_and_stale_cache_survives(tmp_path):
    fail = False

    def handler(request):
        if request.url.path.endswith("/current") and fail:
            return httpx.Response(429, json={"message": "key=test-key"})
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test-key", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    initial = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert initial.current.status.available and initial.forecast.status.available
    fail = True
    later = NOW + timedelta(seconds=601)
    client.now = lambda: later
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=later))
    assert result.current.status.available and result.current.status.stale
    assert "429" in (result.current.status.error or "")
    assert result.forecast.status.available and result.forecast.status.refreshed


def test_invalid_replacement_retains_last_valid_cache_and_secret_not_persisted(tmp_path):
    bad = False

    def handler(request):
        nonlocal bad
        if bad and request.url.path.endswith("/current"):
            return httpx.Response(200, json={"lat": 49.2, "lon": -123.1, "data": [{"dt": "broken"}]})
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    cache = tmp_path / "cache"
    client = OpenWeatherClient(
        api_key="secret-test-key", cache_dir=cache, transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    current_cache = next(path for path in cache.glob("*.json") if "value" in json.loads(path.read_text()))
    before = current_cache.read_bytes()
    bad = True
    later = NOW + timedelta(seconds=601)
    client.now = lambda: later
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=later))
    assert result.current.status.stale
    assert current_cache.read_bytes() == before
    artifacts = b"".join(path.read_bytes() for path in cache.glob("*.json"))
    assert b"secret-test-key" not in artifacts
    assert b"appid" not in artifacts


def test_missing_key_and_corrupt_cache_report_unavailable(tmp_path):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    missing = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert not missing.current.status.available
    assert not missing.forecast.status.available
    assert calls == 0


def test_corrupt_cache_is_not_trusted(tmp_path):
    def handler(request):
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    cache = tmp_path / "cache"
    client = OpenWeatherClient(
        api_key="test", cache_dir=cache, daily_request_limit=2,
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    current_cache = next(path for path in cache.glob("*.json") if "value" in json.loads(path.read_text()))
    current_cache.write_text("{corrupt")
    # The persisted counter is exhausted, so the corrupt bytes cannot become accepted evidence.
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert not result.current.status.available
    assert not result.current.status.cache_hit
    assert "budget exhausted" in (result.current.status.error or "")


def test_cache_write_failure_does_not_discard_valid_live_response(tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    monkeypatch.setattr(client, "_write_cache", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert result.current.status.available and result.current.status.refreshed
    assert "not cached" in (result.current.status.error or "")


def test_concurrent_calls_share_refresh(tmp_path):
    calls = []

    async def handler(request):
        calls.append(request.url.path)
        await asyncio.sleep(0.01)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )

    async def run():
        return await asyncio.gather(*[
            client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW) for _ in range(5)
        ])

    results = asyncio.run(run())
    assert len(calls) == 2
    assert all(result.current.status.available and result.forecast.status.available for result in results)


def test_budget_exhaustion_uses_stale_cache_without_request(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    cache = tmp_path / "cache"
    client = OpenWeatherClient(
        api_key="test", cache_dir=cache, daily_request_limit=2,
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    later = NOW + timedelta(seconds=601)
    client.now = lambda: later
    exhausted = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=later))
    assert len(calls) == 2
    assert exhausted.current.status.stale and exhausted.forecast.status.stale
    assert "budget exhausted" in (exhausted.current.status.error or "")


def test_http_failure_does_not_leak_key_or_provider_body(tmp_path):
    def handler(request):
        return httpx.Response(401, text="secret-key should not be exposed")

    client = OpenWeatherClient(
        api_key="secret-key", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    rendered = result.model_dump_json()
    assert "secret-key" not in rendered
    assert "should not be exposed" not in rendered
    assert "401" in (result.current.status.error or "")


@pytest.mark.parametrize("status_code", [401, 403, 429])
def test_auth_subscription_and_rate_limit_failures_are_source_statuses(tmp_path, status_code):
    def handler(_request):
        return httpx.Response(status_code, text="private provider details")

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert not result.current.status.available and not result.current.status.success
    assert f"HTTP {status_code}" in (result.current.status.error or "")
    assert "private provider details" not in result.model_dump_json()


def test_invalid_json_and_transport_errors_are_sanitized(tmp_path):
    def handler(request):
        if request.url.path.endswith("/current"):
            return httpx.Response(200, content=b"not-json")
        raise httpx.ConnectError("https://secret-token@api.openweathermap.org/failure")

    client = OpenWeatherClient(
        api_key="secret-token", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    rendered = result.model_dump_json()
    assert not result.current.status.available and not result.forecast.status.available
    assert "secret-token" not in rendered
    assert "api.openweathermap.org/failure" not in rendered


def test_timeout_is_an_independent_source_failure(tmp_path):
    def handler(request):
        if request.url.path.endswith("/timeline/15min"):
            raise httpx.ReadTimeout("provider timeout containing appid=test")
        return httpx.Response(200, json=CURRENT_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert result.current.status.available
    assert not result.forecast.status.available
    assert "test" not in result.forecast.status.error


def test_corrupt_budget_fails_closed_without_outbound_calls(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "request-budget.json").write_text("corrupt")
    client = OpenWeatherClient(
        api_key="test", cache_dir=cache, transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert calls == []
    assert not result.current.status.available and not result.forecast.status.available
    assert "guard state is unavailable" in (result.current.status.error or "")


def test_current_and_forecast_fail_independently_in_both_directions(tmp_path):
    def handler(request):
        if request.url.path.endswith("/timeline/15min"):
            return httpx.Response(503, text="private provider response")
        return httpx.Response(200, json=CURRENT_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache",
        transport=httpx.MockTransport(handler), now=lambda: NOW,
    )
    result = asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert result.current.status.available
    assert not result.forecast.status.available
    assert "private provider response" not in result.model_dump_json()


def test_request_uses_only_approved_metric_products_and_parameters(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=CURRENT_FIXTURE if request.url.path.endswith("/current") else TIMELINE_FIXTURE)

    client = OpenWeatherClient(
        api_key="test", cache_dir=tmp_path / "cache", transport=httpx.MockTransport(handler), now=lambda: NOW
    )
    asyncio.run(client.get_weather(COORDS.latitude, COORDS.longitude, evaluation_time=NOW))
    assert {str(request.url.copy_with(query=None)) for request in requests} == {
        "https://api.openweathermap.org/data/4.0/onecall/current",
        "https://api.openweathermap.org/data/4.0/onecall/timeline/15min",
    }
    assert all(request.url.params["units"] == "metric" for request in requests)
    assert all(request.url.params["lat"] == str(COORDS.latitude) for request in requests)
    assert all(request.url.params["lon"] == str(COORDS.longitude) for request in requests)
