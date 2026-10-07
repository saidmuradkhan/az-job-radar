import argparse
import asyncio
import logging

from az_job_radar.collect import collect
from az_job_radar.db import get_engine, uids_with_description
from az_job_radar.scrape import scrape_and_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="az-job-radar", description="Collect vacancies from Azerbaijani job sites."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scrape = commands.add_parser("scrape", help="scrape all sources and save to the database")
    scrape.add_argument(
        "--database-url",
        help="defaults to $DATABASE_URL, or a local SQLite file az_job_radar.db",
    )
    scrape.add_argument(
        "--no-details",
        action="store_true",
        help="only read listing pages (faster, but no full descriptions)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    engine = get_engine(args.database_url)
    known = uids_with_description(engine)

    async def fetch():
        return await collect(details=not args.no_details, skip=known)

    try:
        run = asyncio.run(scrape_and_store(engine, fetch))
    finally:
        engine.dispose()

    print(
        f"Run #{run.id}: {run.status}, {run.found} vacancies found, {run.new} new, "
        f"{run.duplicates} cross-site duplicates"
    )
    return 0 if run.status == "ok" else 1
