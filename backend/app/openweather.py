"""OpenWeather One Call 4.0 adapter with isolated cache and request budget."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SOURCE = "OpenWeather"
CURRENT_PRODUCT = "onecall4_current"
TIMELINE_PRODUCT = "onecall4_timeline_15min"
CURRENT_URL = "https://api.openweathermap.org/data/4.0/onecall/current"
TIMELINE_URL = "https://api.openweathermap.org/data/4.0/onecall/timeline/15min"
APPROVED_HOST = "api.openweathermap.org"
CACHE_TTL_SECONDS = 600
MAX_DAILY_REQUESTS = 100
MAX_RESPONSE_BYTES = 1_000_000
REQUEST_TIMEOUT = httpx.Timeout(12.0, connect=3.0, read=7.0, write=3.0, pool=3.0)
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "openweather"
DEFAULT_BUDGET_PATH = DEFAULT_CACHE_DIR / "request-budget.json"


class WeatherCoordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    latitude: float = Field(strict=True)
    longitude: float = Field(strict=True)

    @field_validator("latitude")
    @classmethod
    def valid_latitude(cls, value: float) -> float:
        if not math.isfinite(value) or not -90 <= value <= 90:
            raise ValueError("latitude is outside valid bounds")
        return value

    @field_validator("longitude")
    @classmethod
    def valid_longitude(cls, value: float) -> float:
        if not math.isfinite(value) or not -180 <= value <= 180:
            raise ValueError("longitude is outside valid bounds")
        return value


class WeatherCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: int | None = None
    group: str | None = None
    description: str | None = None


class CurrentWeather(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = SOURCE
    product: str = CURRENT_PRODUCT
    requested_coordinates: WeatherCoordinates
    provider_coordinates: WeatherCoordinates | None = None
    observed_at: datetime
    fetched_at: datetime
    units: str = "metric"
    temperature_c: float | None = None
    feels_like_c: float | None = None
    condition: WeatherCondition | None = None
    humidity_pct: float | None = None
    wind_speed_m_s: float | None = None
    wind_direction_deg: float | None = None
    wind_gust_m_s: float | None = None
    visibility_m: float | None = None
    rain_1h_mm: float | None = None
    snow_1h_mm: float | None = None


class ForecastInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = SOURCE
    product: str = TIMELINE_PRODUCT
    requested_coordinates: WeatherCoordinates
    forecast_at: datetime
    fetched_at: datetime
    units: str = "metric"
    precipitation_probability_pct: float | None = None
    temperature_c: float | None = None
    feels_like_c: float | None = None
    condition: WeatherCondition | None = None
    humidity_pct: float | None = None
    wind_speed_m_s: float | None = None
    wind_direction_deg: float | None = None
    wind_gust_m_s: float | None = None
    visibility_m: float | None = None
    rain_1h_mm: float | None = None
    rain_3h_mm: float | None = None
    snow_1h_mm: float | None = None
    snow_3h_mm: float | None = None


class ForecastCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluation_time: datetime
    window_end: datetime
    first_interval_at: datetime | None = None
    last_interval_at: datetime | None = None
    expected_interval_count: int
    returned_interval_count: int
    missing_intervals: list[datetime] = Field(default_factory=list)
    malformed_records: int = 0
    duplicate_records: int = 0
    initial_page_only: bool = True
    continuous: bool


class WeatherSourceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = SOURCE
    dataset_id: str
    success: bool
    available: bool
    fetched_at: datetime | None = None
    cache_hit: bool = False
    refreshed: bool = False
    stale: bool = False
    cache_age_seconds: int | None = None
    error: str | None = None


class CurrentWeatherResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weather: CurrentWeather | None = None
    status: WeatherSourceStatus


class ForecastWeatherResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intervals: list[ForecastInterval] = Field(default_factory=list)
    coverage: ForecastCoverage | None = None
    status: WeatherSourceStatus


class OpenWeatherResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: CurrentWeatherResult
    forecast: ForecastWeatherResult


class OpenWeatherError(Exception):
    """Sanitized adapter configuration or persistent request guard failure."""


class _ExpectedSourceFailure(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _optional_number(record: dict[str, Any], key: str) -> float | None:
    value = record.get(key)
    if value is None:
        return None
    number = _number(value)
    if number is None:
        raise ValueError(f"invalid numeric field: {key}")
    return number


def _date_from_epoch(value: Any) -> datetime:
    number = _number(value)
    if number is None:
        raise ValueError("invalid provider timestamp")
    try:
        return datetime.fromtimestamp(number, timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise ValueError("invalid provider timestamp") from None


def _condition(value: Any) -> WeatherCondition | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise TypeError("invalid provider condition")
    item = value[0]
    if not isinstance(item, dict):
        raise TypeError("invalid provider condition")
    code = item.get("id")
    if code is not None and (isinstance(code, bool) or not isinstance(code, int)):
        raise ValueError("invalid provider condition code")
    return WeatherCondition(
        code=code,
        group=item.get("main") if isinstance(item.get("main"), str) else None,
        description=(item.get("description") if isinstance(item.get("description"), str) else None),
    )


def _amount(record: dict[str, Any], key: str, period: str) -> float | None:
    raw = record.get(key)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError(f"invalid precipitation field: {key}")
    return _optional_number(raw, period)


def normalize_current(
    payload: Any,
    coordinates: WeatherCoordinates,
    fetched_at: datetime,
) -> CurrentWeather:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("invalid current response structure")
    data = payload["data"]
    if len(data) != 1 or not isinstance(data[0], dict):
        raise ValueError("invalid current response data")
    item = data[0]
    provider_coords = WeatherCoordinates(latitude=payload.get("lat"), longitude=payload.get("lon"))
    return CurrentWeather(
        requested_coordinates=coordinates,
        provider_coordinates=provider_coords,
        observed_at=_date_from_epoch(item.get("dt")),
        fetched_at=_utc(fetched_at),
        temperature_c=_optional_number(item, "temp"),
        feels_like_c=_optional_number(item, "feels_like"),
        condition=_condition(item.get("weather")),
        humidity_pct=_optional_number(item, "humidity"),
        wind_speed_m_s=_optional_number(item, "wind_speed"),
        wind_direction_deg=_optional_number(item, "wind_deg"),
        wind_gust_m_s=_optional_number(item, "wind_gust"),
        visibility_m=_optional_number(item, "visibility"),
        rain_1h_mm=_amount(item, "rain", "1h"),
        snow_1h_mm=_amount(item, "snow", "1h"),
    )


def normalize_timeline(
    payload: Any,
    coordinates: WeatherCoordinates,
    fetched_at: datetime,
    evaluation_time: datetime,
) -> tuple[list[ForecastInterval], ForecastCoverage]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise TypeError("invalid timeline response structure")
    # Validate echoed source coordinates without treating them as the selected location.
    WeatherCoordinates(latitude=payload.get("lat"), longitude=payload.get("lon"))
    fetched = _utc(fetched_at)
    start = _utc(evaluation_time)
    end = start + timedelta(hours=3)
    expected = []
    next_slot = (int(start.timestamp()) + 899) // 900 * 900
    while next_slot <= end.timestamp():
        expected.append(datetime.fromtimestamp(next_slot, timezone.utc))
        next_slot += 900

    found: dict[datetime, ForecastInterval] = {}
    malformed = duplicate = 0
    for raw in payload["data"]:
        try:
            if not isinstance(raw, dict):
                raise TypeError("record is not an object")
            target = _date_from_epoch(raw.get("dt"))
            if target in found:
                duplicate += 1
                continue
            if not start <= target <= end:
                continue
            probability = _optional_number(raw, "pop")
            if probability is not None and not 0 <= probability <= 1:
                raise ValueError("invalid precipitation probability")
            found[target] = ForecastInterval(
                requested_coordinates=coordinates,
                forecast_at=target,
                fetched_at=fetched,
                precipitation_probability_pct=(probability * 100 if probability is not None else None),
                temperature_c=_optional_number(raw, "temp"),
                feels_like_c=_optional_number(raw, "feels_like"),
                condition=_condition(raw.get("weather")),
                humidity_pct=_optional_number(raw, "humidity"),
                wind_speed_m_s=_optional_number(raw, "wind_speed"),
                wind_direction_deg=_optional_number(raw, "wind_deg"),
                wind_gust_m_s=_optional_number(raw, "wind_gust"),
                visibility_m=_optional_number(raw, "visibility"),
                rain_1h_mm=_amount(raw, "rain", "1h"),
                rain_3h_mm=_amount(raw, "rain", "3h"),
                snow_1h_mm=_amount(raw, "snow", "1h"),
                snow_3h_mm=_amount(raw, "snow", "3h"),
            )
        except (ValueError, ValidationError, TypeError):
            malformed += 1

    intervals = [found[stamp] for stamp in sorted(found)]
    missing = [stamp for stamp in expected if stamp not in found]
    coverage = ForecastCoverage(
        evaluation_time=start,
        window_end=end,
        first_interval_at=intervals[0].forecast_at if intervals else None,
        last_interval_at=intervals[-1].forecast_at if intervals else None,
        expected_interval_count=len(expected),
        returned_interval_count=len(intervals),
        missing_intervals=missing,
        malformed_records=malformed,
        duplicate_records=duplicate,
        continuous=bool(expected) and not missing,
    )
    return intervals, coverage


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class DailyRequestBudget:
    """Persistent process-safe UTC request counter; refuses unsafe state."""

    def __init__(self, path: Path | str = DEFAULT_BUDGET_PATH, limit: int = MAX_DAILY_REQUESTS):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_DAILY_REQUESTS:
            raise ValueError(f"daily request limit must be between 1 and {MAX_DAILY_REQUESTS}")
        self.path = Path(path)
        self.limit = limit
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.initialized_path = self.path.with_suffix(self.path.suffix + ".initialized")

    def record_attempt(self, now: datetime) -> None:
        day = _utc(now).date().isoformat()
        try:
            with _exclusive_file_lock(self.lock_path):
                initialized = self.initialized_path.exists()
                if initialized:
                    marker = json.loads(self.initialized_path.read_text(encoding="utf-8"))
                    if marker != {"schema_version": 1, "initialized": True}:
                        raise ValueError("invalid budget initialization marker")
                    if not self.path.exists():
                        raise ValueError("initialized budget state is missing")

                state_exists = self.path.exists()
                if state_exists:
                    state = json.loads(self.path.read_text(encoding="utf-8"))
                    if (
                        not isinstance(state, dict)
                        or set(state) != {"utc_date", "attempts"}
                        or not isinstance(state.get("utc_date"), str)
                        or isinstance(state.get("attempts"), bool)
                        or not isinstance(state.get("attempts"), int)
                        or state["attempts"] < 0
                    ):
                        raise ValueError("invalid budget state")
                    try:
                        valid_date = date.fromisoformat(state["utc_date"]).isoformat() == state["utc_date"]
                    except ValueError:
                        valid_date = False
                    if not valid_date:
                        raise ValueError("invalid budget date")
                    count = state["attempts"] if state["utc_date"] == day else 0
                else:
                    if initialized:
                        raise ValueError("initialized budget state is missing")
                    count = 0
                    # Persist initialization first. If the following state write fails or
                    # the process stops, later calls fail closed instead of resetting.
                    _atomic_json(self.initialized_path, {"schema_version": 1, "initialized": True})

                # Migrate a valid pre-marker state without resetting its count.
                if state_exists and not initialized:
                    _atomic_json(self.initialized_path, {"schema_version": 1, "initialized": True})
                if count >= self.limit:
                    raise _ExpectedSourceFailure("daily request budget exhausted")
                _atomic_json(self.path, {"utc_date": day, "attempts": count + 1})
        except _ExpectedSourceFailure:
            raise
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            raise OpenWeatherError("daily request guard state is unavailable; upstream requests are disabled") from None


class OpenWeatherClient:
    """Callable backend adapter for independent One Call 4.0 current and timeline data."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        budget_path: Path | str | None = None,
        daily_request_limit: int | None = None,
        cache_ttl_seconds: int = CACHE_TTL_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Any = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("OPENWEATHER_API_KEY", "")).strip()
        if isinstance(cache_ttl_seconds, bool) or not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds <= 0:
            raise ValueError("cache TTL must be a positive integer")
        if daily_request_limit is None:
            configured = os.getenv("OPENWEATHER_DAILY_REQUEST_LIMIT", "100")
            try:
                daily_request_limit = int(configured)
            except ValueError:
                raise ValueError("OPENWEATHER_DAILY_REQUEST_LIMIT must be an integer") from None
        self.cache_dir = Path(cache_dir)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.transport = transport
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.budget = DailyRequestBudget(budget_path or self.cache_dir / "request-budget.json", daily_request_limit)
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}
        self._locks_guard = asyncio.Lock()

    async def _product_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_guard:
            current = self._locks.get(key)
            lock = current[0] if current else asyncio.Lock()
            self._locks[key] = (lock, (current[1] if current else 0) + 1)
            return lock

    async def _release_product_lock(self, key: str, lock: asyncio.Lock) -> None:
        async with self._locks_guard:
            current = self._locks.get(key)
            if current and current[0] is lock:
                if current[1] <= 1:
                    del self._locks[key]
                else:
                    self._locks[key] = (lock, current[1] - 1)

    @staticmethod
    def _cache_key(product: str, coordinates: WeatherCoordinates) -> str:
        identity = {
            "product": product,
            "latitude": round(coordinates.latitude, 4),
            "longitude": round(coordinates.longitude, 4),
            "units": "metric",
            "parameters": {"timeline": "15min"} if product == TIMELINE_PRODUCT else {},
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _read_cache(
        self,
        path: Path,
        product: str,
        coordinates: WeatherCoordinates,
        evaluation: datetime | None,
    ) -> tuple[BaseModel, datetime] | None:
        try:
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(wrapper, dict) or wrapper.get("schema_version") != 1:
                return None
            fetched = _utc(datetime.fromisoformat(wrapper["fetched_at"]))
            if product == CURRENT_PRODUCT:
                value = CurrentWeather.model_validate(wrapper["value"])
                if (
                    value.source != SOURCE
                    or value.product != CURRENT_PRODUCT
                    or value.units != "metric"
                    or value.fetched_at != fetched
                ):
                    return None
            else:
                payload = wrapper["provider_data"]
                intervals, coverage = normalize_timeline(
                    payload, coordinates, fetched, evaluation or fetched
                )
                value = ForecastWeatherResult(
                    intervals=intervals,
                    coverage=coverage,
                    status=WeatherSourceStatus(
                        dataset_id=product, success=bool(intervals), available=bool(intervals),
                        fetched_at=fetched,
                    ),
                )
            return value, fetched
        except (OSError, ValueError, TypeError, KeyError, ValidationError, json.JSONDecodeError):
            return None

    def _write_cache(
        self,
        path: Path,
        fetched: datetime,
        value: BaseModel,
        provider_data: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "fetched_at": _utc(fetched).isoformat(),
        }
        if isinstance(value, CurrentWeather):
            payload["value"] = value.model_dump(mode="json")
        else:
            if provider_data is None:
                raise ValueError("validated timeline response is required for cache replacement")
            # Provider pagination links can contain credentials; persist only observed weather fields.
            payload["provider_data"] = {
                key: provider_data[key]
                for key in ("lat", "lon", "timezone", "timezone_offset", "data")
                if key in provider_data
            }
        _atomic_json(path, payload)

    async def _request(self, product: str, coordinates: WeatherCoordinates, now: datetime) -> Any:
        if not self.api_key:
            raise _ExpectedSourceFailure("OpenWeather API key is not configured")
        url = CURRENT_URL if product == CURRENT_PRODUCT else TIMELINE_URL
        # URL constants are source-owned; no redirect target is followed and errors are sanitized.
        if url.startswith("https://") is False or httpx.URL(url).host != APPROVED_HOST:
            raise OpenWeatherError("OpenWeather endpoint configuration is invalid")
        self.budget.record_attempt(now)

        async def perform_request() -> Any:
            async with httpx.AsyncClient(
                transport=self.transport,
                timeout=REQUEST_TIMEOUT,
                follow_redirects=False,
            ) as client, client.stream(
                "GET",
                url,
                params={
                    "lat": coordinates.latitude,
                    "lon": coordinates.longitude,
                    "units": "metric",
                    "appid": self.api_key,
                },
            ) as response:
                if response.status_code in {401, 403, 429}:
                    raise _ExpectedSourceFailure(f"OpenWeather request rejected (HTTP {response.status_code})")
                if response.is_redirect:
                    raise _ExpectedSourceFailure("OpenWeather redirect was rejected")
                if response.status_code < 200 or response.status_code >= 300:
                    raise _ExpectedSourceFailure(f"OpenWeather request failed (HTTP {response.status_code})")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise _ExpectedSourceFailure("OpenWeather response exceeded size limit")
            try:
                return json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise _ExpectedSourceFailure("OpenWeather returned invalid JSON") from None

        try:
            return await asyncio.wait_for(perform_request(), timeout=12.0)
        except _ExpectedSourceFailure:
            raise
        except (asyncio.TimeoutError, httpx.TimeoutException, httpx.TransportError):
            raise _ExpectedSourceFailure("OpenWeather request timed out or transport failed") from None

    async def get_weather(
        self,
        latitude: float,
        longitude: float,
        *,
        evaluation_time: datetime | None = None,
    ) -> OpenWeatherResult:
        """Fetch current and next-three-hour timeline independently for a selected destination."""
        coordinates = WeatherCoordinates(latitude=latitude, longitude=longitude)
        evaluation = _utc(evaluation_time or self.now())
        current, forecast = await asyncio.gather(
            self._get_current(coordinates), self._get_forecast(coordinates, evaluation)
        )
        return OpenWeatherResult(current=current, forecast=forecast)

    async def _get_current(self, coordinates: WeatherCoordinates) -> CurrentWeatherResult:
        return await self._load_product(CURRENT_PRODUCT, coordinates, None)

    async def _get_forecast(
        self, coordinates: WeatherCoordinates, evaluation: datetime
    ) -> ForecastWeatherResult:
        return await self._load_product(TIMELINE_PRODUCT, coordinates, evaluation)

    async def _load_product(
        self, product: str, coordinates: WeatherCoordinates, evaluation: datetime | None
    ) -> CurrentWeatherResult | ForecastWeatherResult:
        key = self._cache_key(product, coordinates)
        lock = await self._product_lock(key)
        try:
            async with lock:
                now = _utc(self.now())
                path = self.cache_dir / f"{key}.json"
                cached = self._read_cache(path, product, coordinates, evaluation)
                cached_value, cached_at = cached if cached else (None, None)
                age = max(0, int((now - cached_at).total_seconds())) if cached_at else None
                if cached_value is not None and age is not None and age < self.cache_ttl_seconds:
                    return self._with_status(product, cached_value, cached_at, now, cache_hit=True)
                try:
                    raw = await self._request(product, coordinates, now)
                    fetched = _utc(self.now())
                    cache_payload = None
                    if product == CURRENT_PRODUCT:
                        value: BaseModel = normalize_current(raw, coordinates, fetched)
                    else:
                        intervals, coverage = normalize_timeline(raw, coordinates, fetched, evaluation or now)
                        cache_payload = raw
                        value = ForecastWeatherResult(
                            intervals=intervals,
                            coverage=coverage,
                            status=WeatherSourceStatus(
                                dataset_id=product,
                                success=True,
                                available=bool(intervals),
                                fetched_at=fetched,
                                refreshed=True,
                                error=None if intervals else "no forecast intervals in requested window",
                            ),
                        )
                    # Validate the entire typed replacement before atomic activation.
                    value = type(value).model_validate(value.model_dump(mode="python"))
                except _ExpectedSourceFailure as exc:
                    reason = exc.reason
                except OpenWeatherError:
                    reason = "daily request guard state is unavailable; upstream requests are disabled"
                except (ValueError, TypeError, ValidationError, OSError):
                    reason = "OpenWeather returned an invalid response"
                else:
                    try:
                        self._write_cache(path, fetched, value, cache_payload)
                        cache_error = None
                    except OSError:
                        cache_error = "cache replacement failed; live response was not cached"
                    return self._with_status(
                        product, value, fetched, fetched, refreshed=True, error=cache_error
                    )
                if cached_value is not None and cached_at is not None:
                    return self._with_status(
                        product, cached_value, cached_at, now, stale=True,
                        error=f"refresh unavailable: {reason}",
                    )
                return self._unavailable(product, reason)
        finally:
            await self._release_product_lock(key, lock)

    def _with_status(
        self,
        product: str,
        value: BaseModel,
        fetched_at: datetime,
        now: datetime,
        *,
        cache_hit: bool = False,
        refreshed: bool = False,
        stale: bool = False,
        error: str | None = None,
    ) -> CurrentWeatherResult | ForecastWeatherResult:
        age = max(0, int((_utc(now) - _utc(fetched_at)).total_seconds()))
        available = bool(value.intervals) if isinstance(value, ForecastWeatherResult) else True
        status = WeatherSourceStatus(
            dataset_id=product,
            success=refreshed or cache_hit or error is None,
            available=available,
            fetched_at=fetched_at,
            cache_hit=cache_hit,
            refreshed=refreshed,
            stale=stale,
            cache_age_seconds=age,
            error=error or ("no forecast intervals in requested window" if not available else None),
        )
        if isinstance(value, CurrentWeather):
            return CurrentWeatherResult(weather=value, status=status)
        return ForecastWeatherResult(intervals=value.intervals, coverage=value.coverage, status=status)

    @staticmethod
    def _unavailable(product: str, error: str) -> CurrentWeatherResult | ForecastWeatherResult:
        status = WeatherSourceStatus(dataset_id=product, success=False, available=False, error=error)
        if product == CURRENT_PRODUCT:
            return CurrentWeatherResult(status=status)
        return ForecastWeatherResult(status=status)
