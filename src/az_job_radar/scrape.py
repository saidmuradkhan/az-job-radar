import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from az_job_radar.db import ScrapeRun, upsert_vacancies
from az_job_radar.models import Vacancy

logger = logging.getLogger(__name__)

Fetch = Callable[[], Awaitable[list[Vacancy]]]


def now() -> datetime:
    return datetime.now(UTC)


async def scrape_and_store(engine: Engine, fetch: Fetch) -> ScrapeRun:
    with Session(engine, expire_on_commit=False) as session:
        run = ScrapeRun(started_at=now(), status="running", found=0, new=0)
        session.add(run)
        session.commit()

        try:
            vacancies = await fetch()
            run.found = len(vacancies)
            run.new = upsert_vacancies(session, vacancies, now())
            run.status = "ok"
        except Exception as error:
            logger.exception("Scrape run %s failed", run.id)
            session.rollback()
            run.status = "failed"
            run.error = str(error)

        run.finished_at = now()
        session.add(run)
        session.commit()
        return run
