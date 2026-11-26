"""Read aggregate RouteLens API usage from the application database."""

import argparse
import sys
from collections import Counter
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api_usage import DEFAULT_DAYS, UsageStore, UsageUnavailable, configured_usage_path


def print_table(heading: str, rows: Mapping[str, int]) -> None:
    width = max(len(heading), max(map(len, rows), default=0))
    print(f"\n{heading:<{width}}  {'Attempts':>10}")
    for label, attempts in rows.items():
        print(f"{label:<{width}}  {attempts:>10,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="UTC dates including today")
    parser.add_argument("--daily", action="store_true", help="show totals by UTC date")
    parser.add_argument("--operations", action="store_true", help="show totals by operation")
    args = parser.parse_args()
    store = UsageStore(configured_usage_path())
    try:
        start, end = store.window(args.days)
    except ValueError as error:
        parser.error(str(error))
    try:
        report = store.read_report(start, end)
    except UsageUnavailable:
        print(
            "API usage database is missing or unreadable. Check the application data directory.",
            file=sys.stderr,
        )
        return 1

    print(f"API usage · {report.start} through {report.end} inclusive (UTC)")
    print("Backend request attempts include quota reservations. Provider-account totals may differ.")
    print("MapTiler browser map resources are untracked.")
    if report.gaps:
        print("Degraded tracking on " + ", ".join(map(str, sorted(report.gaps))) + ".")
    print_table("Provider", report.provider_totals())
    if args.daily:
        daily = Counter()
        for (day, _), attempts in report.counts.items():
            daily[day] += attempts
        dates = (report.start + timedelta(days=offset) for offset in range(args.days))
        print_table("Date (UTC)", {day.isoformat(): daily[day] for day in dates})
    if args.operations:
        print_table("Operation", {
            operation.value: attempts for operation, attempts in report.operation_totals().items()
        })
    return 0


if __name__ == "__main__":
    sys.exit(main())
