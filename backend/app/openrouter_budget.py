"""Shared file coordination for the independent OpenRouter role ledgers."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

MAX_LEDGER_BYTES = 64 * 1024


def _lock_path(first: Path, second: Path) -> Path:
    """Return one stable lock path for a ledger pair, including temp test pairs."""
    paths = sorted((str(first.resolve()), str(second.resolve())))
    identity = hashlib.sha256("\0".join(paths).encode("utf-8")).hexdigest()
    # Both roles derive this from the same canonical pair, so separate processes
    # and adapter instances coordinate even when the role files have different parents.
    return Path(paths[0]).parent / f".openrouter-reservations-{identity}.lock"


@contextmanager
def reservation_lock(first: Path, second: Path) -> Iterator[None]:
    first = Path(first)
    second = Path(second)
    lock_path = _lock_path(first, second)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_ledger(path: Path, timestamp: float) -> dict:
    """Read an empty or valid role ledger; raise on any invalid persisted state."""
    if not path.exists():
        return {
            "attempts": [],
            "estimated_project_usd": 0.0,
            "estimated_daily": {},
            "_validated_timestamps": [],
        }
    if path.stat().st_size > MAX_LEDGER_BYTES:
        raise ValueError("budget ledger is oversized")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise TypeError("budget ledger is not an object")
    attempts = record["attempts"]
    project = _ledger_number(record["estimated_project_usd"])
    daily = record["estimated_daily"]
    if not isinstance(attempts, list) or not isinstance(daily, dict):
        raise TypeError("budget ledger fields have invalid types")
    timestamps = [_ledger_number(item) for item in attempts]
    daily_values = [_ledger_number(item) for item in daily.values()]
    if (
        not math.isfinite(project)
        or project < 0
        or any(not math.isfinite(item) or not (0 <= item <= timestamp + 60) for item in timestamps)
        or any(not math.isfinite(item) or item < 0 for item in daily_values)
    ):
        raise ValueError("budget ledger contains invalid values")
    record["estimated_project_usd"] = project
    record["_validated_timestamps"] = timestamps
    return record


def _ledger_number(value: object) -> float:
    """Accept JSON numbers only and normalize overflow/nonfinite values to denial."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("budget ledger numeric field has an invalid type")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError("budget ledger numeric field is out of range") from error
    if not math.isfinite(number):
        raise ValueError("budget ledger numeric field is nonfinite")
    return number
