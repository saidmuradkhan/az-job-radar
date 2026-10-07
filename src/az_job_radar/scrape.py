import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from az_job_radar.db import ScrapeRun, mark_duplicates, upsert_vacancies
from az_job_radar.models import Vacancy

logger = logging.getLogger(__name__)

Fetch = Callable[[], Awaitable[list[Vacancy]]]

DUPLICATE_WINDOW = timedelta(days=45)


def now() -> datetime:
    return datetime.now(UTC)


async def scrape_and_store(engine: Engine, fetch: Fetch) -> ScrapeRun:
    with Session(engine, expire_on_commit=False) as session:
        run = ScrapeRun(started_at=now(), status="running", found=0, new=0, duplicates=0)
        session.add(run)
        session.commit()

        try:
            vacancies = await fetch()
            run.found = len(vacancies)
            run.new = upsert_vacancies(session, vacancies, now())
            run.duplicates = mark_duplicates(session, since=now() - DUPLICATE_WINDOW)
            run.status = "ok"
        except Exception as error:
            # Roll back first: after a failed flush the session can't even read run.id.
            session.rollback()
            logger.exception("Scrape run %s failed", run.id)
            run.status = "failed"
            run.error = str(error)

        run.finished_at = now()
        session.add(run)
        session.commit()
        return run
