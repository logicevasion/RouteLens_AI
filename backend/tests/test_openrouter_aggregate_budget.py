"""Regression coverage for the shared OpenRouter estimated-spend guard."""

from __future__ import annotations

import inspect
import json
import multiprocessing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.openrouter_briefing import BriefingAttemptBudget
from app.openrouter_budget import MAX_LEDGER_BYTES, reservation_lock
from app.openrouter_vision import AttemptBudget

NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def _ledger(estimate: float) -> dict:
    return {
        "attempts": [],
        "estimated_project_usd": estimate,
        "estimated_daily": {},
    }


def _compatible_vision_budget(path: Path, briefing_path: Path) -> AttemptBudget:
    """Pass the peer path when supported, while retaining the original signature."""
    arguments = {"now": lambda: NOW}
    if "briefing_path" in inspect.signature(AttemptBudget).parameters:
        arguments["briefing_path"] = briefing_path
    return AttemptBudget(path, **arguments)


def test_arch_004_original_vision_reservation_exceeds_aggregate_cap(tmp_path):
    vision_path = tmp_path / "vision.json"
    briefing_path = tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(4.80)))
    briefing_path.write_text(json.dumps(_ledger(0.18)))

    # Both role states are valid. The briefing guard allows its $0.002 attempt,
    # then the old vision-only guard would allow another $0.02, reaching $5.002.
    vision = _compatible_vision_budget(vision_path, briefing_path)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    assert briefing.reserve() is True
    vision_accepted = vision.reserve()
    if vision_accepted:
        original_total = (
            json.loads(vision_path.read_text())["estimated_project_usd"]
            + json.loads(briefing_path.read_text())["estimated_project_usd"]
        )
        assert round(original_total, 8) == 5.002
    assert vision_accepted is False, "vision accepted a reservation that brings the valid combined estimate to $5.002"
    vision_estimate = json.loads(vision_path.read_text())["estimated_project_usd"]
    briefing_estimate = json.loads(briefing_path.read_text())["estimated_project_usd"]
    assert briefing_estimate == 0.182
    assert round(vision_estimate + briefing_estimate, 8) < 5.0


@pytest.mark.parametrize(
    ("vision_estimate", "briefing_estimate", "order", "expected"),
    [
        (4.80, 0.178, "vision_then_briefing", (True, False)),
        (4.80, 0.18, "briefing_then_vision", (True, False)),
    ],
)
def test_sequential_reservation_orders_keep_aggregate_below_five(
    tmp_path, vision_estimate, briefing_estimate, order, expected
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(vision_estimate)))
    briefing_path.write_text(json.dumps(_ledger(briefing_estimate)))
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )

    reservations = (vision.reserve(), briefing.reserve()) if order == "vision_then_briefing" else (
        briefing.reserve(), vision.reserve()
    )

    assert reservations == expected
    total = sum(
        json.loads(path.read_text())["estimated_project_usd"]
        for path in (vision_path, briefing_path)
    )
    assert total < 5.0


@pytest.mark.parametrize(
    ("vision_estimate", "briefing_estimate", "expected"),
    [(4.80, 0.179, True), (4.80, 0.18, False), (4.81, 0.18, False)],
)
def test_aggregate_strictly_below_five_boundary(
    tmp_path, vision_estimate, briefing_estimate, expected
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(vision_estimate)))
    briefing_path.write_text(json.dumps(_ledger(briefing_estimate)))
    budget = AttemptBudget(
        vision_path, briefing_path=briefing_path, now=lambda: NOW
    )

    assert budget.reserve() is expected


def _reserve_in_process(role: str, vision_path: str, briefing_path: str, barrier, queue):
    vision = AttemptBudget(
        vision_path, briefing_path=briefing_path, now=lambda: NOW
    )
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    barrier.wait()
    queue.put(vision.reserve() if role == "vision" else briefing.reserve())


def _hold_shared_lock(vision_path: str, briefing_path: str, acquired, release):
    with reservation_lock(Path(vision_path), Path(briefing_path)):
        acquired.set()
        if not release.wait(10):
            raise TimeoutError("test did not release the shared lock")


