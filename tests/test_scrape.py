import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from az_job_radar import scrape
from az_job_radar.db import ScrapeRun, VacancyRow, get_engine
from az_job_radar.models import Vacancy
from az_job_radar.scrape import scrape_and_store


def make_vacancy(external_id: str, source: str = "boss.az") -> Vacancy:
    return Vacancy(
        source=source,
        external_id=external_id,
        title="Python Developer",
        company="Acme",
        url=f"https://boss.az/vacancies/{external_id}",
    )


@pytest.fixture
def engine():
    engine = get_engine("sqlite://")
    yield engine
    engine.dispose()


async def test_successful_run_is_recorded(engine):
    async def fetch():
        return [make_vacancy("1"), make_vacancy("2")]

    first = await scrape_and_store(engine, fetch)
    second = await scrape_and_store(engine, fetch)

    assert (first.status, first.found, first.new) == ("ok", 2, 2)
    assert (second.status, second.found, second.new) == ("ok", 2, 0)
    assert second.finished_at is not None
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 2
        assert session.scalar(select(func.count()).select_from(ScrapeRun)) == 2


async def test_failed_run_is_recorded_with_the_error(engine):
    async def fetch():
        raise RuntimeError("network is down")

    run = await scrape_and_store(engine, fetch)

    assert run.status == "failed"
    assert run.error == "network is down"
    with Session(engine) as session:
        saved = session.get(ScrapeRun, run.id)
        assert saved.status == "failed"
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 0


async def test_run_counts_cross_site_duplicates(engine):
    async def fetch():
        return [make_vacancy("1"), make_vacancy("1", source="hellojob.az")]

    run = await scrape_and_store(engine, fetch)

    assert (run.found, run.new, run.duplicates) == (2, 2, 1)


async def test_database_error_is_recorded(engine, monkeypatch):
    def broken_mark_duplicates(session, since):
        session.add(ScrapeRun(started_at=None))
        session.flush()

    monkeypatch.setattr(scrape, "mark_duplicates", broken_mark_duplicates)

    async def fetch():
        return [make_vacancy("1")]

    run = await scrape_and_store(engine, fetch)

    assert run.status == "failed"
    with Session(engine) as session:
        assert session.get(ScrapeRun, run.id).status == "failed"
        assert session.scalar(select(func.count()).select_from(VacancyRow)) == 0
