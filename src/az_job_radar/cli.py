import argparse
import asyncio
import logging

from az_job_radar.collect import collect
from az_job_radar.db import get_engine
from az_job_radar.scrape import scrape_and_store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="az-job-radar", description="Collect IT vacancies from Azerbaijani job sites."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scrape = commands.add_parser("scrape", help="scrape all sources and save to the database")
    scrape.add_argument(
        "--database-url",
        help="defaults to $DATABASE_URL, or a local SQLite file az_job_radar.db",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    engine = get_engine(args.database_url)
    try:
        run = asyncio.run(scrape_and_store(engine, collect))
    finally:
        engine.dispose()

    print(
        f"Run #{run.id}: {run.status}, {run.found} vacancies found, {run.new} new, "
        f"{run.duplicates} cross-site duplicates"
    )
    return 0 if run.status == "ok" else 1