def _reserve_with_lock_probe(vision_path: str, briefing_path: str, probe_done, blocked, release, queue):
    from app import openrouter_budget

    original_flock = openrouter_budget.fcntl.flock

    def probe_flock(fd, operation):
        if operation == openrouter_budget.fcntl.LOCK_EX:
            try:
                original_flock(fd, operation | openrouter_budget.fcntl.LOCK_NB)
            except BlockingIOError:
                blocked.set()
            else:
                original_flock(fd, openrouter_budget.fcntl.LOCK_UN)
            probe_done.set()
            if not release.wait(10):
                raise TimeoutError("test did not release the competing reservation")
        return original_flock(fd, operation)

    openrouter_budget.fcntl.flock = probe_flock
    budget = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    queue.put(budget.reserve())


def test_role_reservation_blocks_while_other_process_holds_shared_lock(tmp_path):
    context = multiprocessing.get_context("fork")
    vision_path = tmp_path / "vision-ledger" / "request-budget.json"
    briefing_path = tmp_path / "briefing-ledger" / "request-budget.json"
    vision_path.parent.mkdir()
    briefing_path.parent.mkdir()
    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    acquired, release_holder = context.Event(), context.Event()
    probe_done, blocked, release_reserver = context.Event(), context.Event(), context.Event()
    queue = context.Queue()
    holder = context.Process(
        target=_hold_shared_lock,
        args=(str(vision_path), str(briefing_path), acquired, release_holder),
    )
    reserver = context.Process(
        target=_reserve_with_lock_probe,
        args=(str(vision_path), str(briefing_path), probe_done, blocked, release_reserver, queue),
    )
    holder.start()
    assert acquired.wait(10)
    reserver.start()
    assert probe_done.wait(10)
    try:
        assert blocked.is_set(), "reservation lock was not held by the other process"
    finally:
        release_reserver.set()
        release_holder.set()
    holder.join(timeout=10)
    reserver.join(timeout=10)
    assert holder.exitcode == 0
    assert reserver.exitcode == 0
    assert queue.get(timeout=2) is True


