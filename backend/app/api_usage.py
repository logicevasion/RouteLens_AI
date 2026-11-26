"""Aggregate accounting and daily admission for application-side HTTP attempts."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from collections import Counter
from collections.abc import Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from math import ceil
from pathlib import Path
from threading import BoundedSemaphore, Event, Lock

DEFAULT_DAYS = 30
BUSY_TIMEOUT_SECONDS = 0.25
ADMISSION_TIMEOUT_SECONDS = 1.0
MAX_PENDING_ADMISSIONS = 128
DEFAULT_DAILY_LIMIT = 100
MAX_SQLITE_INTEGER = 2**63 - 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


class Operation(str, Enum):
    MAPTILER_GEOCODING = "maptiler.geocoding"
    ORS_DIRECTIONS = "openrouteservice.directions"
    OPENWEATHER_CURRENT = "openweather.current"
    OPENWEATHER_TIMELINE = "openweather.timeline_15min"
    ECCC_PAGE = "eccc_swob.page"
    DRIVEBC_PAGE = "drivebc_open511.page"
    ROAD_AHEAD_CLOSURES = "vancouver_road_ahead.closures"
    ROAD_AHEAD_CONSTRUCTION = "vancouver_road_ahead.construction"
    ROAD_AHEAD_DETAIL = "vancouver_road_ahead.detail"
    CAMERA_CATALOGUE = "vancouver_traffic_cameras.catalogue"
    CAMERA_PAGE = "vancouver_traffic_cameras.page"
    CAMERA_FRAME = "vancouver_traffic_cameras.frame"
    OPENROUTER_VISION = "openrouter.vision"
    OPENROUTER_BRIEFING = "openrouter.briefing"

    @property
    def provider(self) -> str:
        return self.value.split(".", 1)[0]


PROVIDERS = tuple(dict.fromkeys(operation.provider for operation in Operation))
BROWSER_MAP_PROVIDER = "maptiler_map_resources"
DAILY_LIMIT_ENV = {
    Operation.MAPTILER_GEOCODING: "MAPTILER_GEOCODING_DAILY_LIMIT",
    Operation.ORS_DIRECTIONS: "OPENROUTESERVICE_DIRECTIONS_DAILY_LIMIT",
}


class UsageUnavailable(Exception):
    """The database could not provide a report."""


class DailyQuotaExhausted(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class DailyQuotaUnavailable(Exception):
    """The application could not safely reserve a quota slot."""


def configured_daily_limits() -> dict[Operation, int]:
    limits = {}
    for operation, name in DAILY_LIMIT_ENV.items():
        value = os.environ.get(name, str(DEFAULT_DAILY_LIMIT)).strip()
        try:
            if value.isascii() and value.isdecimal():
                limit = int(value)
                if 1 <= limit <= MAX_SQLITE_INTEGER:
                    limits[operation] = limit
                    continue
        except ValueError:
            # Python may reject unusually long decimal strings during conversion.
            pass
        raise ValueError(f"{name} must be an integer between 1 and {MAX_SQLITE_INTEGER}.")
    return limits


def configured_usage_path() -> Path:
    """Resolve a process-environment override relative to the checkout if needed."""
    data_dir = os.environ.get("ROUTELENS_DATA_DIR") or "data/app"
    return PROJECT_ROOT / data_dir / "api-usage.sqlite3"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UsageReport:
    start: date
    end: date
    counts: dict[tuple[date, Operation], int]
    gaps: frozenset[date]

    def provider_totals(self) -> dict[str, int]:
        totals = dict.fromkeys(PROVIDERS, 0)
        for (_, operation), attempts in self.counts.items():
            totals[operation.provider] += attempts
        return totals

    def operation_totals(self) -> Counter[Operation]:
        totals = Counter(dict.fromkeys(Operation, 0))
        for (_, operation), attempts in self.counts.items():
            totals[operation] += attempts
        return totals


class UsageStore:
    def __init__(
        self,
        path: Path,
        *,
        now: Callable[[], datetime] = utc_now,
        daily_limits: dict[Operation, int] | None = None,
    ) -> None:
        self.path = path.absolute()
        self._now = now
        self._daily_limits = (
            dict.fromkeys(DAILY_LIMIT_ENV, DEFAULT_DAILY_LIMIT)
            if daily_limits is None else daily_limits.copy()
        )
        self._gap_dates: set[date] = set()
        self._gap_lock = Lock()
        self._admission_slots = BoundedSemaphore(MAX_PENDING_ADMISSIONS)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="api-usage")

    def today(self) -> date:
        return self._now().astimezone(timezone.utc).date()

    def window(self, days: int) -> tuple[date, date]:
        end = self.today()
        if not 1 <= days <= end.toordinal():
            raise ValueError("days must be positive and the reporting window must fit the calendar")
        return end - timedelta(days=days - 1), end

    def _open_writer(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path, timeout=BUSY_TIMEOUT_SECONDS)

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                utc_date TEXT NOT NULL,
                operation TEXT NOT NULL,
                attempts INTEGER NOT NULL CHECK (typeof(attempts) = 'integer' AND attempts >= 0),
                PRIMARY KEY (utc_date, operation)
            )
            """
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS api_usage_gaps (utc_date TEXT NOT NULL PRIMARY KEY)"
        )

    def initialize(self) -> None:
        """Make a fresh installation report zero attempts before its first dispatch."""
        try:
            with closing(self._open_writer()) as connection, connection:
                self._ensure_schema(connection)
        except (sqlite3.Error, OSError, ValueError):
            logger.warning("API usage database initialization failed")

    def _record_gap(self, day: date) -> None:
        with self._gap_lock:
            self._gap_dates.add(day)

    async def start(self) -> None:
        """Initialize without using the application's default executor."""
        try:
            await asyncio.wrap_future(self._executor.submit(self.initialize))
        except Exception as error:  # noqa: BLE001 - Accounting must not prevent startup.
            logger.warning("api_usage.initialize_error exception_class=%s", type(error).__name__)

    def close(self) -> None:
        """Drain accepted writes and release the worker."""
        self._executor.shutdown(wait=True)

    @staticmethod
    def _write_gaps(connection: sqlite3.Connection, gaps: set[date]) -> None:
        if gaps:
            connection.executemany(
                "INSERT OR IGNORE INTO api_usage_gaps (utc_date) VALUES (?)",
                ((gap.isoformat(),) for gap in gaps),
            )

    async def reserve(self, operation: Operation) -> None:
        """Require a committed quota reservation before allowing dispatch."""
        if not self._admission_slots.acquire(blocking=False):
            raise DailyQuotaUnavailable
        abandoned = Event()
        try:
            job = self._executor.submit(self._reserve_attempt, operation, abandoned)
        except Exception as error:  # noqa: BLE001 - Failed submissions must block dispatch.
            self._admission_slots.release()
            self._log_admission_error(operation, error)
            raise DailyQuotaUnavailable from None

        # Keep the slot occupied until the worker retires the job, including when
        # callers time out or cancel while jobs are queued behind accounting writes.
        job.add_done_callback(lambda _: self._admission_slots.release())
        result = asyncio.wrap_future(job)
        # Observe any worker error even if the request has stopped waiting.
        result.add_done_callback(lambda finished: finished.exception())
        try:
            retry_after = await asyncio.wait_for(asyncio.shield(result), ADMISSION_TIMEOUT_SECONDS)
        except Exception as error:  # noqa: BLE001 - Any admission failure must block dispatch.
            self._log_admission_error(operation, error)
            raise DailyQuotaUnavailable from None
        finally:
            abandoned.set()
        if retry_after is not None:
            raise DailyQuotaExhausted(retry_after)

    @staticmethod
    def _log_admission_error(operation: Operation, error: Exception) -> None:
        logger.warning(
            "api_usage.admission_error operation=%s exception_class=%s",
            operation.value,
            type(error).__name__,
        )

    def _reserve_attempt(self, operation: Operation, abandoned: Event) -> int | None:
        if abandoned.is_set():
            return None
        with self._gap_lock:
            gaps = self._gap_dates.copy()
        with closing(self._open_writer()) as connection, connection:
            # SQLite serializes writers across connections and processes. Read the
            # UTC date after taking the lock in case the request waited across midnight.
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_schema(connection)
            if abandoned.is_set():
                return None
            now = self._now().astimezone(timezone.utc)
            updated = connection.execute(
                """
                INSERT INTO api_usage (utc_date, operation, attempts) VALUES (?, ?, 1)
                ON CONFLICT (utc_date, operation) DO UPDATE SET attempts = attempts + 1
                WHERE attempts < ?
                """,
                (now.date().isoformat(), operation.value, self._daily_limits[operation]),
            )
            if not updated.rowcount:
                reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                return ceil((reset - now).total_seconds())
            self._write_gaps(connection, gaps)
        with self._gap_lock:
            self._gap_dates.difference_update(gaps)
        return None

    def record(self, operation: Operation, day: date) -> None:
        """Atomically increment one daily row, using a short, bounded write."""
        with self._gap_lock:
            gaps = self._gap_dates.copy()
        try:
            with closing(self._open_writer()) as connection, connection:
                self._ensure_schema(connection)
                connection.execute(
                    """
                    INSERT INTO api_usage (utc_date, operation, attempts) VALUES (?, ?, 1)
                    ON CONFLICT (utc_date, operation) DO UPDATE SET attempts = attempts + 1
                    """,
                    (day.isoformat(), operation.value),
                )
                self._write_gaps(connection, gaps)
        except (sqlite3.Error, OSError, ValueError):
            self._record_gap(day)
            logger.warning("API usage attempt could not be recorded for %s", operation.value)
        else:
            with self._gap_lock:
                self._gap_dates.difference_update(gaps)

    def count_dispatch(self, operation: Operation) -> None:
        # Submit before HTTPX enters the transport. SQLite contention must stay
        # outside provider deadlines, and cancellation of the request must not
        # cancel the accounting write for an already dispatched attempt.
        day = self.today()
        try:
            self._executor.submit(self._record_attempt, operation, day)
        except Exception as error:  # noqa: BLE001 - Failed submissions must not stop dispatch.
            self._hook_error(operation, error, day)

    def _hook_error(
        self, operation: Operation, error: Exception, day: date | None = None
    ) -> None:
        if day is None:
            try:
                day = self.today()
            except Exception:  # noqa: BLE001 - Keep diagnostics available if the store clock fails.
                day = utc_now().date()
        self._record_gap(day)
        logger.warning(
            "api_usage.request_hook_error operation=%s exception_class=%s",
            operation.value,
            type(error).__name__,
        )

    def _record_attempt(self, operation: Operation, day: date) -> None:
        try:
            self.record(operation, day)
        except Exception as error:  # noqa: BLE001 - Preserve a gap for unexpected write failures.
            self._record_gap(day)
            logger.warning(
                "api_usage.record_error operation=%s exception_class=%s",
                operation.value,
                type(error).__name__,
            )

    async def flush(self) -> None:
        """Wait for previously submitted writes on the single-worker executor."""
        await asyncio.wrap_future(self._executor.submit(lambda: None))

    async def report(self, start: date, end: date) -> UsageReport:
        """Read after previously submitted writes on the same executor."""
        return await asyncio.wrap_future(self._executor.submit(self.read_report, start, end))

    def read_report(self, start: date, end: date) -> UsageReport:
        """Read one snapshot of daily counts and gaps without creating the database."""
        with self._gap_lock:
            gaps = {day for day in self._gap_dates if start <= day <= end}
        bounds = (start.isoformat(), end.isoformat())
        counts: dict[tuple[date, Operation], int] = {}
        try:
            with closing(sqlite3.connect(
                self.path.as_uri() + "?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
            )) as connection:
                rows = connection.execute(
                    """
                    SELECT utc_date, operation, attempts FROM api_usage WHERE utc_date BETWEEN ? AND ?
                    UNION ALL
                    SELECT utc_date, NULL, NULL FROM api_usage_gaps WHERE utc_date BETWEEN ? AND ?
                    """,
                    (*bounds, *bounds),
                )
                for utc_date, operation, attempts in rows:
                    day = date.fromisoformat(utc_date)
                    if operation is None:
                        gaps.add(day)
                    else:
                        counts[day, Operation(operation)] = attempts
        except (sqlite3.Error, OSError, ValueError):
            raise UsageUnavailable from None
        return UsageReport(start, end, counts, frozenset(gaps))


_active_store: ContextVar[UsageStore | None] = ContextVar("api_usage_store", default=None)


@contextmanager
def observe_usage(store: UsageStore) -> Iterator[None]:
    token = _active_store.set(store)
    try:
        yield
    finally:
        _active_store.reset(token)


def usage_hooks(operation: Operation) -> dict[str, list[Callable[[object], Awaitable[None]]]]:
    """Reserve capped attempts or observe uncapped HTTPX dispatches in the app."""
    store = _active_store.get()
    if store is None:
        return {}

    if operation in DAILY_LIMIT_ENV:
        async def reserve_before_request(_request: object) -> None:
            await store.reserve(operation)

        return {"request": [reserve_before_request]}

    async def before_request(_request: object) -> None:
        try:
            store.count_dispatch(operation)
        except Exception as error:  # noqa: BLE001 - HTTPX propagates hook exceptions.
            store._hook_error(operation, error)

    return {"request": [before_request]}
