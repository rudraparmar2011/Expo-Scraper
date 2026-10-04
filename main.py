"""
main.py
-------
CLI entry point for the Expo Scraper project.

Usage:
    python main.py --site exhibition_globe                # scrape + save
    python main.py --site exhibition_globe --no-db        # scrape only (print)
    python main.py --site exhibition_globe --max 5        # limit records
    python main.py --site all                             # run all registered scrapers
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from utils.database import init_db, save_expos, count_expos
from utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Registry — add new scrapers here as you build them
# ---------------------------------------------------------------------------
def _get_scrapers() -> dict[str, Callable[[], list[dict]]]:
    from scrapers.exhibition_globe import scrape as scrape_eg
    return {
        "exhibition_globe": scrape_eg,
        # "allevents": scrape_allevents,   # add later
        # "meraevents": scrape_meraevents, # add later
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="expo-scraper",
        description="Scrape expos in Ahmedabad & Vadodara and store them.",
    )
    parser.add_argument(
        "--site",
        choices=["exhibition_globe", "all"],
        default="exhibition_globe",
        help="Which source to scrape (default: exhibition_globe)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum records to keep (for testing)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Do not save to database — just print a summary",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=5,
        help="How many sample records to print (default: 5)",
    )
    return parser.parse_args()


def run_one(name: str, max_records: int | None) -> list[dict]:
    scrapers = _get_scrapers()
    if name not in scrapers:
        log.error("Unknown scraper: {}", name)
        return []
    log.info("Running scraper: {}", name)
    return scrapers[name]()


def run_all(max_records: int | None) -> list[dict]:
    all_records: list[dict] = []
    for name in _get_scrapers():
        all_records.extend(run_one(name, max_records))
    return all_records


def main() -> int:
    args = parse_args()

    if not args.no_db:
        init_db()

    if args.site == "all":
        records = run_all(args.max)
    else:
        records = run_one(args.site, args.max)

    log.info("Scraped {} records total", len(records))

    if not records:
        log.warning("No records scraped.")
        return 1

    # ---- Print samples ----
    print()
    print("=" * 70)
    print(f"TOP {min(args.show, len(records))} SAMPLES")
    print("=" * 70)
    for r in records[: args.show]:
        print(f"\n📌 {r.get('name', '?')[:75]}")
        print(f"   City     : {r.get('city')}")
        print(f"   Category : {r.get('category')} / {r.get('sub_category')}")
        print(f"   Dates    : {r.get('start_date')} → {r.get('end_date')}")
        print(f"   Venue    : {r.get('venue')}")
        print(f"   Fees     : {r.get('fees')} {r.get('currency') or ''}")
        print(f"   URL      : {r.get('source_url')}")

    # ---- Save to DB ----
    if not args.no_db:
        summary = save_expos(records)
        log.info("DB summary: {}", summary)
        log.info("Total rows in DB now: {}", count_expos())
    else:
        log.info("Skipped DB save (--no-db)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())