def test_cross_role_process_reservations_share_the_ledger_lock_repeatedly(tmp_path):
    context = multiprocessing.get_context("fork")
    for run in range(5):
        run_dir = tmp_path / str(run)
        run_dir.mkdir()
        vision_path, briefing_path = run_dir / "vision.json", run_dir / "briefing.json"
        vision_path.write_text(json.dumps(_ledger(4.80)))
        briefing_path.write_text(json.dumps(_ledger(0.178)))
        barrier, queue = context.Barrier(2), context.Queue()
        processes = [
            context.Process(
                target=_reserve_in_process,
                args=(role, str(vision_path), str(briefing_path), barrier, queue),
            )
            for role in ("vision", "briefing")
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
        outcomes = [queue.get(timeout=2), queue.get(timeout=2)]
        assert sum(outcomes) == 1
        vision_estimate = json.loads(vision_path.read_text())["estimated_project_usd"]
        briefing_estimate = json.loads(briefing_path.read_text())["estimated_project_usd"]
        assert round(vision_estimate + briefing_estimate, 8) < 5.0


@pytest.mark.parametrize("reserving_role", ["vision", "briefing"])
@pytest.mark.parametrize("invalid_kind", ["malformed", "oversized", "unreadable"])
def test_invalid_peer_or_role_ledger_fails_closed(
    tmp_path, monkeypatch, reserving_role, invalid_kind
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    invalid_path = vision_path if reserving_role == "briefing" else briefing_path
    original = invalid_path.read_text()
    original_read_text = Path.read_text
    if invalid_kind == "malformed":
        invalid_path.write_text("{")
    elif invalid_kind == "oversized":
        daily = {
            (date(2026, 10, 28) - timedelta(days=offset)).isoformat(): 0.0
            for offset in range(5000)
        }
        oversized = json.dumps({**_ledger(0.0), "estimated_daily": daily})
        invalid_path.write_text(oversized)
        assert invalid_path.stat().st_size > MAX_LEDGER_BYTES
        assert json.loads(invalid_path.read_text())["estimated_project_usd"] == 0.0
    else:
        def fail_selected_path(path, *args, **kwargs):
            if path == invalid_path:
                raise PermissionError("injected unreadable ledger")
            return original_read_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", fail_selected_path)

    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    assert (vision.reserve() if reserving_role == "vision" else briefing.reserve()) is False
    if invalid_kind == "unreadable":
        assert original_read_text(invalid_path) == original


@pytest.mark.parametrize("reserving_role", ["vision", "briefing"])
@pytest.mark.parametrize(
    "invalid_ledger",
    [
        {"attempts": [], "estimated_project_usd": "0.0", "estimated_daily": {}},
        {"attempts": [], "estimated_project_usd": -0.1, "estimated_daily": {}},
        {"attempts": "none", "estimated_project_usd": 0.0, "estimated_daily": {}},
        {"attempts": [], "estimated_project_usd": 0.0, "estimated_daily": []},
    ],
    ids=["estimate-type", "negative-estimate", "attempts-type", "daily-type"],
)
def test_semantically_invalid_opposite_ledger_fails_closed(
    tmp_path, reserving_role, invalid_ledger
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    invalid_path = vision_path if reserving_role == "briefing" else briefing_path
    invalid_path.write_text(json.dumps(invalid_ledger))
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )

    assert (vision.reserve() if reserving_role == "vision" else briefing.reserve()) is False


@pytest.mark.parametrize("reserving_role", ["vision", "briefing"])
@pytest.mark.parametrize("large_value", ["estimate", "timestamp", "daily"])
def test_extreme_numeric_values_fail_closed_without_overflow(
    tmp_path, reserving_role, large_value
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    invalid_path = vision_path if reserving_role == "briefing" else briefing_path
    huge_integer = int("9" * 1000)
    invalid = _ledger(0.0)
    if large_value == "estimate":
        invalid["estimated_project_usd"] = huge_integer
    elif large_value == "timestamp":
        invalid["attempts"] = [huge_integer]
    else:
        invalid["estimated_daily"] = {"2026-10-28": huge_integer}
    invalid_path.write_text(json.dumps(invalid))
    assert json.loads(invalid_path.read_text())
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )

    assert (vision.reserve() if reserving_role == "vision" else briefing.reserve()) is False


@pytest.mark.parametrize("reserving_role", ["vision", "briefing"])
def test_failed_atomic_replace_denies_and_preserves_role_ledger(
    tmp_path, monkeypatch, reserving_role
):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    role_path = vision_path if reserving_role == "vision" else briefing_path
    prior = role_path.read_bytes()

    def fail_replace(source, target):
        raise OSError("injected atomic replacement failure")

    monkeypatch.setattr("app.openrouter_vision.os.replace", fail_replace)
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    assert (vision.reserve() if reserving_role == "vision" else briefing.reserve()) is False
    assert role_path.read_bytes() == prior


def test_missing_ledgers_initialize_on_accepted_reservation(tmp_path):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    assert vision.reserve() is True
    assert json.loads(vision_path.read_text())["estimated_project_usd"] == 0.02
    assert not briefing_path.exists()


def test_existing_role_estimate_boundaries_are_preserved(tmp_path):
    vision_path, briefing_path = tmp_path / "vision.json", tmp_path / "briefing.json"
    vision_path.write_text(json.dumps(_ledger(4.88)))
    briefing_path.write_text(json.dumps(_ledger(0.0)))
    vision = AttemptBudget(vision_path, briefing_path=briefing_path, now=lambda: NOW)
    assert vision.reserve() is True  # Exactly $4.90 remains allowed.
    assert vision.reserve() is False

    vision_path.write_text(json.dumps(_ledger(0.0)))
    briefing_path.write_text(json.dumps(_ledger(4.987)))
    briefing = BriefingAttemptBudget(
        briefing_path, vision_path=vision_path, now=lambda: NOW
    )
    assert briefing.reserve() is True  # $4.989 is below the role's $4.99 guard.
    briefing_path.write_text(json.dumps(_ledger(4.988)))
    assert briefing.reserve() is False  # Equality at $4.99 remains rejected.
