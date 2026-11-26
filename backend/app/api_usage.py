"""Best-effort aggregate accounting for application-side HTTP attempts."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from collections import Counter
from collections.abc import Awaitable, Callable, Iterator
from contextlib import closing, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Lock

DEFAULT_DAYS = 30
BUSY_TIMEOUT_SECONDS = 0.25
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


class UsageUnavailable(Exception):
    """The database could not provide a report."""


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
    def __init__(self, path: Path, *, now: Callable[[], datetime] = utc_now) -> None:
        self.path = path.absolute()
        self._now = now
        self._gap_dates: set[date] = set()
        self._gap_lock = Lock()
        self._pending: set[asyncio.Future[None]] = set()

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
                if gaps:
                    connection.executemany(
                        "INSERT OR IGNORE INTO api_usage_gaps (utc_date) VALUES (?)",
                        ((gap.isoformat(),) for gap in gaps),
                    )
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
        loop = asyncio.get_running_loop()
        try:
            future = loop.run_in_executor(None, self.record, operation, day)
        except RuntimeError as error:
            self._record_gap(day)
            logger.warning(
                "api_usage.request_hook_error operation=%s exception_class=%s",
                operation.value,
                type(error).__name__,
            )
            return
        self._pending.add(future)
        future.add_done_callback(self._pending.discard)

    async def flush(self) -> None:
        """Wait for the attempts already submitted when a report or shutdown starts."""
        await asyncio.gather(*(asyncio.shield(future) for future in self._pending))

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
    """Count each HTTPX dispatch, including accepted redirects, when scoped to the app."""
    store = _active_store.get()
    if store is None:
        return {}

    async def before_request(_request: object) -> None:
        store.count_dispatch(operation)

    return {"request": [before_request]}
